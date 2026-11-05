# Clerk2020 M2 design v1.1 — separate specification successor

**Methods only, not implementation or authority.** This successor addresses both findings in `INDEPENDENT_AUDIT_E01_CLERK2020_M2_DESIGN_V1_SPECIFICATION_FINDINGS.json`, SHA520b5d9fddbc03acc555bfa2d27969add79ad1642a32a47a5955bcaef7054bb8/11741bytes. The exact original v1 JSON and document are preserved; no finding is edited or declared closed by this worker. The companion `configs/e01_clerk2020_m2_inspection_design_v1_1.json` freezes closed schemas, type bounds, hash projections, namespaces, state/counter transitions, numeric partitions and terminal protocol. Every actual registration/code/runtime/control/job/release/approval identity remains null; source approval is zero and the actual factory is disabled.

The accepted M1 snapshot/failure artifacts at721a0e9 and review9655bf81 remain unchanged. Historical2020 statistics and dated2026nominees remain the same two byte-registered source references, with reported81/38pages; no PDF/private cover/raw/history/control/person input was statted/read/hashed and no runtime import/install/helper/key/environment/network/model operation occurred. Original retrospective24House/up-to8Senate plus4House/2Senate deep scope and M3–M6 source/class/round/party/unit/geography/selection/baseline gates remain unwaived.

## 1. Hash rules and fixed registration precede release hashes

Canonical structured records use sorted-key, compact-separator, exact UTF-8 JSON without Unicode normalization, duplicate keys, nonfinite values or bool-as-integer coercion. `H(object)` hashes those exact canonical bytes. Single-object files have no newline. Journal/tail rows add one framing newline; chain hashes omit that newline, while file/prefix hashes include exact framing. No record contains its own hash. The schema field sets are closed and every required field participates; implementations cannot choose later which fields to exclude.

A trusted registrar preassigns `campaign_id`, `source_set_id` and `anchor_id`. `CampaignRegistration` (A0) binds the study, source-set metadata digest, repository-root identity, fixed control/registry/index namespaces and accepted acquisition reference. The source-set digest is over the exact two registered metadata records, sorted by source ID, with only the declared source-ID/path/URL/hash/size/page/role fields. A0 contains no future static-spec, decision, genesis, head or own hash.

Paths are fixed from those preassigned IDs:

- registry: `data/processed/e01_clerk2020_m2_registry/<campaign_id>`;
- control: `data/processed/e01_clerk2020_m2_control/<campaign_id>`;
- source-set index: `data/processed/e01_clerk2020_m2_registry/source_sets/<source_set_id>.local.json`;
- one-shot admission slot: `<registry>/attempts/<phase>-<preassigned_attempt_id>.reservation.local.json`.

None is derived from a release hash. A protected registrar index maps this study/source-set identity to exactly one campaign. A failed admission cannot choose a new ID/root to regain allowance. Changed, missing, cloned, crossed or truncated state refuses. A continuation keeps A0, source set, genesis and namespaces; a new static spec references its predecessor and a new decision pins the current external anchor plus all old charges, including uncertainty. Recreating genesis or omitting old usage is forbidden. Local locks/hashes are not hostile-host antirollback or owner authentication; the fixed outside-journal registrar/anchor is the explicit trusted boundary.

## 2. Closed acyclic authority and context graph

The JSON defines exact field/type/null sets for Registration, StaticSpec, BootstrapDecision, ExecutionDecision, IssuedEnvelope, PhasePacket, ReservationToken, CounterAxis/State, Genesis, JournalEvent, AnchorState, BootstrapReceipt, PreparedMetadata, DerivedContext, FinalizationReservation, PrefixLedger, FinalSeal, TerminalTailEvent, WriterAck and CallerObservation. Event payloads are independently closed by event type. No actual instances are created here.

The initial direction is:

`source-set → A0 → static spec C → BOOT decision B → issued envelope I_B → reservation token R_B → genesis G → bootstrap journal/counters → BOOT_COMMIT → bootstrap receipt → completed bootstrap anchor → prepared metadata P → EXEC decision E → issued envelope I_E → reservation R_E → derived context → EXEC admission/active anchor → source work`.

