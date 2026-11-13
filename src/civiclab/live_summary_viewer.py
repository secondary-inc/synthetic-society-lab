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
CROSSMODEL_AUDIT = 'reports/INDEPENDENT_AUDIT_E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json'
CROSSMODEL_AUDIT_SHA256 = 'ea7fece4bf153eef45ec067ef8ce9753b874e53b644d2a51505add4c5820bcfd'
CROSSMODEL_STATUS = 'PASS_SCOPED_ACTUAL_EXPLORATORY_EVIDENCE_ACCOUNTING_AND_REGISTERED_SCORES'
CROSSMODEL_AGGREGATE = 'reports/E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json'
CROSSMODEL_AGGREGATE_SHA256 = 'b7269ba6c0a828c907a50b2de8b67d45dc8d4714efb8de8ccb90acba99467fb0'
WRAPPER_AUDIT = 'reports/INDEPENDENT_AUDIT_E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json'
WRAPPER_AGGREGATE = 'reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json'
# Exact separate actual-evidence PASS; the aggregate retains its build-time pending field.
WRAPPER_AUDIT_SHA256 = 'a713b6b298b3c37979486d5b167880e836081675edc8d049b05e67d23c30a475'
WRAPPER_AGGREGATE_SHA256 = 'fd4a4a25e3138aa963c32bdd26c6120ef2b43a4b66deee7ca63dab272d0ab964'
WRAPPER_AUDIT_STATUS = 'PASS_SCOPED_ACTUAL_EVIDENCE_ACCOUNTING_MATCHED_SCORING_AND_LIMITATIONS'
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


def crossmodel_projection(root):
    """Admit an exact accepted public audit and its exact aggregate only."""
    def read(path, digest):
        with (Path(root) / path).open('rb') as stream:
            raw = stream.read(1_000_001)
        if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Cross-model public evidence is changed or unreviewed')
        return json.loads(raw)
    audit = read(CROSSMODEL_AUDIT, CROSSMODEL_AUDIT_SHA256)
    if audit['status'] != CROSSMODEL_STATUS or audit['reviewed_public_aggregate']['path'] != CROSSMODEL_AGGREGATE or audit['reviewed_public_aggregate']['sha256'] != CROSSMODEL_AGGREGATE_SHA256:
        raise ValueError('Cross-model actual outcome is not accepted')
    a = read(CROSSMODEL_AGGREGATE, CROSSMODEL_AGGREGATE_SHA256)
    s = crossmodel_summary(a)
    s.update(source_audit=CROSSMODEL_AUDIT, source_audit_sha256=CROSSMODEL_AUDIT_SHA256,
             source_aggregate=CROSSMODEL_AGGREGATE, source_aggregate_sha256=CROSSMODEL_AGGREGATE_SHA256)
    return s


