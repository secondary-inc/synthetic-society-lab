# Clerk2020 M2 finite PDF format inspection design v1

**Design only. No implementation or source authority.** M1 has independent authored-code acceptance in `INDEPENDENT_AUDIT_E01_CLERK2020_M1_CODE_AUTHORED_V1.json`, SHA9655bf81b508495585a86e4b1fa1d94e0016581274c3996c78e8cd111348395a/10583bytes. All17 M1 candidate/failure files remain byte-identical to commit721a0e9. Its actual entry point remains refused. This design freezes a separate M2 backend/admission/recorder/cumulative-quota contract for independent review before coding. Every actual code/runtime/control/job/release/approval identity is null; approved source bytes/reads/pages are zero.

M2 will inspect format, not candidate/vote records. It cannot accept2020 features,2026 nominees/final ballots, seat/class/round/party/unit facts, selection, geography, predictions or outcomes. Original retrospective24House/up-to8Senate and4House/2Senate deep scope remains; M3–M6 gates and the separate2018→2024diagnostic stay unchanged. This task reads public metadata/code/Git blobs only, never a PDF/private cover/raw/history/person source or helper.

## Fixed registered inputs and separate future authority

The design registers exactly two already-acquired inputs from the accepted capture metadata (audit2b0e3af466645773ca00b11590d871533ee7b2d80abec27abb9b2e77cd5c3a75):

- Historical2020 statistics: `data/raw/e01_clerk_documents_capture_v1/clerk2020_statistics.pdf`,602172bytes, SHA666b2a1f673f263087c141c4d44b0dce47cbddc8f4df27fbc8b415cf05842b76, reported81physical pages.
- Dated2026 nominee compilation: `data/raw/e01_clerk_documents_capture_v1/clerk2026_nominees.pdf`,257739bytes, SHAcb2e4194c88042cf22f8589fb6b8c352d29b501f96abc62a962b6cc52e2c28a8, reported38physical pages.

Known input identities are reference metadata, not current read permissions. Page counts are reported cover-inspection evidence; the future strict reader must verify them. Publication dates retain M0 attribution and require later literal spans. No raw source/body/cover was reopened to draft this design.

One proposed M2 campaign contains one job, exactly these two source-read attempts and two sequential backend attempts, at most119 page extractions. There is no M2 automatic replay. This is a discovery inspection, not M4's later actual-record primary/replay, which remains required. Any independent rehash/re-extraction/visual review needs a separate finite allowance carried through the cumulative ledger. Historical acquisition/cover observations remain separate receipts; this new campaign does not invent or reset a project-wide historical OS-I/O counter.

## Exact backend and runtime policy

Proposed backend ID is `CLERK_PYPDF_6_10_0_TEXT_DIAGNOSTIC_V1`: pypdf6.10.0 on CPython3.12.14, macOS/darwin arm64, standard library plus exact reviewed project code. The version choices come from existing `pyproject.toml` and the observed Python3.12 lock, both hash-linked in the JSON. They do not certify an installed runtime artifact. Before actual source work, independent runtime review must bind interpreter binary, relevant stdlib/backend/project file manifest, distribution/wheel hashes, imported origins and readonly environment. Those identities are null now. All transitive dependencies/build tools must be enumerated and pinned by that receipt. There is no implicit pip/network acquisition or inherited user-site/plugin environment.

The proposed API is `PdfReader` over immutable `BytesIO` source snapshots, strict mode, unencrypted input and one fixed text-extraction mode. Implementation must verify the exact6.10.0 API/options/warning/visitor behavior in backend-source review and generated minimal-PDF fixtures. No backend was imported/called or installed for this design. Unknown signatures, lazy resource requirements, unsupported version/origin or artifact mismatch block admission. Do not substitute pdfplumber, PDFium, pdftotext, permissive parsing, OCR, rendering or a newer version on failure.

The reader rejects encryption/password needs, malformed/repair-dependent structure and warnings. Proposed structure checks refuse active/external actions, JavaScript and embedded/external-file features rather than following them; exact checks require fixture/library review. No PDF action is executed. Trusted backend dependencies import under the pinned runtime first; parse-time code then denies filesystem/network/arbitrary imports/plugins/process creation. Any unsupported lazy access refuses and requires review, not a widened allowlist on the source.