C references A0 and exact future code/runtime/backend/policy artifacts; it does not reference its own hash, genesis, EXEC or derived output context. Its projection-policy hash is exactly `H(policy.projection)`; its budget-policy hash is exactly `H({limits, stage_partitions, counter_protocol, write_slot_schedule})`. This is a fixed projection, not implementer discretion. A continuation C references only an earlier static spec, never a future one.

A first BOOT decision allows `CREATE_ONCE` with null prior genesis/anchor; a continuation requires `VERIFY_EXISTING` and exact previous refs. G is created afterward and binds C/B/I_B/R_B; B never predicts its future G hash. Bootstrap receipt binds the completed bootstrap journal byte-prefix and counter/code/runtime verification results, but not its later anchor. That completed anchor then binds the receipt. P binds both before E exists.

E references P, G and the completed pre-issuance anchor. It does not reference its own hash, its later issued envelope, derived context/run ID, seal, tail or ACK. The trusted registrar issues a separate downstream envelope containing `H(E)` and its predecessor envelope/anchor; the caller supplies that envelope's expected hash outside its bytes. The same rule applies to BOOT. Replayed ordinals/slots refuse; a caller-minted digest is not trusted authority.

A bounded in-memory PhasePacket contains only canonical A0/C/decision/issued-envelope bytes. External expected-envelope SHA validates the envelope, which binds the decision and its static refs. No filesystem read is required to parse these links. Unknown/extra fields or oversized packets refuse before effects.

The fixed run derivation is `e01-` plus the first32hex characters of `H({kind:M2_RUN_ID_V1_1,campaign_id,job_id,execution_decision_sha256:H(E)})`. The output path is C's permitted output base plus that run ID. E contains only the preassigned job ID, output-base policy and derivation-rule identifier, not a literal future hash-derived run path. DerivedContext binds E/I_E/R_E/P/G/A0/C and those computed values. EXEC_STARTED binds its hash afterward. A new M2 recorder owns this deterministic ID; it cannot patch the old RunStore or silently choose another UUID/root.

## 3. First writes and verification reads have explicit authority

The root of trust is a separately reviewed minimal bootstrap/registrar TCB and an externally supplied expected issued-envelope hash. It does not import pypdf or unknown M2 backend code before verifying runtime/code. Authority delivery/TCB startup is an explicit boundary, not a journal fabricated before it exists.

The issued BOOT envelope durably consumes one externally registered attempt and prepays a bounded delivery/initial-write slice before launch. Delivery permits at most262144metadata bytes; initial path checks are limited to the fixed registration/reservation namespace. The first O_EXCL reservation slot, A0/genesis/initial anchor writes have explicit initial-write authority, at most16384bytes within the larger prepaid schedule. There is no claim that a local quota journal existed first. If local reservation persistence fails, the registrar's already-issued attempt remains consumed; no second preflight or alternate root is permitted.

After memory-only packet validation, the TCB creates the fixed outside-registry reservation token before reading existing anchor metadata, public configs or code/runtime files. It then creates G and the initial anchor only for a permitted first registration, or verifies the existing immutable G/root for a continuation. Bootstrap journal reservations are fsynced before bulk reads. Unknown/partial/crossed state stops without source access.

The8MiB metadata allowance is partitioned once:256KiB prepaid delivery,6MiB BOOT admission and1.75MiB EXEC admission, totaling8388608bytes. The512MiB code-integrity allowance is511MiB BOOT manifest hashing plus two EXEC hot-code checks of at most512KiB each, totaling536870912bytes. The remaining readonly runtime tree receives identity/stat/origin checks against its verified immutable manifest; we do not claim to rehash the full512MiB again for free. Any drift or need for another full pass requires a separately budgeted continuation, not a repeat preflight.

BOOT has one45second active window/10second CPU allocation; EXEC has one75second active window/50second aggregate CPU allocation. Their cumulative active total is120seconds/60CPU seconds. Independent review idle time is excluded explicitly; this is not falsely described as one continuous clock across two external decisions. Child30second wall/20–21second CPU and256MiB sampled/trusted RSS ceilings, bounded probes/cleanup and the other v1 limits remain prospective, not measured feasibility or hard memory/OS containment.

