"""Earn complexity only on matched units, inputs, outcomes and compute."""
from .common import canonical_hash

MODULES = {
    "E01": "Retrospective forecasting",
    "E02": "Controlled synthetic information effects",
    "E03": "Synthetic city (deferred)",
    "E04": "Government AI reliability (deferred)",
}


def compare_gate(simple, advanced, *, require_equal_compute=False):
    required = ("evaluation_units", "outcome", "split_hash", "input_cutoff", "instrument_hash")
    reasons = []
    for field in required:
        if field not in simple or field not in advanced or simple[field] != advanced[field]:
            reasons.append("unmatched " + field)
    if require_equal_compute and ("token_budget" not in simple or
                                 simple.get("token_budget") != advanced.get("token_budget")):
        reasons.append("unmatched token_budget")
    for run in (simple, advanced):
        if run.get("status") != "PASS":
            reasons.append("comparison run not passed")
        if not run.get("artifact_sha256"):
            reasons.append("missing comparison artifact")
    return {"status": "PASS" if not reasons else "BLOCKED", "reasons": reasons,
            "comparison_hash": canonical_hash([simple, advanced]),
            "interpretation": "Eligibility to assess incremental value; not proof of superiority."}
