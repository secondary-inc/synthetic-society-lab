"""Dated public checkpoint; never reads the live owner, keys or raw responses."""
from decimal import Decimal
from hashlib import sha256
from html import escape
import json
from pathlib import Path


SOURCES = {
    'partial': ('reports/E02_WRAPPER_CROSSMODEL_STOPPED_ACTUAL_20261116.json',
                '21ec7483ee0f2e91633b30c76b9fe196e27c5768c8a0131c36e0ae14ce0c6baf'),
    'partial_review': ('reports/INDEPENDENT_AUDIT_E02_WRAPPER_CROSSMODEL_STOPPED_ACTUAL_20261116.json',
                       'e856a477ae56adf13ca44b01c7f0a00f7807a305675c262117a627c09b63672d'),
    'stop_review': ('reports/INDEPENDENT_AUDIT_E02_CANARY_ACTUAL_STOP_20261117.json',
                    '4b30219fc437f57d6edfc4db9c558db83f38bba366e50fa7b9c534a1630a4698'),
    'e01_review': ('reports/INDEPENDENT_AUDIT_E01_SAVED_JSON_ACTUAL_20261118.json',
                   '8719b82b0356e0b42af96bf312291ea4ed42942c2b24c1cb11cb8986d7e2066a'),
}


def projection(root):
    records = {}
    for name, (path, digest) in SOURCES.items():
        with (Path(root) / path).open('rb') as stream:
            raw = stream.read(100_001)
        if len(raw) > 100_000 or sha256(raw).hexdigest() != digest:
            raise ValueError('Checkpoint evidence changed or missing acceptance')
        records[name] = json.loads(raw)
    partial, review, stop, e01 = (records[k] for k in SOURCES)
    if (review['decision'] != 'PASS_PARTIAL_RETAINED_EVIDENCE_ACCOUNTING_AND_REPLAY_ONLY'
            or stop['scope_decisions']['conservative_hold_preservation'] != 'PASS'
            or e01['status'] != 'PASS'):
        raise ValueError('Checkpoint scope is not independently accepted')
    totals = partial['research_totals_including_incomplete_prefix']
    accounting = stop['accounting']
    if (totals['responses'] != accounting['previous_verified_responses']
            or totals['verified_model_usage_USD'] != accounting['previous_verified_usage_USD']
            or accounting['new_verified_responses'] != 0):
        raise ValueError('Checkpoint totals disagree')
    # Explicit aggregate allowlist. Never export whole reports or their evidence paths.
    return {
        'recorded_date': 'November 18, 2026 · Eastern time',
        'full_contract': 'INCOMPLETE',
        'completed_studies': totals['completed_studies'],
        'verified_responses': totals['responses'],
        'verified_usage_usd': totals['verified_model_usage_USD'],
        'exposure_usd': format(Decimal(accounting['current_conservative_exposure_microusd']) / Decimal(1_000_000), '.6f'),
        'fifth_responses': partial['committed_responses'],
        'fifth_planned_maximum': partial['planned_model_POSTs_maximum'],
        'fifth_complete': partial['research_study_complete'],
        'latest_attempt_status': 'STOPPED_CPU_LIMIT_NO_SAVED_RESPONSE_OR_BILL',
        'provider_outcome': stop['scope_decisions']['provider_HTTP_completion'],
        'provider_charge': stop['scope_decisions']['provider_charge'],
        'uncertain_holds_count': len(accounting['old_holds_microusd']) + 1,
        'new_hold_usd': format(Decimal(accounting['new_hold_microusd']) / Decimal(1_000_000), '.6f'),
        'e01': {key: e01['metrics'][key] for key in (
            'regular_frame_slots', 'document_state_coverage_count',
            'remaining_document_acquisition_jobs', 'final_ballots_accepted')},
        'sources': [{'path': path, 'sha256': digest} for path, digest in SOURCES.values()],
    }


def render(s):
    h = lambda value: escape(str(value), quote=True)
    e = s['e01']
    sources = ''.join(f'<li><code>{h(x["path"])}</code><br><small>{h(x["sha256"])}</small></li>'
                      for x in s['sources'])
    return f'''<section class="live-main" aria-labelledby="checkpoint-title">
<div class="live-topline"><span class="live-kicker">Recorded {h(s['recorded_date'])}</span><span class="live-pill live-neutral">FULL RESEARCH CONTRACT INCOMPLETE</span></div>
<h2 id="checkpoint-title">Four completed studies; fifth study incomplete</h2>
<p class="live-deck">This saved checkpoint summarizes verified model work. It is not a live account balance or evidence about human persuasion.</p>
<div class="live-cards">
<div class="live-card"><div class="live-value">{h(s['verified_responses'])}</div><div class="live-label">Verified model responses across separate studies</div></div>
<div class="live-card"><div class="live-value">{h(s['fifth_responses'])} / {h(s['fifth_planned_maximum'])}</div><div class="live-label">Fifth study responses / planned maximum</div></div>
<div class="live-card"><div class="live-value">${h(s['verified_usage_usd'])}</div><div class="live-label">Verified research model-usage invoices</div></div>
<div class="live-card"><div class="live-value">${h(s['exposure_usd'])}</div><div class="live-label">Conservative exposure, including unresolved holds</div></div>
</div>
<div class="live-warning"><strong>Latest attempt stopped at its CPU limit.</strong> No new response or bill was saved. Provider outcome: {h(s['provider_outcome'])}; provider charge: {h(s['provider_charge'])}. The full ${h(s['new_hold_usd'])} reservation remains held, alongside all earlier holds ({h(s['uncertain_holds_count'])} unresolved holds in total). A dispatch intent does not prove receipt by the provider. Consumed attempts must not be replayed.</div>
<p class="live-note">The fifth study's full registered comparison remains unperformed. Partial response counts are not a treatment-effect estimate. Four completed study results remain separate below; their dated cost totals are historical checkpoints. Local compute and agent labor are unpriced.</p>
<section class="live-panel"><h3>E01: saved source-readiness data read successfully</h3>
<p>{h(e['regular_frame_slots'])} frame slots · {h(e['document_state_coverage_count'])} states with documents · {h(e['remaining_document_acquisition_jobs'])} acquisition jobs remaining · {h(e['final_ballots_accepted'])} accepted final ballots.</p>
<p class="live-note">The independently reviewed offline read cost $0 and made no model requests. It does not accept ballots, choose races or produce a forecast. E01 remains retrospective; population calibration, human anchoring and full research gates remain open.</p></section>
<details class="live-panel" style="margin-top:18px"><summary>Checkpoint provenance</summary><p class="live-note">Built only from four pinned public records. Review acceptance is limited to each record's stated scope; stopped execution remains stopped. No raw answers, credentials or live owner records are loaded.</p><ul class="live-audit">{sources}</ul></details>
</section><hr class="live-study-divider">'''