EXEC receives its own one-shot issued envelope in memory and creates its fixed admission reservation before new metadata reads. Only after verifying the exact prior anchor/G/BOOT receipt/runtime identity, reconstruction of charged state, derived context and durable active-source reservation may any PDF stat/open/backend dispatch occur. E's prior anchor is the pre-issuance snapshot; downstream issue/reservation/admission objects do not force E to hash itself.

## 4. Held, reserved, charged and observed are distinct

Each fixed counter axis has ceiling, held, reserved, charged, observed/null, observed-known-sum and uncertain-charged fields. `charged+reserved+held≤ceiling`; available is the remainder. Allocate moves available to held; reserve moves held to pending-effect reserved. Known settlement moves actual usage to charged and unused reservation back to held; unknown settlement charges the full reservation and leaves aggregate observation null. No negative settlement, inferred zero after a crash, or automatic reuse of an attempt is permitted.

Counter snapshots bind registration/static spec, the external reservation token and the prior known journal head. Initial inline G state has a null pre-genesis head; later snapshots name an already-known head, never their own future committing event. Reconstruction replays that exact external token and closed prefix events. All counter-before payload hashes refer upstream; BOOT_COMMIT and COMMIT_PREFIX may reference an already-written snapshot. They never form a two-way hash link with it.

The axes cover bootstrap/EXEC admission attempts, source jobs/reads/bytes, backend attempts/pages, code/metadata/closing-verification reads, data/control/all writes, active time and CPU. Existing v1 globals are retained: one job, two reads,859913source bytes, two backends,119extractions,262144inspection data,131072control metadata and524288all owned writes. Code+metadata+source+2MiB closing reads still sum to548216585counted application bytes. OS loader/page faults/native ps/memory seeks remain outside that explicit application-read counter; no project-wide historical OS-I/O claim is made.

Write accounting cannot recurse into “reserve a journal entry before reserving its own write.” The external BOOT envelope conservatively precharges the full write ceilings once. That prepaid token authorizes only a closed, bounded, create-once file/event schedule; remaining effect permission is constrained by those slots, not by minting new available credit. The same write must satisfy global and category caps; their intersection is not added twice to the global total. Unobserved final/self-write counts can remain null without reducing charged usage.

The explicit schedule is now48normal journal events×1024=49152bytes, plus73728static recorder bytes and8192private stderr =131072control bytes. Static space partitions as24576BOOT,24576EXEC precommit and24576terminal. The larger inline genesis ceiling8192 and four initial slots total14336, within the16384initial allowance and24576BOOT allocation. Source/page reservations are per source/dispatch, not119unbounded per-page journal rows. Known terminal slot maxima total18432, below its24576envelope. Data262144+control131072=393216 leaves131072staging/failure headroom under524288. Exact serializer/event/crash fixtures must prove this schedule before actual use; limits are not free extra channels or guaranteed writable failure space.

Crash or missing settlement conservatively charges the pending reservation; ambiguous whole allocation charges all unproved remaining held/reserved amounts and stops. The issued slot/STARTED is consumed even if a zero-effect outcome seems likely. A later independently approved extension uses the same registry/root/G/history and raises lifetime ceilings explicitly while carrying every old known and uncertain charge forward. It cannot rerun an old slot, reset genesis, refund an unknown or create a new release-hash namespace.

## 5. A fixed sealed prefix, then a bounded terminal tail

The successful source-data files remain the v1 private projection/public diagnostics/private provenance, collectively262144bytes. The exact ten sealed-prefix files are manifest, environment, bounded run `events.jsonl`, summary, the three data files, payload-hash file, inspection-commit file and `counters.prefix.local.json`. `checksums.json` (L) is a closed ten-name→raw-SHA mapping. It excludes itself, authoritative quota journal, future H/seal/tail/ACK/anchor objects. The run events log is not the quota journal and freezes with the other files before L; no late failure message is appended into an already sealed run log.