def crossmodel_summary(a):
    """Project public aggregates only; receipt admission is the caller's job.

    Never copy scored phase records, raw answers, generation IDs or source paths.
    Build uses this only after exact audit and aggregate admission.
    """
    analysis = a['analysis']
    phases = analysis['phase_counts']
    allowed = {'ANSWER', 'SKIPPED_INVALID_PRE', 'FAILED_UNCERTAIN',
               'PARSE_ERROR', 'CANCELLED', 'NOT_ATTEMPTED'}
    if set(phases) - allowed:
        raise ValueError('Unrecognized cross-model phase disposition')
    models = []
    for key, name in (('A', 'A · GPT-4.1 nano / Azure'),
                      ('B', 'B · Qwen3-30B-A3B-Instruct-2507 / Nebius')):
        m = analysis['models'][key]
        factual = [m['baseline_quality']['comprehension'],
                   m['comprehension']['OMITTED'], m['comprehension']['SHOWN']]
        unasked = sum(f['quality_counts'].get('UNASKED', 0) for f in factual)
        asked = sum(f['planned'] for f in factual) - unasked
        valid = sum(f['valid'] for f in factual)
        model = dict(name=name, factual_asked=asked,
                     factual_correct=sum(f['correct'] for f in factual),
                     factual_errors=sum(f['observed_factual_errors'] for f in factual),
                     factual_missing_invalid=asked - valid, unasked_slots=unasked,
                     support_missing_null=sum(q['count'] for q in m['item_quality_counts']
                                              if q['item'] == 'library_support' and q['quality'] == 'MISSING_NULL'),
                     attenuation_pattern_met=m['prespecified_patterns']['attenuation_in_this_configuration'])
        for target, source in (('omitted', m['content_contrasts']['OMITTED']),
                               ('shown', m['content_contrasts']['SHOWN']),
                               ('interaction', m['primary_cue_interaction'])):
            model[target] = dict(mean=source['mean_points'], complete=source['complete_contexts'])
        models.append(model)
    c = analysis['crossmodel_common_context_interaction_difference']
    return dict(models=models, sample_dates='November 10, 2026 · Eastern time',
                actual_responses=phases.get('ANSWER', 0), planned_slots=a['design']['planned_total_study_model_POSTs'],
                skipped_slots=phases.get('SKIPPED_INVALID_PRE', 0),
                failed_slots=phases.get('FAILED_UNCERTAIN', 0),
                parse_error_slots=phases.get('PARSE_ERROR', 0),
                cancelled_slots=phases.get('CANCELLED', 0),
                unattempted_slots=phases.get('NOT_ATTEMPTED', 0),
                research_cost_usd=a['billing']['verified_combined_study_USD'],
                all_research_cost_usd=a['billing']['all_research_verified_USD'],
                conservative_exposure_usd=format(Decimal(a['billing']['conservative_owner_exposure_microusd']) / Decimal(1_000_000), '.6f'),
                full_pattern_met=analysis['prespecified_patterns']['attenuation_across_both_fixed_configurations'],
                crossmodel=dict(mean=c['mean_points'], complete=c['complete_contexts'],
                                context_values=[{k: row[k] for k in ('A_value', 'B_value', 'value')} for row in c['context_values']]),
                recovery_note='Two exact saved baselines were reused across an execution gap; 51 new answers were collected without prompt retries. Four historical financial holds remain unchanged, including the recovered Qwen baseline hold. A reported-null Qwen service tier remains unknown.')