This requires separately versioned modules, policy, disabled actual factory, monitored worker and private recorder/new release kind `CLERK2020_M2_READ_ONLY_FORMAT_INSPECTION_V1`. It is not a toggle or patch of M1. A future granted factory must accept exact externally bound release bytes/hash, code/runtime/policy/source/output/control/limit identities and a separate lead decision; none is instantiated here.

## Numeric bounds and explicit changes from M1

The JSON freezes all ceilings; none is permission by itself.

- Two documents;1MiB each/2MiB total accepted source-input ceilings, exact registered sum859911bytes. The campaign reserves602173+257740=859913 physical source-read bytes, allowing one overflow-detection byte per source. A normal exact read consumes859911; a changed/growing file stops. Read in65536-byte chunks, one read/hash pass per source. Worker digest checks are over memory snapshots, not extra source-file passes.
-100pages/document and119total, with exact expected81/38 required before extraction. One `extract_text` attempt per admitted physical page; reserve all source pages before its worker starts. Page-tree construction is backend work charged to time/CPU/RSS, not a claim that only119 PDF objects are visited.
-40000returned characters/160000UTF-8 bytes per page,4760000characters/19040000UTF-8 bytes total. Page text is transient; do not retain all document text or create a hidden full-text sidecar. Invalid Unicode refuses instead of replacement. Final returned text must satisfy limits; a visitor cap may be used only after its abort/consistency behavior is verified. No streaming/preallocation guarantee is assumed.
-4MiB input packet;262144bytes total inspection data across private projection/public diagnostics;4096stderr bytes per child,8192private failure stderr total. Strict JSON depth12;16384nodes total,96nodes per page and4096envelope nodes.119×96+4096=15520, below the node ceiling.
- Runtime integrity hashing: at most8192allowlisted files/512MiB and a2MiB runtime manifest. Other public admission metadata: at most64files, normally1MiB each, total8MiB including the special runtime manifest. Post-write recorder verification reads at most2MiB. Counted application file reads total at most548216585bytes across those components plus859913source bytes. This counts explicit program reads, not OS loader/page faults/native ps/library I/O or memory-buffer seeks; no global OS-I/O claim is made.
- One whole-job120second monotonic work deadline beginning before runtime/code verification and reservation, with30seconds per backend including import/page-tree/text work. Child CPU soft/hard20/21seconds; aggregate controller plus owned child/probe CPU stop threshold60seconds checked durably at checkpoints. These replace M1's5second/3–4second mock limits because PDF graph/font/page work is a different operation. They are prospective finite budgets, not measured source performance or a reason to autoextend on failure.
-256MiB sampled RSS stop threshold for controller and active backend, replacing M1's128MiB mock threshold to propose explicit room for PDF object/font caches. This is not evidence that the sources need that memory. Fixed owned-PID `/bin/ps` sampling, trusted child peak checks,0.05second polls and at-most1second probes retain M1's declared monitoring boundary. There is no RLIMIT_AS/DATA/hard RSS or decoder-preallocation guarantee. Parent death, hostile host and allocations between samples are not contained. If this boundary is insufficient, actual access remains blocked.
- One-second bounded cleanup: kill owned process group; on group PermissionError, one explicit direct-owned-child kill; always attempt bounded reap. No work retry, alternate root/backend, descendant containment or always-running supervisor is promised. Blocking filesystem/native OS operations are not preemptively hard-wall-contained; all reviewed code paths check finite/nondecreasing clocks and quotas before/after bounded operations.

Compressed/cyclic/object-heavy/font/text-bomb fixtures must test the claimed limits before a real release. pypdf may allocate/decompress before a visitor/final-text check returns. We make that limitation explicit rather than inventing a hard decoded-byte cap unsupported by the backend.

## A bounded private projection, not4.76million retained characters

