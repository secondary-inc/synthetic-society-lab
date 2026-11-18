"""Candidate-only FEC Senate cell parsing. Never adopts counts or emits features.

No source is opened at import. The workbook adapter is optional and read-only;
the caller owns the separately reviewed actual-run release. Authored tests use
only fictional rows and inert reader objects. No CLI invokes the actual source.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import re
import signal
import sys
import threading
import time
import warnings
import zipfile
import xml.etree.ElementTree as ET

CONTRACT_SHA256 = "db5d3b76ed7e0d4ab6f05143e40096e7acaa7663bda0f305473f17954232a23a"
CONTRACT_CANONICAL_SHA256 = "b08106f8d25e68f171e41d5e1f084c051701f7f10f212629da539384ea4a0a81"
READER_VERSION = "3.1.5"
ET_XMLFILE_VERSION = "2.0.0"
SENATE = "12. US Senate Results by State"
SUMMARY = "7. Table 6 Senate by Party"
RANGES = {SENATE: (542, 26), SUMMARY: (78, 7),
          "14. 2020 Party Labels": (121, 5), "1. 2020 Publication Information": (150, 2)}
# Exact opaque printer settings in the one pinned FEC source.
# Every other member is parsed as XML regardless of its filename suffix.
OPAQUE_PARTS = {
    'xl/printerSettings/printerSettings1.bin': (4821, 'ac43c34e45e564ed98b2e1547a3dc42dd51ca069caba2b9e090914cad3f6615b'),
    'xl/printerSettings/printerSettings2.bin': (8800, '8a7c955ec8e5578364177da2fad65b27c693b9e42e4ea3e839ccba917a8e032e'),
    'xl/printerSettings/printerSettings3.bin': (5528, '1c519dd3f54033b3a310954f4c1242de99ddc04a4f03796ac40c361840a5fd8f'),
    'xl/printerSettings/printerSettings4.bin': (5528, '1c519dd3f54033b3a310954f4c1242de99ddc04a4f03796ac40c361840a5fd8f'),
    'xl/printerSettings/printerSettings5.bin': (5528, '1c519dd3f54033b3a310954f4c1242de99ddc04a4f03796ac40c361840a5fd8f'),
    'xl/printerSettings/printerSettings11.bin': (8800, '8a7c955ec8e5578364177da2fad65b27c693b9e42e4ea3e839ccba917a8e032e'),
    'xl/printerSettings/printerSettings14.bin': (4821, '0880d8a02b0c8fb1da513dfa5bc4c38d7702257d4054a8de87d16dd273807643'),
    'xl/printerSettings/printerSettings15.bin': (4821, '0880d8a02b0c8fb1da513dfa5bc4c38d7702257d4054a8de87d16dd273807643'),
    'xl/printerSettings/printerSettings16.bin': (4821, '0880d8a02b0c8fb1da513dfa5bc4c38d7702257d4054a8de87d16dd273807643'),
    'xl/printerSettings/printerSettings17.bin': (4821, '0880d8a02b0c8fb1da513dfa5bc4c38d7702257d4054a8de87d16dd273807643'),
    'xl/printerSettings/printerSettings9.bin': (4821, '26a3634737c60e4e9a43393bb93502afeb561c5253a852e38dab1390030290b6'),
    'xl/printerSettings/printerSettings8.bin': (5528, '1c519dd3f54033b3a310954f4c1242de99ddc04a4f03796ac40c361840a5fd8f'),
    'xl/printerSettings/printerSettings7.bin': (5528, '1c519dd3f54033b3a310954f4c1242de99ddc04a4f03796ac40c361840a5fd8f'),
    'xl/printerSettings/printerSettings12.bin': (4821, '26a3634737c60e4e9a43393bb93502afeb561c5253a852e38dab1390030290b6'),
    'xl/printerSettings/printerSettings6.bin': (5528, '1c519dd3f54033b3a310954f4c1242de99ddc04a4f03796ac40c361840a5fd8f'),
    'xl/printerSettings/printerSettings10.bin': (4821, 'f4852f34b27abefb3256ca573d68500ca71f6484b54a4076f55a455bfbc0741b'),
    'xl/printerSettings/printerSettings13.bin': (4821, '26a3634737c60e4e9a43393bb93502afeb561c5253a852e38dab1390030290b6'),
}
STAGES = ((11, "PRIMARY"), (13, "PRIMARY_RUNOFF"), (15, "GENERAL"), (17, "GENERAL_RUNOFF"))
STATES = frozenset("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
OTHER_PARTIES = frozenset("W AKI LIB APV UPC IDE IND GRE CON WWP NPY NPA OTH UST NLP LMN GLC OBF LWR PG/PRO W(D) W(R) W(GRE)".split())
TOTAL_LABELS = {"Total State Votes:": "S", "Total Full Term State Votes:": "S-FULL TERM", "Total Unexpired Term State Votes:": "S-UNEXPIRED TERM"}
REMOVAL_FOOTNOTE = "# The Montana Green Party candidates were removed from the general election ballot in August 2020 by court order."
FALSE_FLAGS = {"source_adoption": False, "historical_feature_adoption": False,
               "sample_selection_adoption": False, "forecast_consumption": False, "numeric_acceptance": False}


class ParserRefused(ValueError):
    """Fixed, nonsecret code; never includes a raw cell or foreign exception."""


def require(ok, code):
    if not ok:
        raise ParserRefused(code)


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(packed(value)).hexdigest()


def load_contract(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(65537)
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == CONTRACT_SHA256, "CONTRACT_PIN")
    return json.loads(raw)


def checked_contract(contract):
    # Bind the exact bytes via load_contract for I/O callers, and the exact
    # canonical content for pure callers. This snapshot never trusts flags.
    require(type(contract) is dict and contract.get("kind") == "E01_FEC2020_SENATE_MAPPING_PARSER_CONTRACT_V1", "CONTRACT_SCHEMA")
    require(contract.get("adoption") is False and contract.get("forecast_consumption") is False, "CONTRACT_AUTHORITY")
    require(contract.get("implementation_bounds_proposed", {}).get("range_cells_max") == 16000, "CONTRACT_BOUNDS")
    require(digest(contract) == CONTRACT_CANONICAL_SHA256, "CONTRACT_CONTENT_PIN")
    return json.loads(packed(contract))


@dataclass(frozen=True)
class Cell:
    value: object = None
    kind: str = "n"


def cell_value(cell):
    require(type(cell) is Cell and cell.kind in {"n", "s", "inlineStr", "b"}, "CELL_TYPE_OR_FORMULA")
    value = cell.value
    require(value is None or type(value) in {str, int, float, bool}, "CELL_PRIMITIVE")
    if type(value) is str:
        require(len(value) <= 4096, "CELL_TEXT_BOUND")
    if type(value) is float:
        require(math.isfinite(value), "CELL_NONFINITE")
    if type(value) is int:
        require(abs(value) <= 10**15, "CELL_INTEGER_BOUND")
    require(cell.kind != "b" or type(value) is bool, "CELL_TYPE_VALUE")
    require(value is None or cell.kind != "n" or type(value) in {int, float}, "CELL_TYPE_VALUE")
    require(value is None or cell.kind not in {"s", "inlineStr"} or type(value) is str, "CELL_TYPE_VALUE")
    return value


def source_reference(source):
    require(type(source) is dict and set(source) == {"source_id", "bytes", "sha256", "provenance"}, "SOURCE_SCHEMA")
    require(type(source["bytes"]) is int and 0 < source["bytes"] <= 6251110, "SOURCE_SIZE")
    require(type(source["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", source["sha256"]) is not None, "SOURCE_HASH")
    if source["provenance"] == "MOCK":
        require(type(source["source_id"]) is str and re.fullmatch("AUTHORED_[A-Z0-9_]{1,80}", source["source_id"]) is not None, "MOCK_ID")
    else:
        require(source == {"source_id": "FEC2020_WORKBOOK_CANDIDATE_20261118", "bytes": 6251110,
                           "sha256": "5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e",
                           "provenance": "CANDIDATE_NOT_ADOPTED"}, "REAL_SOURCE_PIN")
    return dict(source)


def count(value, *, removed=False):
    if value is None or (type(value) is str and not value.strip()):
        return {"votes": None, "status": "MISSING"}
    if type(value) is str and value in {"n/a", "-", "*"}:
        return {"votes": None, "status": "NONNUMERIC_MARKER", "literal": value}
    if value == "#" and type(value) is str:
        return {"votes": None, "status": "REMOVED_FROM_BALLOT" if removed else "UNKNOWN_BLOCKED", "literal": "#"}
    require(type(value) in {int, float} and 0 <= value <= 10**12
            and math.isfinite(value) and int(value) == value, "INVALID_VOTE_COUNT")
    return {"votes": int(value), "status": "OBSERVED_INTEGER"}


def blank(value):
    return value is None or (type(value) is str and not value.strip())


def party_bucket(party):
    if party in ("D", "R"):
        return party
    if party in OTHER_PARTIES:
        return "OTHER"
    # DFL, AK nonpartisan and OR coalition acceptance is not supplied by a label.
    return "UNKNOWN"


def row_record(cells, row_number, source):
    require(type(cells) in {list, tuple} and len(cells) == 26, "ROW_WIDTH")
    values = [cell_value(cell) for cell in cells]
    require(type(values[0]) is int and values[0] == row_number, "ROW_ORDINAL")
    require(values[24:] == [None, None] and values[19] is None and values[20] is None, "UNREVIEWED_COMBINED_OR_EXTRA_COLUMNS")
    raw = {"row": row_number, "values": values, "types": [cell.kind for cell in cells]}
    result = {"source": source, "sheet": SENATE, "raw_row": raw, "raw_row_sha256": digest(raw),
              "state": values[1], "contest_label": values[3], "candidate_name": values[8],
              "fec_id_literal": values[4], "party_literal": values[10], "party_bucket": "UNKNOWN",
              "class": None, "term_context": None, "event_date": None,
              "candidate_identity_accepted": False, "role": None, "stages": [], "blockers": []}
    if all(value is None for i, value in enumerate(values) if i not in (0, 4)) and values[4] in (None, "n/a"):
        result["role"] = "ORDINAL_ONLY_SEPARATOR"
        return result
    require(values[1] in STATES and type(values[2]) is str and bool(values[2].strip())
            and values[3] in {"S", "S-FULL TERM", "S-UNEXPIRED TERM"}, "STATE_CONTEST_CONTEXT")
    label = values[9]
    if label == "Party Votes:":
        require(blank(values[8]) and not blank(values[10]), "PARTY_SUBTOTAL_ROLE")
        result["role"] = "PARTY_SUBTOTAL"
    elif label in TOTAL_LABELS:
        require(values[3] == TOTAL_LABELS[label] and blank(values[8]) and blank(values[10]), "CONTEST_TOTAL_ROLE")
        result["role"] = "CONTEST_TOTAL"
    else:
        require(label is None and type(values[8]) is str and bool(values[8].strip())
                and type(values[10]) is str and bool(values[10].strip()), "UNKNOWN_ROW_ROLE")
        result["role"] = "CANDIDATE_STAGE_VOTE"
        result["party_bucket"] = party_bucket(values[10])
        if result["party_bucket"] == "UNKNOWN":
            result["blockers"].append("PARTY_IDENTITY_UNREVIEWED")
    removal = (values[1] == "MT" and row_number in {304, 305, 306, 307}
               and values[23] == REMOVAL_FOOTNOTE)
    for column, stage in STAGES:
        measured = count(values[column], removed=removal and stage == "GENERAL")
        event_date = None
        if stage == "GENERAL_RUNOFF" and values[1] == "GA" and measured["votes"] is not None:
            allowed = {"General Runoff Election on January 5, 2021.", "Special General Runoff Election on January 5, 2021."}
            if values[23] in allowed:
                event_date = "2021-01-05"
        result["stages"].append({"stage": stage, "column": chr(65+column), "cell": chr(65+column)+str(row_number),
                                 "cycle_year": 2020, "event_date": event_date,
                                 "event_year": 2021 if event_date else None, **measured})
        if measured["status"] in {"UNKNOWN_BLOCKED", "NONNUMERIC_MARKER"} and stage in {"GENERAL", "GENERAL_RUNOFF"}:
            result["blockers"].append("GENERAL_COUNT_UNAVAILABLE")
    if result["role"] == "CANDIDATE_STAGE_VOTE":
        if any(s["status"] == "REMOVED_FROM_BALLOT" for s in result["stages"]):
            result["role"] = "FOOTNOTE_REMOVAL"
        elif not any(s["status"] != "MISSING" for s in result["stages"][2:]):
            result["role"] = "PRIMARY_ONLY"
    return result


def audit_rows(cells, contract, source):
    """Parse exactly one bounded Senate range into nonadopted candidate records."""
    contract = checked_contract(contract)
    source = source_reference(source)
    iterator = iter(cells)
    header = next(iterator, None)
    require(type(header) in {tuple, list} and len(header) == 26
            and [cell_value(cell) for cell in header] == contract["input_contract"]["header_literal"]
            and all(type(cell.value) is type(value) for cell, value in zip(header, contract["input_contract"]["header_literal"])), "SENATE_HEADER")
    records = []
    seen = set()
    for number in range(2, 543):
        row = next(iterator, None)
        require(row is not None, "MISSING_ROW")
        record = row_record(row, number, source)
        if record["role"] in {"CANDIDATE_STAGE_VOTE", "PRIMARY_ONLY", "FOOTNOTE_REMOVAL"}:
            name = record["candidate_name"]
            fec = record["fec_id_literal"]
            identity = fec.strip() if type(fec) is str and re.fullmatch("S[0-9A-Z]{8}", fec.strip()) else name
            for stage in record["stages"]:
                if stage["votes"] is not None:
                    keys = {(record["state"], record["contest_label"], stage["stage"], "id", identity),
                            (record["state"], record["contest_label"], stage["stage"], "name", name.strip())}
                    require(not keys.intersection(seen), "DUPLICATE_CANDIDATE_STAGE")
                    seen.update(keys)
        records.append(record)
    require(next(iterator, None) is None, "EXTRA_ROW")
    result = {"kind": "FEC2020_SENATE_CANDIDATE_ROWS_V1", "provenance": source["provenance"],
              "records": records, "source": source, **FALSE_FLAGS}
    require(len(packed(result)) <= 4194304, "OUTPUT_BOUND")
    return result


def stage_controls(parsed):
    """Internal exact-count checks; never mixes events or adds subtotal rows."""
    groups = {}
    for record in parsed["records"]:
        if record["role"] == "ORDINAL_ONLY_SEPARATOR":
            continue
        for stage in record["stages"]:
            key = (record["state"], record["contest_label"], stage["stage"])
            row = groups.setdefault(key, {"candidate_sum": 0, "candidate_count": 0,
                                          "control": None, "control_seen": False, "unknown": False, "party_sums": {"D": 0, "R": 0, "OTHER": 0}, "party_unknown": False})
            if record["role"] == "CONTEST_TOTAL":
                require(not row["control_seen"], "DUPLICATE_CONTEST_TOTAL")
                row["control_seen"] = True
                row["control"] = stage["votes"]
            elif record["role"] != "PARTY_SUBTOTAL":
                if stage["votes"] is not None:
                    row["candidate_sum"] += stage["votes"]
                    row["candidate_count"] += 1
                    if record["party_bucket"] == "UNKNOWN":
                        row["party_unknown"] = True
                    else:
                        row["party_sums"][record["party_bucket"]] += stage["votes"]
                if stage["status"] in {"UNKNOWN_BLOCKED", "NONNUMERIC_MARKER"}:
                    row["unknown"] = True
    output = []
    for (state, contest, stage), row in sorted(groups.items()):
        status = ("BLOCKED_UNKNOWN_COUNT" if row["unknown"] else "UNAVAILABLE_CONTROL" if row["control"] is None
                  else "PASS_INTERNAL_COUNT" if row["candidate_sum"] == row["control"] else "MISMATCH")
        output.append({"state": state, "contest_label": contest, "stage": stage, "status": status, **row})
    return output


def cohort_ledger(parsed, contract):
    output = []
    for state in contract["cohort"]["expected_regular_class_II_states"]:
        rows = [r for r in parsed["records"] if r["state"] == state and r["role"] == "CANDIDATE_STAGE_VOTE"
                and r["contest_label"] != "S-UNEXPIRED TERM" and r["stages"][2]["votes"] is not None]
        blockers = ["CLASS_DATE_TERM_CANDIDATE_PROVENANCE_PENDING"]
        if not rows:
            blockers.append("NO_GENERAL_CANDIDATE_OBSERVATIONS")
        for party in ("D", "R"):
            if sum(r["party_bucket"] == party for r in rows) != 1:
                blockers.append("REQUIRES_EXACTLY_ONE_"+party)
        blockers.extend({"AK": ["NONPARTISAN_MAPPING_UNREVIEWED"], "OR": ["COALITION_MAPPING_UNREVIEWED"],
                         "ME": ["ROUND_PROVENANCE_UNREVIEWED"], "GA": ["CONDITIONAL_GENERAL_PROTOCOL_UNREVIEWED"],
                         "LA": ["MULTIPLE_NOMINEE_RULE_REVIEW_REQUIRED"]}.get(state, []))
        output.append({"state": state, "frame_slot": "2026-"+state+"-SENATE-C2", "status": "BLOCKED_NOT_ADOPTED",
                       "general_candidate_observations": len(rows), "blockers": blockers, "prior_margin_pp": None, **FALSE_FLAGS})
    require(len(output) == 33 and len({r["state"] for r in output}) == 33, "COHORT_FRAME")
    return output


def summary_controls(summary_cells, controls):
    require(type(summary_cells) is list and len(summary_cells) == 78 and all(len(r) == 7 for r in summary_cells), "SUMMARY_RANGE")
    values = [[cell_value(c) for c in row] for row in summary_cells]
    require(values[2][1:] == ["PRIMARY ELECTION (D)", "PRIMARY ELECTION (R)", "PRIMARY ELECTION (O)",
                                     "GENERAL ELECTION (D)", "GENERAL ELECTION (R)", "GENERAL ELECTION (O)"]
            and values[3] == ["State", "Democratic", "Republican", "Other", "Democratic", "Republican", "Other"], "SUMMARY_HEADER")
    output, seen = [], set()
    for number, row in enumerate(values[4:60], 5):
        state = row[0]
        require(state in STATES or state in {"AS", "DC", "GU", "MP", "PR", "VI"}, "SUMMARY_STATE")
        if state not in STATES:
            continue  # Explicit non-state summary rows cannot become Senate seats.
        require(state not in seen, "DUPLICATE_SUMMARY_STATE")
        seen.add(state)
        groups = [r for r in controls if r["state"] == state and r["stage"] == "GENERAL" and r["candidate_count"]]
        runoffs = [r for r in controls if r["state"] == state and r["stage"] == "GENERAL_RUNOFF" and r["candidate_count"]]
        eligible = len(groups) == 1 and not runoffs and state != "GA" and not groups[0]["party_unknown"]
        for column, bucket in ((4, "D"), (5, "R"), (6, "OTHER")):
            control = count(row[column])
            computed = groups[0]["party_sums"][bucket] if eligible else None
            status = ("UNAVAILABLE_CONTROL" if control["votes"] is None else "BLOCKED_EVENT_OR_PARTY_COMPOSITION" if not eligible
                      else "PASS_INTERNAL_COUNT" if computed == control["votes"] else "MISMATCH")
            output.append({"state": state, "bucket": bucket, "source_cell": chr(65+column)+str(number),
                           "control": control["votes"], "control_status": control["status"],
                           "candidate_sum": computed, "status": status})
    return output


def percentage_diagnostics(parsed, controls):
    by_group = {(row["state"], row["contest_label"], row["stage"]): row for row in controls}
    output = []
    for record in parsed["records"]:
        if record["role"] not in {"CANDIDATE_STAGE_VOTE", "PRIMARY_ONLY", "FOOTNOTE_REMOVAL"}:
            continue
        for index, column in ((2, 16), (3, 18)):
            stage = record["stages"][index]
            if stage["votes"] is None:
                continue
            value = record["raw_row"]["values"][column]
            group = by_group[(record["state"], record["contest_label"], stage["stage"])]
            if value is None:
                status = "UNAVAILABLE_PERCENTAGE"
            else:
                require(type(value) in {int, float} and 0 <= value <= 1 and math.isfinite(value), "INVALID_PERCENTAGE")
                status = ("BLOCKED_NO_STAGE_TOTAL" if not group["control"] else "PASS_DIAGNOSTIC"
                          if math.isclose(value, stage["votes"]/group["control"], rel_tol=0, abs_tol=1e-10) else "MISMATCH")
            output.append({"row": record["raw_row"]["row"], "column": chr(65+column), "status": status,
                           "scope": "DIAGNOSTIC_ONLY_NEVER_VOTE_RECONSTRUCTION", "absolute_tolerance": 1e-10})
    return output


def result_from_tables(tables, contract, source):
    require(type(tables) is dict and set(tables) == set(RANGES), "TABLE_SET")
    for title, (rows, columns) in RANGES.items():
        require(type(tables[title]) is list and len(tables[title]) == rows
                and all(type(row) in {list, tuple} and len(row) == columns for row in tables[title]), "TABLE_RANGE")
        for row in tables[title]:
            for cell in row:
                cell_value(cell)
    parsed = audit_rows(tables[SENATE], contract, source)
    controls = stage_controls(parsed)
    result = {**parsed, "kind": "FEC2020_SENATE_CANDIDATE_AUDIT_V1", "stage_controls": controls,
              "party_summary_controls": summary_controls(tables[SUMMARY], controls),
              "percentage_diagnostics": percentage_diagnostics(parsed, controls),
              "auxiliary_raw_rows": {title: [{"row": i, "values": [c.value for c in row], "types": [c.kind for c in row]}
                                               for i, row in enumerate(tables[title], 1)] for title in RANGES if title != SENATE},
              "cohort": cohort_ledger(parsed, contract), "features": [], "scientific_acceptance": "NOT_RUN",
              "limitations": ["Internal worksheet checks are not external independent evidence.",
                              "Candidate/class/date/term/party/stage/round acceptance is pending; no feature projection.",
                              "No original full E01, House, retrospective evaluation or PDF/G03 gate is completed."], **FALSE_FLAGS}
    require(len(packed(result)) <= 4194304, "OUTPUT_BOUND")
    return result


class _NoDTDOrExternalRelationships:
    """Streaming Expat target: no tree, DTD, entity or external-link fetch."""
    def start(self, tag, attributes):
        if tag.rsplit("}", 1)[-1] == "Relationship":
            require(not any(key.rsplit("}", 1)[-1] == "TargetMode" and value.lower() == "external"
                            for key, value in attributes.items()), "EXTERNAL_RELATIONSHIP")
    def end(self, tag):
        pass
    def data(self, value):
        pass
    def doctype(self, name, public_id, system_id):
        raise ParserRefused("XML_DTD_OR_ENTITY")
    def close(self):
        return None


def xml_preflight(content):
    parser = ET.XMLParser(target=_NoDTDOrExternalRelationships())
    # The parser decodes its declared supported encoding before invoking the
    # target. UTF16 DTDs cannot bypass an ASCII-byte substring filter.
    for offset in range(0, len(content), 65536):
        parser.feed(content[offset:offset+65536])
    parser.close()


def archive_preflight(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 6251110, "WORKBOOK_SIZE")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            require(0 < len(members) <= 80 and sum(m.file_size for m in members) <= 67108864, "ARCHIVE_BOUND")
            require(len({m.filename for m in members}) == len(members), "DUPLICATE_ARCHIVE_MEMBER")
            for item in members:
                require(not item.flag_bits & 1 and item.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        # The pinned workbook contains one 41,139,508-byte XML
                        # member. Keep a finite 48 MiB member ceiling inside
                        # the unchanged 64 MiB aggregate expansion ceiling.
                        and item.file_size <= 50331648 and not item.filename.startswith("/")
                        and ".." not in Path(item.filename).parts, "ARCHIVE_MEMBER")
                require("externallinks/" not in item.filename.lower() and "vbaproject" not in item.filename.lower(), "EXTERNAL_LINK_OR_MACRO")
                require("\\" not in item.filename, "ARCHIVE_MEMBER")
                if item.is_dir():
                    require(item.file_size == 0, "ARCHIVE_DIRECTORY_PAYLOAD")
                    continue
                content = archive.read(item)
                opaque_pin = OPAQUE_PARTS.get(item.filename)
                if opaque_pin is not None:
                    require((len(content), hashlib.sha256(content).hexdigest()) == opaque_pin,
                            "OPAQUE_PART_PIN")
                else:
                    # A worksheet relationship may target any filename. Suffix
                    # checks cannot establish which members the reader parses.
                    xml_preflight(content)
            return {"members": len(members), "declared_expanded_bytes": sum(m.file_size for m in members)}
    except (zipfile.BadZipFile, ET.ParseError):
        raise ParserRefused("INVALID_WORKBOOK_ARCHIVE") from None


@contextmanager
def operation_deadline(seconds=120):
    require(threading.current_thread() is threading.main_thread(), "MAIN_THREAD_REQUIRED")
    old_handler = signal.getsignal(signal.SIGALRM)
    old_delay, old_interval = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    def expired(*_):
        raise ParserRefused("OPERATION_DEADLINE")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, min(seconds, old_delay) if old_delay else seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_delay:
            signal.setitimer(signal.ITIMER_REAL, max(.000001, old_delay-(time.monotonic()-started)), old_interval)


def read_candidate_bytes(raw, contract, source, *, reader=None):
    """One bounded optional read-only adapter call; never writes/adopts results.

    A fake reader can be used only with AUTHORED/MOCK source bytes. Actual source
    execution belongs to the separately released FEC-A01 run, not import or CI.
    No caller-supplied table is an official source witness by itself.
    """
    contract = checked_contract(contract)
    source = source_reference(source)
    require(type(raw) is bytes and len(raw) == source["bytes"]
            and hashlib.sha256(raw).hexdigest() == source["sha256"], "WORKBOOK_PIN")
    with operation_deadline():
        archive = archive_preflight(raw)
        if reader is None:
            try:
                import openpyxl as reader
                from openpyxl.xml import functions
                from importlib.metadata import version
            except ImportError:
                raise ParserRefused("OPTIONAL_READER_MISSING") from None
            require(version("et-xmlfile") == ET_XMLFILE_VERSION, "ET_XMLFILE_VERSION")
            require(functions.LXML is False and functions.DEFUSEDXML is False
                    and functions.iterparse.__module__ == "xml.etree.ElementTree"
                    and functions.fromstring.__module__ == "xml.etree.ElementTree", "XML_BACKEND_REQUIRES_FRESH_STDLIB_PROCESS")
            reader_metadata = {"package": "openpyxl", "version": READER_VERSION,
                               "et_xmlfile_version": ET_XMLFILE_VERSION,
                               "backend": "STDLIB_XML_ETREE_ELEMENTTREE", "LXML": False, "DEFUSEDXML": False}
        else:
            require(source["provenance"] == "MOCK", "READER_INJECTION_MOCK_ONLY")
            reader_metadata = {"package": "AUTHORED_INERT_READER", "version": READER_VERSION,
                               "backend": "MOCK_NOT_PACKAGE_QUALIFICATION"}
        require(reader.__version__ == READER_VERSION, "READER_VERSION")
        workbook = None
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                workbook = reader.load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
                tables = {}
                for title, (rows, columns) in RANGES.items():
                    sheet = workbook[title]
                    require(sheet.max_row == rows and sheet.max_column == columns, "DECLARED_SHEET_RANGE")
                    values = []
                    for row in sheet.iter_rows(min_row=1, max_row=rows, min_col=1, max_col=columns):
                        require(len(values) < rows, "READER_EXTRA_ROW")
                        values.append([Cell(cell.value, cell.data_type) for cell in row])
                    tables[title] = values
                result = result_from_tables(tables, contract, source)
                require(len(caught) <= 32, "READER_WARNING_BOUND")
                result["reader"] = {**reader_metadata, "warnings": [str(w.message)[:512] for w in caught]}
                result["archive"] = archive
                require(len(packed(result)) <= 4194304, "OUTPUT_BOUND")
                return result
            finally:
                if workbook is not None:
                    active_error = sys.exception()
                    try:
                        workbook.close()
                    except BaseException:
                        if active_error is None:
                            raise ParserRefused("WORKBOOK_CLOSE_FAILED") from None