def render_crossmodel(s):
    """Render a normalized accepted aggregate; callers bind its public receipt.

    This helper does not read files or compute study estimands.
    """
    h = lambda x: escape(str(x), quote=True)
    def point(value):
        if value is None:
            return 'Not estimable'
        return h(('+' if value > 0 else '') + format(value, '.2f').rstrip('0').rstrip('.'))
    rows = []
    for model in s['models']:
        rows.append('<tr><td><strong>' + h(model['name']) + '</strong></td>' + ''.join(
            '<td>' + point(model[key]['mean']) + '<br><span class="live-note">'
            + h(model[key]['complete']) + ' / 4 contexts</span></td>'
            for key in ('omitted', 'shown', 'interaction')
        ) + '</tr>')
    context_rows = []
    for i, row in enumerate(s['crossmodel']['context_values']):
        context_rows.append(f'<tr><td>Context {i + 1}</td><td>{point(row["A_value"])}</td><td>{point(row["B_value"])}</td><td>{point(row["value"])}</td></tr>')
    factual_rows = ''.join(
        '<tr><td>' + h(m['name']) + '</td><td>' + h(m['factual_correct']) + ' / '
        + h(m['factual_asked']) + '</td><td>' + h(m['factual_errors'])
        + '</td><td>' + h(m['factual_missing_invalid'])
        + '</td><td>' + h(m['unasked_slots']) + '</td></tr>' for m in s['models']
    )
    return f'''<main class="live-main" id="crossmodel-summary">
<div class="live-topline"><span class="live-kicker">Support-only cue study · {h(s['sample_dates'])}</span><span class="live-pill">REAL MODEL EVIDENCE · AUDIT PASSED</span></div>
<h2>The same fixed design, two model configurations.</h2>
<p class="live-deck">This separate study shows only the model's own issue-support rating, rather than its whole previous questionnaire. It does not pool its outcomes with either earlier study.</p>
<div class="live-cards">
<div class="live-card"><div class="live-value">{h(s['actual_responses'])} / {h(s['planned_slots'])}</div><div class="live-label">Observed answers / planned slots</div></div>
<div class="live-card"><div class="live-value">{h(s['skipped_slots'])} skipped</div><div class="live-label">Rule-derived skips only · {h(s['failed_slots'])} failed/uncertain · {h(s['parse_error_slots'])} parse errors · {h(s['cancelled_slots'])} cancelled · {h(s['unattempted_slots'])} unattempted</div></div>
<div class="live-card"><div class="live-value">{h(s['crossmodel']['complete'])} / 4</div><div class="live-label">Common complete contexts for B − A</div></div>
<div class="live-card"><div class="live-value">${h(s['research_cost_usd'])}</div><div class="live-label">Verified charges for this distinct study</div></div>
</div>
<section class="live-panel"><h3>Signed support contrasts, in points</h3>
<p class="live-note">Content contrast = support with positive evidence − support with negative evidence. Primary cue interaction = SHOWN contrast − OMITTED contrast. Each cell carries its own complete-case denominator.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Model / provider configuration</th><th>OMITTED content contrast</th><th>SHOWN content contrast</th><th>Primary cue interaction</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="live-warning"><strong>A signed interaction is not automatically attenuation.</strong><br>A negative interaction can include a reversal of the content contrast. Inspect both signed content contrasts; no psychological anchoring mechanism or model-family effect is established here.</div></section>
<div class="live-grid"><section class="live-panel"><h3>Cross-model comparison · common contexts only</h3>
<p class="live-note">B − A cue-interaction difference: <strong>{point(s['crossmodel']['mean'])} points</strong>, across {h(s['crossmodel']['complete'])} common complete contexts. This is not subtraction of model means with different eligible samples.</p>
<table><thead><tr><th>Technical context</th><th>A interaction</th><th>B interaction</th><th>B − A</th></tr></thead><tbody>{''.join(context_rows)}</tbody></table>
<p class="live-note">No confidence interval, p-value, equivalence test or independent-person sample size is claimed.</p></section>
<section class="live-panel"><h3>Missingness and comprehension</h3>
<table><thead><tr><th>Configuration</th><th>Factual correct / asked</th><th>Observed factual errors</th><th>Missing / invalid factual items among asked</th><th>Unasked slots</th></tr></thead><tbody>{factual_rows}</tbody></table>
<p class="live-note">Incorrect observed answers, missing items, rule-derived skips and unattempted slots are separate dispositions. Unrelated missing thermometer answers do not by themselves invalidate usable issue support in this study.</p>
<p class="live-note">Configuration A returned three null issue-support answers, including one baseline that caused three SHOWN skips. Factual comprehension remained correct in those observed answers; missing support is not a factual error.</p>
<p class="live-note">{h(s['recovery_note'])}</p></section></div>
<section class="live-panel"><h3>Scope and accounting</h3><p class="live-note">Four authored technical contexts, one fictional issue and two fixed model/provider configurations. Provider, tokenization and quantization differences are not isolated as causal factors. No human-persuasion, nationwide-population or family-wide robustness claim follows.</p>
<p class="live-note">The full prespecified cross-configuration attenuation pattern was not met: configuration A lacks a complete four-context primary sample. Configuration B met its within-configuration descriptive pattern. These flags do not establish an anchoring mechanism.</p>
<p class="live-note">All seven complete pairs contracted in absolute magnitude with no observed reversal. This descriptive observation is separate from the incomplete full registered pattern. Verified research charges across the three distinct studies total <strong>${h(s['all_research_cost_usd'])}</strong>.</p>
<p class="live-note">Provider telemetry reports streaming despite non-streaming client requests; this discrepancy remains unresolved. Complete parsed responses and their request/billing bindings were verified. Null Qwen service tiers remain unknown.</p>
<p class="live-note">Conservative cumulative ledger exposure: <strong>${h(s['conservative_exposure_usd'])}</strong>, including retained historical holds. Shared cap $5, cumulative E02 cap $1 and E01 paid inference $0 remain unchanged.</p>
<details><summary>Accepted public evidence</summary><p class="live-audit">{h(s['source_audit'])}<br>SHA-256 {h(s['source_audit_sha256'])}</p><p class="live-note">Aggregate allowlist only. Private responses, owner stores and credentials are not exported.</p></details></section>
</main><hr class="live-study-divider">'''


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
<div class="live-topline"><span class="live-kicker">Earlier issue-aligned experiment · November 9, 2026 · Eastern time</span><span class="live-pill">COMPLETE WITH SKIPS · AUDIT PASSED</span></div>
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
<p class="live-note"><strong>Historical November 9 ledger checkpoint: ${exposure}</strong>, including unchanged historical holds. Shared cap $5; cumulative E02 cap $1; E01 paid inference $0. No automatic sample extension or next paid run is implied.</p>
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