Each physical page produces at most2048canonical UTF-8 JSON bytes and96nodes. It contains input source/hash, physical page, printed-page UNKNOWN, full returned text length/UTF-8 length/hash, generic line/blank-line/length/non-ASCII statistics, up to three bounded text windows, retained byte intervals, omitted byte count and exact coverage flags. Role/layout remain UNKNOWN_UNREVIEWED/UNKNOWN_UNVERIFIED. No automated Senate/candidate/party/vote/class/stage/date eligibility extraction occurs.

Window positions are deterministic: up to256UTF-8 bytes from the prefix,256from the suffix and512centered in the stream. Merge overlaps; select by position only, never candidate/party/votes/content. Each window records kind, exact UTF-8 range/hash, text and truncation. Combined raw window text is at most1024bytes/page. Actual canonical JSON escaping must fit the2048serialized-page ceiling too. Clip deterministically on UTF-8 boundaries within both limits and report every omission/truncation; do not silently drop mandatory metadata. If mandatory metadata alone exceeds its cap, refuse. A short page may happen to be retained entirely; compute page and full-document coverage flags from actual interval unions rather than asserting either complete or incomplete retention falsely.

119×2048=243712page bytes plus at most8192aggregate envelope bytes yields251904private-projection bytes. Add at most8192public diagnostics and2048private provenance:262144exactly. All three inspection-data files count against that one cap; provenance is not a hidden extra channel. The two raw worker stdout ceilings are81×2048+2048=167936 and38×2048+2048=79872,247808total; aggregate job framing fits the remaining envelope. Implementation must prove that its exact serializer fits, including control-character escaping. It cannot call full text “retained” just because a hash exists.

Text windows and stderr are private `.local.` artifacts. Public diagnostics expose only allowlisted IDs/hashes/byte/page/omission/UNKNOWN/resource/error counts and zero adoption/model/spend flags. Never publish quotes, names, text, window content, stderr messages or numerical votes/margins. This text-only projection can suggest which pages/layout questions need M3 review; it may miss substantive content. It cannot establish full source-role/table/column/footnote completeness, and any additional full-page/visual reading needs separately counted authority.

## Readonly admission and cumulative accounting

Proposed order is design review → authored implementation/minimal-PDF/error/crash fixtures → independent code/privacy/resource review → exact runtime artifact/bootstrap review → lead metadata-only preparation → independent particular metadata admission → fresh finite lead EXEC. Code/runtime/controls/source/output/limits and external release digest bind acyclically; known source metadata never authorizes itself.

Before any PDF stat/open or backend launch, admit the exact external decision and public code/runtime/policy/metadata, check output/control paths, acquire exclusive ownership and durably consume a create-once job slot. The campaign's held envelope funds subsequent per-source/read/dispatch/write reservations; nested reservations draw within it rather than creating or double-counting new authority. All effects require a preceding fsynced reservation.

Open exact known regular files readonly/no-follow, reject symlink components/lexical escape, compare descriptor and lexical identity/size/mtime/ctime before/after bounded reads, verify exact source hash/size, and freeze immutable bytes. Child receives only the bounded snapshot/policy packet, never the source pathname. Pre-seal stat identity rechecks do not pretend to be a second content hash or hostile-host protection. Source/covers/capture/old controls/M1 candidates never change.

An append-only closed hash-linked journal records context pins, sequence, reservations, known settlements and terminal status under an external lead-pinned genesis/head and exclusive cooperating writer. It is not owner authentication, a rollback-proof filesystem, a MAC from credentials or hostile-host protection. Existing/unknown/corrupt/disputed controls refuse before effects; never delete/reset, pick another root or mint another ledger.

Campaign lifetime ceilings are1job,2source attempts,859913read bytes,2backend attempts,119page extractions,262144inspection-data bytes,131072recorder/control metadata bytes and524288whole-owned-job writes. Known settlements record actual counts. Crash after reservation and before unambiguous settlement conservatively charges the full corresponding reservation and consumes its attempt; observed counts remain null when unknown. If the entire held allocation is ambiguous, charge remaining held ceilings and block. Unused allowance cannot create a new job/source/parser attempt. There is no retry/replay/resume under the original release. Any later independently reviewed lead extension must preserve history and carry charged usage forward, including uncertainty; old acquisition/cover scopes are not silently rewritten as this ledger's invented history.

