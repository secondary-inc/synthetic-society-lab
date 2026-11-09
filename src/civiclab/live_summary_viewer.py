"""Local preview overlay from one exact independently accepted public audit.

No private run, credential, owner store or inference transport is read. The
historical viewer is retained separately and visibly dated, not recertified.
"""
from decimal import Decimal
from html import escape
import hashlib
import json
from pathlib import Path

AUDIT = 'reports/INDEPENDENT_AUDIT_E02_CONTINUATION_ACTUAL_20261108.json'
AUDIT_SHA256 = '8764359767c8ade7ad2da42d8c8f27faa19aff2a27f001cec22367c2c3bf3d8e'
AUDIT_STATUS = 'PASS_ACTUAL_LIMITED_PILOT_COMBINED_EVIDENCE_ACCOUNTING_AND_DESCRIPTIVE_RESCORING'
FOLLOWUP_AUDIT = 'reports/INDEPENDENT_AUDIT_E02_ALIGNMENT_ANCHORING_ACTUAL_20261109.json'
FOLLOWUP_SHA256 = 'cf2bed0882f71d33efd3cd755ace36cf3e58aaef0759b881c0361488a0ec7246'
FOLLOWUP_STATUS = 'PASS_ACTUAL_CLOSED_EVIDENCE_ACCOUNTING_REGISTERED_ARITHMETIC_AND_EXCLUSIONS'
START = '<!-- LIVE_SUMMARY_START -->'
END = '<!-- LIVE_SUMMARY_END -->'


def projection(root):
    """Export an allowlist of aggregate fields; never copy the audit wholesale."""
    path = Path(root) / AUDIT
    with path.open('rb') as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != AUDIT_SHA256:
        raise ValueError('Live pilot audit is changed or unreviewed')
    audit = json.loads(raw)
    if audit['status'] != AUDIT_STATUS:
        raise ValueError('Live pilot audit is not accepted')
    o = audit['oracles']
    s = audit['scientific_interpretation']
    return {
        'title': 'Completed live model pilot',
        'status': 'COMPLETE_LIMITED_EXPLORATORY_SAMPLE',
        'review': 'Independent outcome audit passed',
        'source_audit': AUDIT,
        'source_audit_sha256': AUDIT_SHA256,
        'sample_dates': 'November 5 and 8, 2026 · Eastern time',
        'responses': o['combined_valid'],
        'matched_comparisons': o['complete_blocks'],
        'excluded_comparisons': o['excluded_blocks'],
        'contrast_points': o['primary_mean_C2_minus_C1'],
        'block_contrasts': o['matched_block_differences'],
        'research_cost_usd': o['combined32_generation_cost_usd'],
        'conservative_total_microusd': o['combined_conservative_ledger_microusd'],
        'unchanged_holds_microusd': o['unchanged_holds_microusd'],
        'fictional_profiles': s['fictional_profiles'],
        'authored_notices': s['authored_DEMO_stimuli'],
        'cross_batch_comparisons': s['temporal_partition']['cross_batch'],
        'provider': 'Azure',
        'model': 'GPT-4.1 nano',
        'full_research_contract': 'INCOMPLETE',
        'followup': {
            'status': 'DESIGN_IN_REVIEW_NOT_RUN',
            'planned_calls': 28,
            'question': 'Does proposal support respond to the notice, and does showing the model its baseline anchor the answer?',
        },
    }


def followup_projection(root):
    """Only accepted aggregate outcomes, not raw answers or financial rows."""
    with (Path(root) / FOLLOWUP_AUDIT).open('rb') as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != FOLLOWUP_SHA256:
        raise ValueError('Follow-up audit is changed or unreviewed')
    a = json.loads(raw)
    if a['status'] != FOLLOWUP_STATUS:
        raise ValueError('Follow-up outcome is not independently accepted')
    return {
        'status': 'COMPLETE_WITH_PRESPECIFIED_SKIPS',
        'source_audit': FOLLOWUP_AUDIT,
        'source_audit_sha256': FOLLOWUP_SHA256,
        'planned_slots': a['planned_slots'],
        'actual_responses': a['observed_answers'],
        'skipped_posts': len(a['rule_derived_skipped_slots']),
        'primary_contrasts': a['primary_context_values'],
        'primary_mean': a['primary_mean_points'],
        'primary_contexts': len(a['primary_context_values']),
        'shown_contrasts': a['shown_eligible_context_values'],
        'paired_omitted_contrasts': a['matched_eligible_omitted_context_values'],
        'paired_omitted_mean': a['matched_eligible_omitted_mean_points'],
        'paired_interaction_mean': a['interaction_mean_points'],
        'paired_contexts': len(a['interaction_context_values']),
        'asked_comprehension_correct': a['factual_correct_all_asked'],
        'research_cost_usd': a['new_verified_generation_USD'],
        'conservative_total_microusd': a['conservative_owner_microusd'],
        'unchanged_holds_microusd': a['unchanged_uncertain_holds'],
        'intervals': a['intervals'],
        'anchoring_pattern_met': a['anchoring_compatible_frozen_pattern'],
    }