def wrapper_summary(a):
    """Explicit public aggregate allowlist; not evidence admission or rescoring."""
    analysis = a['analysis']
    phases = analysis['phase_counts']
    allowed = {'ANSWER', 'SKIPPED_INVALID_PRE', 'FAILED_UNCERTAIN', 'PARSE_ERROR', 'CANCELLED', 'NOT_ATTEMPTED'}
    if set(phases) - allowed or any(type(v) is not int or v < 0 for v in phases.values()):
        raise ValueError('Unrecognized wrapper disposition')
    def summary(x):
        return dict(mean=x['mean_points'], complete=x['complete_units'], planned=x['planned_units'])
    def key(row):
        return row['profile_id'], row['topic_id']
    primary = analysis['primary_wrapper_omitted']
    shown = analysis['wrapper_contrasts']['SHOWN']
    interaction = analysis['visibility_interaction']
    magnitude = analysis['absolute_wrapper_magnitude_change']
    lookup = [{key(row): row['value'] for row in value['unit_values']}
              for value in (shown, interaction, magnitude)]
    if any(len(table) != len(value['unit_values']) for table, value in zip(lookup, (shown, interaction, magnitude))):
        raise ValueError('Duplicate wrapper unit')
    primary_keys = [key(row) for row in primary['unit_values']]
    if len(set(primary_keys)) != len(primary_keys) or any(set(table) != set(primary_keys) for table in lookup):
        raise ValueError('Wrapper unit identities differ')
    topic_names = {'LIBRARY': 'Library', 'TRANSIT': 'Transit'}
    rows = []
    for number, row in enumerate(primary['unit_values'], 1):
        if row['topic_id'] not in topic_names:
            raise ValueError('Unreviewed wrapper topic')
        k = key(row)
        rows.append(dict(unit=number, topic=topic_names[row['topic_id']], omitted=row['value'],
                         shown=lookup[0][k], interaction=lookup[1][k], magnitude_change=lookup[2][k]))
    magnitude_values = [r['magnitude_change'] for r in rows if r['magnitude_change'] is not None]
    factual = a['all_planned_factual_dispositions']
    known_factual = {'CORRECT', 'INCORRECT', 'MISSING_KEY', 'MISSING_NULL', 'INVALID',
                     'INVALID_SHAPE', 'PARSE_ERROR', 'FAILED_UNCERTAIN', 'CANCELLED', 'UNASKED'}
    if set(factual) - known_factual or any(type(v) is not int or v < 0 for v in factual.values()):
        raise ValueError('Unrecognized wrapper factual disposition')
    planned = a['design']['maximum_model_POSTs']
    if sum(phases.values()) != planned or sum(factual.values()) != planned:
        raise ValueError('Wrapper planned disposition total differs')
    correct = factual.get('CORRECT', 0)
    errors = factual.get('INCORRECT', 0)
    asked = planned - factual.get('UNASKED', 0)
    return dict(sample_dates='November 12, 2026 · 7:50–8:05 p.m. EST (November 13 UTC)',
        actual_responses=phases.get('ANSWER', 0), planned_slots=planned,
        skipped_slots=phases.get('SKIPPED_INVALID_PRE', 0), failed_slots=phases.get('FAILED_UNCERTAIN', 0),
        parse_error_slots=phases.get('PARSE_ERROR', 0), cancelled_slots=phases.get('CANCELLED', 0),
        unattempted_slots=phases.get('NOT_ATTEMPTED', 0),
        primary=summary(primary), shown=summary(shown), interaction=summary(interaction),
        magnitude=summary(magnitude), units=rows,
        matched_omitted=summary(analysis['matched_wrapper_contrasts']['OMITTED']),
        matched_shown=summary(analysis['matched_wrapper_contrasts']['SHOWN']),
        expansion_count=sum(v > 0 for v in magnitude_values),
        contraction_count=sum(v < 0 for v in magnitude_values),
        unchanged_magnitude_count=sum(v == 0 for v in magnitude_values),
        reversal_count=analysis['direction_diagnostics']['sign_reversal_count'],
        primary_by_topic=[dict(topic=topic_names[t], **summary(analysis['primary_by_topic'][t]))
                          for t in ('LIBRARY', 'TRANSIT')],
        all_items_valid=all(q['quality'] == 'VALID' for q in analysis['item_quality_counts']) and sum(q['count'] for q in analysis['item_quality_counts']) == phases.get('ANSWER', 0) * 4,
        factual=dict(correct=correct, asked=asked, planned=planned, errors=errors,
                     missing_invalid=asked - correct - errors, unasked=factual.get('UNASKED', 0)),
        research_cost_usd=a['billing']['verified_batch_USD'],
        all_research_generations=a['billing']['all_research_generations_across_four_distinct_studies'],
        all_research_cost_usd=a['billing']['all_research_verified_USD'],
        conservative_exposure_usd=format(Decimal(a['billing']['conservative_owner_exposure_microusd']) / Decimal(1_000_000), '.6f'))