Bookkeeping has its own finite space:64events×1024=65536journal bytes,57344static recorder metadata and8192private failure stderr sum to131072. The524288whole-write ceiling includes projection, metadata, staging/failure bytes and reservations; it is a cooperating-writer counter, not a global filesystem quota. A bounded failure report uses reserved headroom only; unavailable storage or exhausted integrity state may prevent any durable failure marker.

## Recorder, failure and review

The proposed source-inspection recorder uses a single new E01/EXPLORATORY run parent with role `CLERK_M2_SOURCE_FORMAT_INSPECTION_ONLY`, not a prediction run. Data files are `inspection_projection.local.json`, `inspection_diagnostics.json`, `inspection_provenance.local.json`; ordinary manifest/environment/events/summary/payload-hash/commit/ledger/final-seal files bind exact input/code/runtime/policy and journal head. No original PDF copy or full-text artifact is written.

Keep exactly one complete OR partial private page projection. Do not retain per-source responses and a duplicate merged copy. On a child failure, preserve completed-source projection once plus bounded unparsed failed-child stdout only within the combined251904private-data budget; record captured/stored/truncated ranges/hashes. Such fragments are never valid page evidence. Stderr belongs within the8192private stderr allocation. If full output already persisted, later failure metadata refers to it rather than overwriting or duplicating it. No next source runs after failure.

Commit order: data payloads complete → source-stat/code/runtime/control/counter rechecks → summary/closed checksums → final seal binding exact ledger/control head and policy/code/input/runtime → verify own saved metadata without new extraction → completed writer ACK. Final seal and caller acknowledgment are distinct. Post-seal invalidating failures deny success; EIO/EROFS may leave an uncertain seal without ACK. Read-only resolution requires a separate decision and grants no automatic retry. Crashes retain STARTED, charged reservations and available partial files. No always-writable tombstone or parent-death cleanup is promised.

Independent saved-output review must check exact original artifacts, counters, context, page projection/coverage/privacy and source-role limits. It may be separately released without PDF reads; any additional source hash, re-extraction or visual pass requires explicit cumulative allowance. Whole private-run export and private HTTP/reference aliases must refuse. There is no new dashboard, public text endpoint or external publication approval.

## Acceptance before any actual inspection

M2D requires independent acceptance of these exact two design files. M2C then implements only separately versioned code and generated minimal valid/error PDFs, including Unicode/rotation/blank pages, strict/warning/encrypted/xref cases, compressed/object/font/text limits,119-page projection escaping/coverage arithmetic, native resource/cancel/reap failures, input/path/hash/alias adversaries and zero effects for invalid metadata. Test real spawned crashes around each reserve/read/dispatch/write/ledger/seal/ACK boundary; prove counters cannot fall through unknown state, replay, truncation, coedited metadata, copied controls or a new root under the declared trusted-anchor boundary. No actual source body is permitted for these fixtures.

M2R independently reviews implementation/resource/privacy behavior and exact runtime artifacts plus particular prepared metadata. All actual identities remain null until those steps; no missing hash is guessed. Only a separate finite lead EXEC can then permit M2A's one all119-page inspection. Independent retained-output/source-format review follows. M3 observed-format parser, M4 actual records/replay, M5 source/feature/class/round/party/unit/geography/selection and M6 REAL baseline/evaluation remain blocked and unwaived. Inspection cannot self-certify them or replace the original study with a convenient subset.

This task created no code/backend/config activation, installation, grant, control or source-run artifact. All operations were public design metadata checks; GET/model/key/source/helper operations and API spend were zero. Development compute is unpriced. Current13typed/20unfinished/12legacy/final0 and all scientific/rights/prospective/publication limitations remain unchanged.

## Worker handoff

TASK_ID: E01_CLERK2020_M2_VERSIONED_DESIGN_v1