Finalization is strictly ordered:

1. A RESERVE_FINALIZATION event activates the already-prepaid terminal write slots and fully conservatively charges the2MiB closing-verification read allowance. Its counter-before hash is upstream; it does not reference a future post-reservation snapshot.
2. Write X (`counters.prefix.local.json`) with known source/backend observations through the prior sequence and unknown/precharged terminal effects. X contains neither future L/H nor seal/tail/ACK hashes. Write summary `PAYLOADS_CLOSED_AWAITING_SEAL`, inspection commit and L. All closing hash reads draw from that precharged2MiB; all these files freeze.
3. Append final normal COMMIT_PREFIX event H binding context/L/X/finalization reservation. Permanently freeze the normal quota journal at that exact sequence, byte offset and head. Publish a downstream prefix-anchor record; H cannot reference that future anchor.
4. Create S, the final seal, binding H and the exact raw journal-prefix hash/size/last sequence, L, X, G/context/decision and the terminal-protocol ID. S has no own hash, mutable latest-head, tail or ACK ref.
5. Perform bounded saved-byte verification without PDFs/backend/source. Write Tail1 VERIFY_OK or VERIFY_FAILED, with first predecessor `H(S)`. Subsequent tail records chain from the preceding tail record. Each describes observations completed before its own serialization/write; its own final byte count remains unobserved, covered by the prepaid cap.
6. Only after VERIFY_OK, create writer ACK A referencing S/H/X/Tail1. Then Tail2 ACK_COMMITTED binds `H(A)`; then publish a completed protected anchor referencing S/H/Tail2/A. No object points forward into its own preimage.
7. Return normally only after the durable completed anchor and no invalidating tail. A separately observed caller return is not inferred from an ACK file. At most Tail3 INVALIDATE and a matching invalidated anchor may follow an error if their reserved slots/storage permit. No normal-journal append, counter refund, data/run-log mutation, reseal or source rerun is allowed after H.

The seal therefore binds an immutable prefix plus a specified downstream protocol, not a “latest head” that is later changed. BOOT receipt similarly binds its completed byte-prefix even though a later authorized EXEC can append beyond that offset. Prefix and tail are physically/schema-separated.

Writer terminal success requires valid VERIFY_OK→ACK_COMMITTED, A, a completed protected anchor and no INVALIDATE. Caller delivery still needs an external normal-return observation. Seal-only, partial tail, lost ACK, missing final anchor or post-persist EIO remains SEALED_OR_ACK_UNKNOWN. Charged terminal maxima stay frozen; known lower observations live only in tail records and never refund source rights.

Failure after H but before S can use a reserved failure/anchor record referring to H with null seal/tail/ACK; it cannot append to the frozen normal journal or claim success. EROFS/power loss may prevent even that marker. Preserve whatever bytes/slots exist. A separately authorized bounded read-only observer may inspect original G/prefix/L/X/S/tail/A/anchor/caller evidence; it cannot rewrite old ACK/counters, infer normal delivery, reopen PDFs, re-extract or activate a retry. This design grants no observer pass itself.

## 6. Retained projection, source and backend boundaries

The original v1 positive intent is retained without changing its failed files: strict proposed pypdf6.10.0/CPython3.12.14darwinarm64 artifact/API admission; exactly the acquired historical2020 and dated2026nominee PDFs; one readonly parent hash pass plus one overflow probe/source; immutable worker snapshots; exact81/38page verification; no candidate/vote parser or OCR/render/download/fallback. Library artifacts/APIs are still untested unknown identities pending generated PDF/backend review, not accepted installed facts.

Full returned text is transient, capped40000characters/160000UTF-8 bytes per page and4760000characters total. Each private page projection remains2048serialized bytes/96nodes with at most1024position-selected UTF-8 snippet bytes, explicit clipping/coverage/omission hashes and UNKNOWN role/layout.119page bytes243712+envelope8192=251904private; add8192public diagnostics+2048private provenance=262144. Actual JSON escaping must fit. It is not a full-text-retention claim or a public quote/name channel. M3may require additional separately budgeted source evidence. All publication/rights/latest/as-of/ballot/feature/scientific limitations remain.

