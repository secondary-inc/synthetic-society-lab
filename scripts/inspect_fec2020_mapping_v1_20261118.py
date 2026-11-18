"""Bounded local cell-structure inspection, never a numeric adoption/parser run."""
from pathlib import Path
import hashlib
import io
import json
import resource
import signal
import sys
import warnings
import zipfile


def inspect():
    import openpyxl
    root = Path(__file__).resolve().parents[1]
    contract_path = root / "configs/e01_fec2020_senate_mapping_v1.json"
    contract_raw = contract_path.read_bytes()
    contract = json.loads(contract_raw)
    source = contract["source"]
    path = root / source["path"]
    with path.open("rb") as stream:
        raw = stream.read(source["bytes"] + 1)
    assert len(raw) == source["bytes"]
    assert hashlib.sha256(raw).hexdigest() == source["sha256"]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        assert len(members) <= 80
        expanded = sum(member.file_size for member in members)
        assert expanded <= 67108864
        assert len({m.filename for m in members}) == len(members)
    captured = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
        try:
            ranges = {"12. US Senate Results by State": (542, 26),
                      "7. Table 6 Senate by Party": (78, 7),
                      "14. 2020 Party Labels": (121, 5),
                      "1. 2020 Publication Information": (150, 2)}
            sheets = {}
            formula_cells = []
            for title, (rows, columns) in ranges.items():
                values = []
                for row in workbook[title].iter_rows(min_row=1, max_row=rows, min_col=1, max_col=columns):
                    formula_cells.extend(title + "!" + cell.coordinate for cell in row if cell.data_type == "f")
                    values.append([cell.value for cell in row])
                sheets[title] = values
            assert not formula_cells
            senate = sheets["12. US Senate Results by State"]
            summary = sheets["7. Table 6 Senate by Party"]
            assert senate[0] == contract["input_contract"]["header_literal"]
            assert len(contract["cohort"]["expected_regular_class_II_states"]) == 33
            assert len(set(contract["cohort"]["expected_regular_class_II_states"])) == 33
            cells = sum(rows * columns for rows, columns in ranges.values())
            assert cells <= contract["implementation_bounds_proposed"]["range_cells_max"]
            checks = {
                "GA_regular_and_special_distinct_labels": senate[83][3] == "S-FULL TERM" and senate[96][3] == "S-UNEXPIRED TERM",
                "GA_later_runoff_footnote": all("January 5, 2021" in senate[row-1][23] for row in (84, 92, 97, 98)),
                "AK_nonpartisan_primary_label_preserved": senate[16][10] == "N(D)/D" and "Nonpartisan" in senate[16][23],
                "MT_removed_ballot_marker_is_not_zero": senate[303][15] == "#" and "removed" in senate[303][23],
                "MN_DFL_literal": senate[261][10] == "DFL",
                "OR_combined_label_one_row": senate[402][10] == "DEM/IP/WF",
                "NC_whitespace_total_role": senate[385][9] == "Total State Votes:" and senate[385][8] == " " and senate[385][10] == " ",
                "WV_other_summary_missing": summary[57][6] is None,
                "WY_other_summary_missing": summary[59][6] is None,
                "no_combined_total_counts_observed": all(row[19] is None for row in senate[1:]),
                "publication_month_observed": sheets["1. 2020 Publication Information"][41][0] == "October 2022",
                "GA_summary_scope_note": all("both full and unexpired" in summary[row-1][0] for row in (68, 70)),
            }
            assert all(checks.values())
            captured = [str(warning.message)[:512] for warning in caught]
        finally:
            workbook.close()
    return {"kind": "E01_FEC2020_MAPPING_SOURCE_INSPECTION_V1", "status": "AUTHOR_STRUCTURE_CHECKS_PASS_NOT_NUMERIC_ACCEPTANCE",
            "source_ref": {key: source[key] for key in ("path", "bytes", "sha256")},
            "contract_ref": {"path": str(contract_path.relative_to(root)), "bytes": len(contract_raw),
                             "sha256": hashlib.sha256(contract_raw).hexdigest()},
            "runtime": sys.version.split()[0], "reader": "openpyxl", "reader_version": openpyxl.__version__,
            "reader_options": {"read_only": True, "data_only": False, "keep_links": False},
            "zip_members": len(members), "declared_expanded_bytes": expanded,
            "bounded_cells": cells, "formula_cells": formula_cells, "checks": checks, "warnings": captured,
            "numeric_vote_totals_computed": False, "source_adoption": False, "forecast_consumption": False,
            "actual_parser_run": False, "network_calls": 0, "model_calls": 0, "cost_usd": 0,
            "limits": {"wall_seconds": 120, "CPU_seconds": 120, "source_bytes": source["bytes"], "output_bytes": 65536},
            "limitation": "Inspection of a proposal on one reader/runtime; no independent methods, parser, numeric, candidate/class/date or scientific acceptance. Header/footer formatting warnings do not qualify print layout."}


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (119, 120))
    def expired(*_):
        raise RuntimeError("FEC_MAPPING_INSPECTION_DEADLINE")
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGXCPU, expired)
    signal.setitimer(signal.ITIMER_REAL, 120)
    result = inspect()
    body = json.dumps(result, sort_keys=True, indent=2, allow_nan=False)
    assert len(body.encode()) <= 65536
    print(body)