def wrapper_projection(root):
    """Fail closed until an exact independent actual audit is accepted and pinned."""
    if WRAPPER_AUDIT_SHA256 is None or WRAPPER_AUDIT_STATUS is None or WRAPPER_AGGREGATE_SHA256 is None:
        raise ValueError('Wrapper actual audit is not yet pinned')
    def read(path, digest):
        target = Path(root) / path
        if target.is_symlink() or target.parent.is_symlink():
            raise ValueError('Wrapper evidence must be regular public files')
        with target.open('rb') as stream:
            raw = stream.read(1_000_001)
        if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Wrapper public evidence is changed or unreviewed')
        return json.loads(raw)
    audit = read(WRAPPER_AUDIT, WRAPPER_AUDIT_SHA256)
    # The exact audited aggregate binding is checked as well as receipt bytes.
    if audit['overall_status'] != WRAPPER_AUDIT_STATUS:
        raise ValueError('Wrapper actual outcome is not accepted')
    binding = audit['input_pins'][WRAPPER_AGGREGATE]
    if binding['bytes'] != 34947 or binding['sha256'] != WRAPPER_AGGREGATE_SHA256:
        raise ValueError('Wrapper audit aggregate binding differs')
    a = read(WRAPPER_AGGREGATE, WRAPPER_AGGREGATE_SHA256)
    result = wrapper_summary(a)
    result.update(source_audit=WRAPPER_AUDIT, source_audit_sha256=WRAPPER_AUDIT_SHA256,
                  source_aggregate=WRAPPER_AGGREGATE, source_aggregate_sha256=WRAPPER_AGGREGATE_SHA256)
    return result