## 7. Acceptance and specification oracles

Independent successor review must address both original findings separately; this worker records no closure. Before implementation acceptance, authored checks must cover closed-field/hash-DAG directions and excluded downstream fields; initial delivery/reservation before the first explicit read; concurrent first registration/slot/root/anchor conflicts; cross-root/replayed/truncated/cloned histories; every held/reserved/known/unknown/precharged counter transition and cap boundary; source-zero gating until EXEC admission; and native crash/clock/pause/storage behavior around each reserve/effect/settle.

Finalization fixtures must crash before/after last data write, terminal reserve, X, summary, L, H, prefix anchor, S, verification, Tail1, A, Tail2, final anchor, caller return and optional INVALIDATE. They must prove all sealed files/head/counter snapshots remain immutable, observations exclude their own unknown writes, lost ACK does not create credit or a rerun, and a future read-only finding cannot retroactively manufacture caller success. Only then may separate code/runtime/particular reviews and finite actual BOOT/EXEC decisions be considered. Actual M2/M3–M6 work remains blocked and no M1 toggle is introduced.

## 8. Worker handoff — specification candidate only

TASK_ID: E01_CLERK2020_M2_DESIGN_V1_1_SUCCESSOR

FILES_CHANGED: Only `configs/e01_clerk2020_m2_inspection_design_v1_1.json` and this document. No shared status, runtime, source, predecessor or auditor files edited.

OUTPUT_ARTIFACTS: Separate v1.1 methods specification; config SHA-256 `7e87d6844ca5bec346af91359d38a9c7a612503962d13b4749fd93d3811fb0e6` (78955 bytes). The document's final hash belongs in the external handoff, not in its own preimage. Original v1 and its BLOCKED audit remain authoritative historical findings; no closure is asserted here.

REPRODUCTION_COMMANDS: From the repository root, run the read-only Python block below. It reads only these public methods files and the 17 explicitly listed M1 code/evidence files, with no package import, runtime installation or actual source access.

TESTS_RUN_AND_RESULTS: 59 static assertions passed: 22 closed schema field-set checks; declared graph acyclicity with 34 nodes/36 edges plus node/edge consistency; disabled factory/null actual identities/zero source authority; all 17 M1 pins and three predecessor/finding pins unchanged; metadata/code/time/CPU, initial/BOOT/terminal/control/data/write/read arithmetic; exact ten-file ledger schema. These checks verify internal specification properties and preserved bytes. They do not implement the authority protocol, validate a JSON Schema engine, exhaustively prove all semantic reference dependencies, exercise crashes or constitute independent acceptance. Runtime/backend/generated-PDF/source tests NOT_RUN.

SOURCE_DATA_AND_LICENSE_NOTES: Public metadata and methods only; existing accepted source identities copied as references. No private/source PDF stat/open/read/hash, new collection, extraction, names, respondent data, credentials or publication. Source rights and prospective/ballot/coverage limitations are unchanged.

COST_USD_ACTUAL_OR_ZERO: $0 API/model/content spend; development compute unpriced. No environment/key/network/model calls.

RISKS_AND_LIMITATIONS: Trusted local registrar/CAS and reviewed bootstrap TCB remain assumptions requiring implementation/review. Native loader I/O is outside the explicitly counted read boundary; runtime identities remain unknown. Counter and serialization/crash behavior remain unimplemented. Lost ACK and unavailable storage stay unknown, without retry/reset/refund. Private snippets are bounded partial windows, not complete parsed source coverage. E01 remains retrospective; no scientific acceptance, expanded coverage or M1 toggle follows.

UNRESOLVED_BLOCKERS: Independent successor methods review must resolve both findings against this exact candidate; thereafter separate authored implementation/generated fixtures, code/runtime identity reviews and finite actual BOOT/EXEC decisions are required. Actual M2 and M3–M6 remain blocked. No E02 dependency is added.

NEXT_UNBLOCKED_TASK: Lead assigns an independent reviewer to these exact two successor files, preserving the original v1/finding; do not self-certify or invoke the actual source/backend while review is pending.

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