def render_followup(s):
    h = lambda x: escape(str(x), quote=True)
    rows = ''.join(
        f'<div class="live-result-row"><span>Context {i + 1}</span>'
        f'<span class="live-evidence-track"><span style="width:{float(v)}%"></span></span>'
        f'<strong>{h(v)} points</strong></div>'
        for i, v in enumerate(s['primary_contrasts'])
    )
    paired = ''.join(
        f'<tr><td>Context {i + 1}</td><td>{h(omitted)}</td><td>{h(shown)}</td><td>{h(shown - omitted)}</td></tr>'
        for i, (omitted, shown) in enumerate(zip(s['paired_omitted_contrasts'], s['shown_contrasts']))
    )
    exposure = format(Decimal(s['conservative_total_microusd']) / Decimal(1_000_000), '.6f')
    return f'''<main class="live-main" id="followup-summary">
<style>.live-evidence-track{{height:8px;background:#e7eee7;border-radius:8px;overflow:hidden}}.live-evidence-track>span{{display:block;height:100%;background:#326951}}.live-study-divider{{max-width:1200px;margin:10px auto;border:0;border-top:1px solid #cbd8cf}}</style>
<div class="live-topline"><span class="live-kicker">Latest real experiment · November 9, 2026 · Eastern time</span><span class="live-pill">COMPLETE WITH SKIPS · AUDIT PASSED</span></div>
<h2>Proposal support responded to the supplied evidence.</h2>
<p class="live-deck">A separate follow-up tested three fictional versions of one library proposal, with earlier answers shown or omitted. It changes the question and outcome from the first pilot; the two studies are not pooled.</p>
<div class="live-cards">
<div class="live-card"><div class="live-value">{h(s['actual_responses'])} / {h(s['planned_slots'])}</div><div class="live-label">Actual real-model responses</div></div>
<div class="live-card"><div class="live-value">{h(s['skipped_posts'])} skipped</div><div class="live-label">Prespecified incomplete-baseline rule</div></div>
<div class="live-card"><div class="live-value">+{h(s['primary_mean'])} points</div><div class="live-label">Positive minus negative evidence · 4 contexts</div></div>
<div class="live-card"><div class="live-value">${h(s['research_cost_usd'])}</div><div class="live-label">Verified follow-up charges</div></div>
</div><div class="live-grid"><section class="live-panel"><h3>Content comparison · baseline answer omitted</h3>
<p class="live-note">Support on a 0–100 scale: positive visit evidence minus negative visit evidence, in the same fictional proposal. All four technical contexts have a usable contrast.</p>{rows}
<p class="live-note">Mean +56.25 points; observed range +50 to +75. No confidence interval, significance test or population estimate is reported.</p></section>
<section class="live-panel"><h3>Baseline-answer cue · only 2 eligible pairs</h3>
<table><thead><tr><th>Technical context</th><th>Omitted</th><th>Shown</th><th>Shown − omitted</th></tr></thead><tbody>{paired}</tbody></table>
<p class="live-note">On these same two contexts, the omitted-cue mean is <strong>+62.5</strong>, shown-cue mean is <strong>0</strong>, and mean interaction is <strong>−62.5 points</strong>. The four-context +56.25 mean is not the comparator for this two-context result.</p>
<div class="live-warning"><strong>Why only two pairs?</strong><br>Both R-prior baseline questionnaires returned a null Democratic-party thermometer. Their six SHOWN posts were skipped under the frozen rule. Only the two D-prior contexts remain paired. This does not establish a party difference or an anchoring mechanism; the full prespecified anchoring pattern was not met.</div></section></div>
<section class="live-panel"><h3>What we learned—and what remains uncertain</h3>
<p>In this fixed model task, an issue-specific support question responded to the fictional evidence. Showing the model its entire previous answer coincided with a smaller response in the two eligible pairs. This is descriptive evidence from one model, one authored issue and four technical contexts, not a human experiment.</p>
<p class="live-note">All {h(s['asked_comprehension_correct'])} asked factual questions were answered correctly. The six skipped posts are missing planned answers, not observed comprehension mistakes. Some party thermometers were missing even when support and comprehension were usable.</p>
<p class="live-note"><strong>Current conservative ledger exposure: ${exposure}</strong>, including unchanged historical holds. Shared cap $5; cumulative E02 cap $1; E01 paid inference $0. No automatic sample extension or next paid run is implied.</p>
<details><summary>Independent follow-up audit and scope</summary><p class="live-audit">{h(s['source_audit'])}<br>SHA-256 {h(s['source_audit_sha256'])}</p><p class="live-note">Only a pinned public outcome audit is projected here. Private journals, raw answers, credentials and owner stores are not read. Full nationwide E02 and original E01 completion remain incomplete.</p></details>
</section></main><hr class="live-study-divider">'''


