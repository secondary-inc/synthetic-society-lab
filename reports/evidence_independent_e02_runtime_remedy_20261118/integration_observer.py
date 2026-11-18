"""One unmodified frozen profile invocation with read-only ledger comparison."""
from pathlib import Path
import hashlib
import importlib.util
import json
import resource
import signal
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "scripts/profile_e02_runtime_remedy_v1_20261118.py"
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest() == "fadce8c30c8d0764cf96c04f57c8627ca619ac2f82045b0637a7fadef597df67"
spec = importlib.util.spec_from_file_location("independently_observed_frozen_profile", PROFILE)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
original_rows = None
replaced_receipt = None
checks = None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def hold_signature(rows):
    fields = ("status", "reserved", "charged", "generation_id", "observed_cost", "billing")
    return {key: {field: row[field] for field in fields}
            for key, row in rows.items() if row["status"] != "PHASE_COMMITTED"}


def trace(frame, event, argument):
    global original_rows, replaced_receipt, checks
    if frame.f_code.co_filename != str(PROFILE) or frame.f_code.co_name != "main":
        return None
    if event == "line" and original_rows is None and "dbrecord" in frame.f_locals:
        # This happens before the original script creates/rewinds its fixture or
        # installs its audit hook. No actual owner path is opened by SQLite.
        raw = frame.f_locals["dbrecord"]["raw"]
        with sqlite3.connect(":memory:") as db:
            db.deserialize(raw)
            serialized = db.execute("SELECT id,data FROM charges").fetchall()
            original_rows = {key: json.loads(data) for key, data in serialized}
            last = json.loads(db.execute("SELECT data FROM events WHERE sequence=1185").fetchone()[0])
            replaced_receipt = last["body"]["payload"]["after"]["id"]
        db.close()
        profile.add("reads", len(raw) + sum(len(data.encode()) for _, data in serialized))
        assert len(original_rows) == 195 and len(hold_signature(original_rows)) == 6
    if event == "return":
        assert argument == 0
        current = frame.f_locals["state"]["rows"]
        expected_prior = {key: row for key, row in original_rows.items() if key != replaced_receipt}
        actual_prior = {key: row for key, row in current.items() if key != replaced_receipt}
        expected_holds, actual_holds = hold_signature(original_rows), hold_signature(current)
        assert len(current) == 195 and len(expected_prior) == 194
        assert expected_prior == actual_prior
        assert expected_holds == actual_holds
        assert frame.f_locals["state"]["consumed"]["total"] == 17152
        assert frame.f_locals["state"]["unfinished"] == 6
        checks = {"kind": "INDEPENDENT_CLOSED_LEDGER_COMPARISON_V1", "prior_194_rows_identical": True,
                  "six_hold_identities_and_financial_signatures_identical": True,
                  "prior_rows_sha256": hashlib.sha256(canonical(expected_prior)).hexdigest(),
                  "hold_signatures_sha256": hashlib.sha256(canonical(expected_holds)).hexdigest(),
                  "conservative_exposure_microusd": 17152, "unfinished_holds": 6,
                  "normal_owner_extra_verify_calls": 0, "raw_data_exported": False,
                  "limitation": "Six financial signatures compared to closed capture. Last row is a retrospective inert reconstruction; it is not a real retry or proof of actual transport outcome."}
        sys.settrace(None)
    return trace


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (599, 600))
    signal.alarm(900)
    sys.settrace(trace)
    code = profile.main("remedy_failure")
    assert checks is not None
    print(json.dumps(checks, sort_keys=True))
    raise SystemExit(code)