p = Path('configs/e01_clerk2020_m2_inspection_design_v1_1.json')
d = json.loads(p.read_text())
checks = []
def check(label, condition):
    assert condition, label
    checks.append(label)
for name, schema in d['closed_schemas'].items():
    check('closed ' + name,
          schema['additional_properties'] is False
          and len(schema['required']) == len(set(schema['required']))
          and set(schema['required']) == set(schema['field_types'])
          and set(schema['nullable_fields']) <= set(schema['required']))
nodes = d['closed_hash_DAG']['nodes']
edges = d['closed_hash_DAG']['edges']
seen = set()
while len(seen) < len(nodes):
    ready = [n for n in nodes if n not in seen
             and all(a in seen for a, b in edges if b == n)]
    assert ready, 'cycle'
    seen.update(ready)
check('DAG', len(set(nodes)) == len(nodes)
      and all(a in nodes and b in nodes for a, b in edges))
check('disabled', d['actual_factory_enabled'] is False)
check('null authority', all(v is None for v in d['actual_identities_and_authority'].values()))
check('zero source authority', all(d[k] == 0 for k in
      ['approved_page_extractions', 'approved_source_bytes', 'approved_source_reads']))
pins = dict(d['M1_all17_pins_unchanged'])
pins.update({
 'configs/e01_clerk2020_m2_inspection_design_v1.json':
 'a7ef796ea2d99a708ee5d31c4eeae9809d621cc3b46f35a523fab374a10057c9',
 'docs/E01_CLERK2020_M2_INSPECTION_DESIGN_v1.md':
 '6b306d48539adc3c4beb0d22ead232c8c084046bcae9e2abbbb10838353c6d7b',
 d['specification_finding_ref']['path']: d['specification_finding_ref']['sha256']})
for path, expected in pins.items():
    check('pin ' + path, hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected)
s = d['stage_partitions']
w = d['write_slot_schedule']
check('metadata', s['delivery_registration']['metadata_read_charge_upfront']
      + s['BOOT']['metadata_read_bytes'] + s['EXEC']['metadata_read_bytes'] == 8388608)
check('code', s['BOOT']['runtime_integrity_read_bytes'] + s['EXEC']['hot_code_read_bytes'] == 536870912)
check('time', s['BOOT']['active_time_ms'] + s['EXEC']['active_time_ms'] == 120000)
check('CPU', s['BOOT']['cpu_ms'] + s['EXEC']['cpu_ms'] == 60000)
check('initial slots', sum(x['max_bytes'] for x in w['initial_registration_slots'])
      == w['initial_registration_total_max'] <= s['delivery_registration']['initial_write_slots_max'])
check('BOOT slots', w['initial_registration_total_max']
      + sum(x['max_bytes'] for x in w['BOOT_static_additional_slots'])
      == w['BOOT_static_actual_slot_sum_max'] <= w['BOOT_static_total_max'])
check('terminal slots', sum(x['max_bytes'] for x in w['terminal_slots'])
      == w['terminal_slot_sum_max'] <= w['terminal_write_envelope'])
check('control', w['normal_journal_event_bytes'] * w['normal_journal_events']
      + w['BOOT_static_total_max'] + w['EXEC_precommit_static_total_max']
      + w['terminal_write_envelope'] + w['private_failure_stderr'] == 131072)
check('projection', 119 * 2048 + 8192 + 8192 + 2048 == 262144)
check('writes', 262144 + 131072 + 131072 == 524288)
check('source probe', 602172 + 257739 + 2 == 859913)
check('read ceiling', 536870912 + 8388608 + 859913 + 2097152 == 548216585)
check('ledger', len(d['sealed_file_policy']['exact_ledger_keys']) == 10
      and set(d['closed_schemas']['PrefixLedger']['required'])
      == set(d['sealed_file_policy']['exact_ledger_keys']))
print('STATIC CHECKS PASS', len(checks))
assert hashlib.sha256(p.read_bytes()).hexdigest() == '7e87d6844ca5bec346af91359d38a9c7a612503962d13b4749fd93d3811fb0e6'
PY
```