def render(summary):
    """Static, accessible presentation; no raw responses or remote resources."""
    h = lambda x: escape(str(x), quote=True)
    cost = '$' + h(summary['research_cost_usd'])
    exposure = '$' + format(Decimal(summary['conservative_total_microusd']) / Decimal(1_000_000), '.6f')
    rows = ''.join(
        f'<div class="live-result-row"><span>Comparison {i + 1}</span>'
        f'<span class="live-zero-line" aria-hidden="true"></span><strong>{h(value)} points</strong></div>'
        for i, value in enumerate(summary['block_contrasts'])
    )
    if summary.get('followup_result'):
        followup_section = '<section class="live-panel"><h3>First pilot retained separately</h3><p class="live-note">The completed follow-up is shown above. This earlier wrapper pilot keeps its original outcome, sample and historical accounting checkpoint. Its zero result has not been replaced or pooled with the follow-up.</p></section>'
    else:
        followup_section = f'<section class="live-panel live-next"><div class="live-next-text"><span class="live-kicker">Next research step</span><h3>Test measurement alignment and baseline anchoring.</h3><p>{h(summary["followup"]["question"])}</p><p class="live-note">Proposed 28-call follow-up: four baselines and 24 post-exposure answers. Design and execution review are still required. No follow-up results are displayed here.</p></div><span class="live-pill live-neutral">DESIGN IN REVIEW · NOT RUN</span></section>'
    return f'''{START}
<style>
.live-main{{max-width:1248px;margin:auto;padding:28px 24px}}
.live-topline{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:20px}}
.live-pill{{background:#d9ebde;color:#164d36;border-radius:30px;padding:7px 12px;font-size:12px;font-weight:650}}
.live-kicker{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:#526c63}}
.live-main h2{{font-size:30px;margin:8px 0 12px;letter-spacing:-.6px}}
.live-deck{{max-width:800px;color:#526c63;margin:0 0 24px}}
.live-cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:22px 0}}
.live-card{{background:#fff;border:1px solid #dce3db;border-radius:7px;padding:20px}}
.live-value{{font-size:29px;line-height:1.4;color:#153d39;font-weight:600}}
.live-label{{font-size:12px;color:#526c63;margin-top:6px}}
.live-grid{{display:grid;grid-template-columns:1.25fr 1fr;gap:18px;margin:20px 0}}
.live-panel{{background:white;border:1px solid #dce3db;padding:24px;border-radius:7px;min-width:0}}
.live-panel h3{{font-size:18px;margin:0 0 14px}}
.live-result-row{{display:grid;grid-template-columns:112px 1fr 65px;gap:14px;align-items:center;font-size:12px;padding:9px 0;border-bottom:1px solid #edf1eb}}
.live-zero-line{{height:1px;background:#c8d7cc;position:relative}}
.live-zero-line:after{{content:'';width:7px;height:7px;border-radius:50%;background:#326951;position:absolute;left:50%;top:-3px}}
.live-note{{font-size:13px;color:#526c63;line-height:1.65}}
.live-warning{{border-left:3px solid #ab701b;background:#fff3d7;padding:15px 18px;margin-top:18px;font-size:13px;line-height:1.65}}
.live-next{{display:flex;gap:24px;align-items:start;justify-content:space-between;flex-wrap:wrap}}
.live-next-text{{max-width:820px}}
.live-neutral{{background:#e9edf0;color:#3b5360}}
.live-audit{{font:11px/1.7 ui-monospace,monospace;overflow-wrap:anywhere}}
.historical-preview{{max-width:1248px;margin:16px auto 32px;padding:0 24px}}
.historical-preview>summary{{padding:18px;background:#e5ece5;border-radius:5px;color:#526c63}}
.historical-preview>main{{padding-left:0;padding-right:0}}
@media(max-width:850px){{.live-cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.live-grid{{grid-template-columns:1fr}}}}
@media(max-width:480px){{.live-main{{padding:20px 12px}}.live-card{{padding:14px}}.live-value{{font-size:24px}}.live-panel{{padding:18px}}.live-main h2{{font-size:25px}}}}
</style>
<main class="live-main" id="live-pilot-summary">
<div class="live-topline"><span class="live-kicker">Current evidence · {h(summary['sample_dates'])}</span><span class="live-pill">REAL MODEL RUN · AUDIT PASSED</span></div>
<h2>The first live pilot is complete.</h2>
<p class="live-deck">All planned answers are scored. This small exploratory run compares the same fictional notices in news and social wrappers. The full research program remains incomplete.</p>
<div class="live-cards">
<div class="live-card"><div class="live-value">{h(summary['responses'])} / 32</div><div class="live-label">Valid real-model answers</div></div>
<div class="live-card"><div class="live-value">{h(summary['matched_comparisons'])} / 8</div><div class="live-label">Complete matched comparisons</div></div>
<div class="live-card"><div class="live-value">{h(summary['contrast_points'])} points</div><div class="live-label">Observed mean difference in changes</div></div>
<div class="live-card"><div class="live-value">{cost}</div><div class="live-label">Verified research charges</div></div>
</div>
<div class="live-grid"><section class="live-panel"><h3>What did we observe?</h3>
<p class="live-note">Every recorded within-arm change and all eight wrapper contrasts were zero on the partisan feeling-thermometer measure.</p>{rows}
<p class="live-note">Zero observed change in this sample does not establish that presentation never matters. The descriptive bootstrap interval [0, 0] is degenerate, not an equivalence result.</p></section>
<section class="live-panel"><h3>What does it establish?</h3>
<p>The bounded live pipeline completed its sample: real inference, retained responses, verified billing and independently checked scoring.</p>
<p class="live-note">{h(summary['fictional_profiles'])} fictional profiles · {h(summary['authored_notices'])} authored DEMO notices · {h(summary['model'])} through {h(summary['provider'])}. These are real model answers to fictional content, not human study results.</p>
<div class="live-warning"><strong>Interpretation limits</strong><br>{h(summary['cross_batch_comparisons'])} of eight comparisons cross execution dates. Baseline-answer anchoring and weak content–measure alignment remain possible. No human, national, causal wrapper-effect or confirmatory claim is supported.</div>
<p class="live-note"><strong>Ledger exposure at first-pilot checkpoint: {exposure}</strong><br>Historical checkpoint including retained holds, distinct from verified research charges and the latest total above. Existing shared cap $5; E02 cap $1; E01 paid inference $0.</p></section></div>
{followup_section}
<details class="live-panel" style="margin-top:18px"><summary>Independent evidence and scope</summary><p class="live-note">This section reads one pinned, accepted public outcome audit. Private journals, credentials and respondent records are not read or exported. This page is a saved snapshot, not a live experiment controller.</p><p class="live-audit">{h(summary['source_audit'])}<br>SHA-256 {h(summary['source_audit_sha256'])}</p></details>
</main>
{END}'''