FILES_CHANGED:
- docs/E01_CLERK2020_M2_INSPECTION_DESIGN_v1.md
- configs/e01_clerk2020_m2_inspection_design_v1.json
- No implementation, M1/failure bytes, original sources/covers/history/protocols, status or Git changed.

OUTPUT_ARTIFACTS:
- Frozen design JSON SHAa7ef796ea2d99a708ee5d31c4eeae9809d621cc3b46f35a523fab374a10057c9; corresponding methods document. This is neither a prepared source-release manifest nor an execution permit.
- Exact known2source identities, proposedpypdf6.10.0/CPython3.12.14darwinarm64 policy, explicitM1bound changes, boundedprivate projection, cumulativecontroller/recorder/failure/crash contract and acceptance gates. All new actualidentities/approvals/releases null/disabled.

REPRODUCTION_COMMANDS:
- Public metadata only: use json/hashlib/subprocess to verify design refs and compare all17M1paths to `git show 721a0e9:<path>`. Do not open a declared `data/` source path.
- Check exact2bodyhash/size/path/URL/role refs against accepted public capture handoff; pagecounts81+38=119. Check nullauthority and the budget equalities recorded in the JSON/document. No source helper or PDF backend invocation is required or permitted.

TESTS_RUN_AND_RESULTS:
- Static public-only checks observed all17M1files match721a0e9; M1review9655bf81/10583bytes and all public metadata refs exact. Both source metadata sets match accepted acquisition/handoff; no source existence/content rechecked.
- Arithmetic checked:source859911+2probes=859913;119×2048=243712;private+envelope251904+public8192+provenance2048=262144;workerstdout167936+79872=247808;119×96+4096=15520≤16384;65536journal+57344static+8192stderr=131072;countedapplicationreads548216585bytes.
- No implementation/fixture/backend/runtime/source tests run in this design task. New backend APIs, limits and recorder crash behavior require subsequent authored implementation and independent validation.

SOURCE_DATA_AND_LICENSE_NOTES:
- Public repository metadata/code/Git only. Known inputs are historical2020counts and dated2026nominees, not2026targetreturns/finalballot/latest/source-role acceptance.
- No actual PDF/privatecover/raw/history/person stat/hash/open/view/helper, runtime probe/install, sourcecopy, sourcecontroller/grant/run or network/model/key operation. Privateexcerpt/nonpublication policy is prospective; no actual quotes/names extracted.

COST_USD_ACTUAL_OR_ZERO:
- $0API; zeroGET/model/key/network. Development compute unpriced.

RISKS_AND_LIMITATIONS:
- Exact library/interpreter versions are proposed policy, not installedartifact acceptance. All future runtimepaths/hashmanifests/codepins/control/job/release identities remain null. FixedAPI/warning/strict/extraction semantics need backend-source and generatedminimalPDF validation.
- SampledRSS/cooperativeIO/time limits are explicit, not hardmemory/decompression/nativeOS/hostilehost/parentdeath containment. No silentfallback orautomatic ceilingextension.
- A262144byte projection does not retain4.76Mcharacters. Position-selected boundedwindows private, explicitomissions/coverage; publicnoquotes/names/stderr. Usefulformatdiscovery maymisscontent and cannotproveM3grammar/class/round/party/unit/completeness.
- OneM2job/twosources/119extractions/0replay is proposed; M4parserprimary/replay andoriginal24House/up8Senate+4/2deep remain unwaived. No science/coverage/forecast/publication changes;13typed/20unfinished/12legacy/final0 unchanged.

UNRESOLVED_BLOCKERS:
- Independent M2D design review NOT_RUN. M2backend/admission/recorder/quota/runtime implementation and generatedPDF/error/crash fixtures notwritten. Independentcode/runtime/particularmetadata and separatefiniteleadEXEC absent. M3–M6 source-record/feature/geography/selection/REALbaseline/evaluation gates remainblocked.

NEXT_UNBLOCKED_TASK:
- Root assigns independent review of these exact frozen two design files. Only after acceptance implement the separate disabledM2backend/admission/recorder/quota system and authoredminimalPDF/error/crash tests. Actualsourceinspection remains separately gated; do not flipM1oractivate this design.