def render_wrapper(s):
    """Render admitted public fields only; never infer acceptance from raw data."""
    h = lambda x: escape(str(x), quote=True)
    def point(value):
        return 'Not estimable' if value is None else h(('+' if value > 0 else '') + format(value, '.3f').rstrip('0').rstrip('.'))
    def metric(key):
        value = s[key]
        return point(value['mean']) + '<br><span class="live-note">' + h(value['complete']) + ' / ' + h(value['planned']) + ' matched units</span>'
    rows = ''.join('<tr><td>Unit ' + h(r['unit']) + ' · ' + h(r['topic']) + '</td>'
                   + ''.join('<td>' + point(r[k]) + '</td>' for k in ('omitted', 'shown', 'interaction', 'magnitude_change'))
                   + '</tr>' for r in s['units'])
    topics = ' · '.join(h(t['topic']) + ': ' + point(t['mean']) + ' points (' + h(t['complete']) + '/' + h(t['planned']) + ')' for t in s['primary_by_topic'])
    f = s['factual']
    mag = s['magnitude']['mean']
    magnitude_note = ('Mean absolute wrapper magnitude is not estimable.' if mag is None else
                      'Mean absolute wrapper magnitude increased.' if mag > 0 else
                      'Mean absolute wrapper magnitude decreased descriptively.' if mag < 0 else
                      'Mean absolute wrapper magnitude was unchanged; this is not equivalence.')
    validity_note = ('All observed responses had valid survey items.' if s['all_items_valid'] else
                     'Observed answers and valid survey items have distinct denominators.')
    return f'''<main class="live-main" id="wrapper-visibility-summary">
<div class="live-topline"><span class="live-kicker">Identical-content wrapper × own-answer visibility · {h(s['sample_dates'])}</span><span class="live-pill">REAL MODEL EVIDENCE · AUDIT PASSED</span></div>
<h2>Wrapper direction and magnitude are different outcomes.</h2>
<p class="live-deck">A fourth separate study crosses NEWS/SOCIAL text labels with OMITTED/SHOWN own support. Four fictional contexts × two authored topics; one Qwen/Nebius configuration selected from prior item completeness. No real feed or source-credibility effect was tested.</p>
<div class="live-cards">
<div class="live-card"><div class="live-value">{h(s['actual_responses'])} / {h(s['planned_slots'])}</div><div class="live-label">Observed answers / planned slots · 8 fresh baselines + 32 posts</div></div>
<div class="live-card"><div class="live-value">{point(s['primary']['mean'])}</div><div class="live-label">Primary SOCIAL − NEWS support · own answer OMITTED · {h(s['primary']['complete'])}/{h(s['primary']['planned'])} units</div></div>
<div class="live-card"><div class="live-value">{point(s['magnitude']['mean'])}</div><div class="live-label">Mean absolute-magnitude change · SHOWN minus OMITTED</div></div>
<div class="live-card"><div class="live-value">${h(s['research_cost_usd'])}</div><div class="live-label">Verified fourth-study charges</div></div></div>
<section class="live-panel"><h3>Signed contrasts and magnitude are different outcomes</h3>
<p class="live-note">All contrasts are support points on a custom 0–100 scale. Signed interaction = SHOWN wrapper contrast − OMITTED wrapper contrast, on the common eligible intersection. Magnitude change = |SHOWN| − |OMITTED| on those same units.</p>
<table><thead><tr><th>OMITTED wrapper contrast</th><th>SHOWN wrapper contrast</th><th>Matched signed interaction</th><th>Absolute-magnitude change</th></tr></thead><tbody><tr><td>{metric('matched_omitted')}</td><td>{metric('matched_shown')}</td><td>{metric('interaction')}</td><td>{metric('magnitude')}</td></tr></tbody></table>
<div class="live-warning"><strong>Negative signed interaction does not establish attenuation.</strong><br>{h(magnitude_note)} A shift from zero to negative is not a strict nonzero sign reversal. Read the recorded unit values and magnitude counts below; a signed decrease alone does not support general masking or an anchoring mechanism.</div>
<div style="overflow-x:auto"><table><thead><tr><th>Technical unit</th><th>OMITTED</th><th>SHOWN</th><th>Signed interaction</th><th>Magnitude change</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="live-note">Recorded magnitude counts: {h(s['expansion_count'])} expansion · {h(s['contraction_count'])} contraction · {h(s['unchanged_magnitude_count'])} unchanged; {h(s['reversal_count'])} strict sign reversals. Topic-specific primary contrasts: {topics}.</p></section>
<div class="live-grid"><section class="live-panel"><h3>Coverage and factual answers</h3>
<p class="live-note">{h(s['skipped_slots'])} skipped · {h(s['failed_slots'])} failed/uncertain · {h(s['parse_error_slots'])} parse errors · {h(s['cancelled_slots'])} cancelled · {h(s['unattempted_slots'])} unattempted.</p>
<p class="live-note">Factual correct / asked: {h(f['correct'])}/{h(f['asked'])}; correct / planned: {h(f['correct'])}/{h(f['planned'])}. Observed wrong: {h(f['errors'])}; missing/invalid among asked: {h(f['missing_invalid'])}; unasked: {h(f['unasked'])}. These categories do not substitute for one another.</p>
<p class="live-note">{h(validity_note)} No answer repair, replacement, sample extension or model/billing retry occurred. The preserved preflight01 and expired02 attempts are not relabeled as executed study answers.</p></section>
<section class="live-panel"><h3>Limits and accounting</h3>
<p class="live-note">Four purposive contexts and two positive-evidence authored topics are not eight independent people. One selected model/provider configuration and a custom support scale do not establish a human effect, equivalence or a general model mechanism. No confidence interval or p-value was estimated. The full original E02 research contract remains incomplete. Text labels do not reproduce visual feeds; source attribution stayed fixed.</p>
<p class="live-note">Four separate research studies: {h(s['all_research_generations'])} generations / ${h(s['all_research_cost_usd'])} verified reported charges, without pooling estimands. Conservative exposure ${h(s['conservative_exposure_usd'])} retains four historical holds and is not an invoice. E02 $1 / shared $5 / E01 paid $0 remain unchanged.</p>
<p class="live-note">Reported-null tier remains UNKNOWN. Provider streamed:true telemetry versus requested stream:false is unresolved; no default tier, streaming behavior or fallback is inferred.</p>
<details><summary>Accepted public evidence</summary><p class="live-audit">{h(s['source_audit'])}<br>SHA-256 {h(s['source_audit_sha256'])}</p><p class="live-audit">{h(s['source_aggregate'])}<br>SHA-256 {h(s['source_aggregate_sha256'])}</p><p class="live-note">Allowlisted aggregates only; no raw answers, generation IDs, private paths, credentials or owner rows are exported. Earlier studies below retain their separate historical results and accounting checkpoints.</p></details></section></div>
</main><hr class="live-study-divider">'''


def build(root, output):
    """Preserve the old viewer and add a public-summary overlay, idempotently."""
    output = Path(output)
    index = output / 'index.html'
    archive = output / 'historical-preview.html'
    summary = projection(root)  # Refuse altered evidence before touching files.
    followup = followup_projection(root)
    crossmodel = crossmodel_projection(root)
    wrapper = wrapper_projection(root) if WRAPPER_AUDIT_SHA256 is not None else None
    if wrapper is not None:
        summary['wrapper_result'] = wrapper
    summary['followup_result'] = followup
    summary['crossmodel_result'] = crossmodel
    summary['followup']['status'] = followup['status']
    source = archive if archive.exists() else index
    original_bytes = source.read_bytes()
    base = original_bytes.decode('utf-8')
    if START in base or base.count('<main>') != 1 or base.count('</main>') != 1:
        raise ValueError('Unexpected historical preview structure')
    page = base.replace('<main>', (render_wrapper(wrapper) if wrapper is not None else '') + render_crossmodel(crossmodel) + render_followup(followup) + render(summary) + '\n<details class="historical-preview"><summary>Historical snapshot · November 3 recorded runs and completion receipts</summary><main>', 1)
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
