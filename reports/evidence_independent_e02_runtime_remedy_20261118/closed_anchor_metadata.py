"""Closed-capture metadata/anchor check; no owner construction or replay."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import resource
import signal
import sqlite3

ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (59, 60))
    signal.alarm(60)
    path = ROOT / "scripts/profile_e02_runtime_remedy_v1_20261118.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "fadce8c30c8d0764cf96c04f57c8627ca619ac2f82045b0637a7fadef597df67"
    spec = importlib.util.spec_from_file_location("closed_capture_only", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = module.capture()
    record = next(r for r in records if r["raw"].startswith(b"SQLite format 3\0"))
    with sqlite3.connect(":memory:") as db:
        db.deserialize(record["raw"])
        rows = {key: json.loads(data) for key, data in db.execute("SELECT id,data FROM charges")}
        event = json.loads(db.execute("SELECT data FROM events WHERE sequence=1185").fetchone()[0])
        source_receipt = event["body"]["payload"]["after"]["id"]
        events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    db.close()
    prior = {key: row for key, row in rows.items() if key != source_receipt}
    holds = {key: digest(row) for key, row in prior.items() if row["status"] != "PHASE_COMMITTED"}
    tree = ast.parse((ROOT / "src/civiclab/e02/wrapper_crossmodel_canary_v1_owner.py").read_text())
    anchor = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ANCHOR" for t in node.targets))
    assert len(rows) == 195 and len(prior) == 194 and events == 1189
    assert digest(prior) == anchor["rows"]
    assert len(holds) == 5 and digest(holds) == anchor["protected"]
    assert sum(row["status"] != "PHASE_COMMITTED" for row in rows.values()) == 6
    assert sum(row["charged"] for row in rows.values()) == 17152
    last = rows[source_receipt]
    assert last["status"] == "UNCERTAIN" and last["reserved"] == last["charged"] == 1003
    print(json.dumps({"kind": "INDEPENDENT_CLOSED_1189_ANCHOR_METADATA_V1", "status": "PASS_METADATA_NOT_OWNER_REPLAY",
                      "rows": 195, "events": 1189, "prior_rows": 194, "prior_rows_match_immutable_anchor": True,
                      "five_prior_holds_match_immutable_anchor": True, "closed_unfinished_holds": 6,
                      "closed_conservative_exposure_microusd": 17152, "closed_last_uncertain_hold_microusd": 1003,
                      "reads_charged_by_capture_helper": module.M["reads"],
                      "normal_owner_calls": 0, "network_calls": 0, "model_calls": 0,
                      "source_mutations": 0, "raw_data_exported": False,
                      "limitation": "Metadata matches the exact source constants enforced by each normal integration verifier. This is not a passed direct final mock receipt-identity comparison or a normal1189 owner replay."}, sort_keys=True))