def build(root, output):
    """Preserve the old viewer and add a public-summary overlay, idempotently."""
    output = Path(output)
    index = output / 'index.html'
    archive = output / 'historical-preview.html'
    summary = projection(root)  # Refuse altered evidence before touching files.
    followup = followup_projection(root)
    summary['followup_result'] = followup
    summary['followup']['status'] = followup['status']
    source = archive if archive.exists() else index
    original_bytes = source.read_bytes()
    base = original_bytes.decode('utf-8')
    if START in base or base.count('<main>') != 1 or base.count('</main>') != 1:
        raise ValueError('Unexpected historical preview structure')
    page = base.replace('<main>', render_followup(followup) + render(summary) + '\n<details class="historical-preview"><summary>Historical snapshot · November 3 recorded runs and completion receipts</summary><main>', 1)
    # The new overlay has its own main; close only the historical main.
    pos = page.rfind('</main>')
    page = page[:pos] + '</main></details>' + page[pos + len('</main>'):]
    if not archive.exists():
        with archive.open('xb') as stream:
            stream.write(original_bytes)
    from .common import atomic_json
    atomic_json(output / 'live-summary.json', summary)
    # Historical snapshot.json stays byte-for-byte unchanged and separately dated.
    temporary = output / 'live-preview-index.tmp'
    temporary.write_text(page)
    temporary.replace(index)
    return index
