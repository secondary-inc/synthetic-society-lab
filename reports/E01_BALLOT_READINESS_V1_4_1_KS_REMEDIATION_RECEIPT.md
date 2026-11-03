# E01 v1.4.1 Kansas source-layout remediation

TASK_ID: E01_V1_4_1_KANSAS_SCOPE_REMEDIATION

FILES_CHANGED: `src/civiclab/e01/ballot_capture_formats_v1_4.py`, `tests/test_e01_ballot_captures_v1_4.py`; new `configs/e01_ballot_readiness_v1_4_1.json`, remediationevidenceJSON and thisreceipt. Originalv1.4code/config/tests/fixtureevidence/receipt preserved before mutation with hashes under ignored `data/processed/reproducibility/e01-ballot-readiness-v1_4-pre-ks-remediation/`. Three named historicalv1.4implementation/captureformats/capturetests reportTXT preserve exact consumedsource/testbytes forGit. Originalv1.3andv1.4configs/evidence/captures/auditorfinding unchanged. No common/CLI/status/sharedhelpers edits.

OUTPUT_ARTIFACTS: Seven currentfilepins in `reports/E01_BALLOT_READINESS_V1_4_1_KS_REMEDIATION.json`; configsourcepins/content unchanged, explicit newv1.4.1filename. Cachedsource readerpreflight only: KS3rows, exactliteral0/0/0scope retained; AK6rows/4printed/2certifiedwriteins. No RunStore readinesspipeline executed and no newreadinessrunIDs claimed.

REPRODUCTION_COMMANDS:57-test command in JSON. Beforeactualreadiness, independent reviewer must verify newpins and exactsourceDOM/visibletextagreement on existing batch03cache. Futurecommand afterfreshapproval: `PYTHONPATH=src .venv/bin/python -m civiclab.e01.ballots configs/e01_ballot_readiness_v1_4_1.json --root "$PWD"`.

TESTS_RUN_AND_RESULTS:57targetedtests PASS;2added tests beyondoriginal55. PositiveKSfixture now matchesobservedliteralDistrict/Position/Division0/0/0. Explicit blank/mixed/nonzero/unknown/00code layouts refuse, no broadstatewidecodingrule. Outputpreserves source_district_literal/source_position_literal/source_division_literal. Actualreaderpreflight first failed ValueError because browseremptycells containNBSP whileDOMalready normalizedwhitespace; type-onlyfailedprobe receipt retained at `data/raw/e01_ballots_v1_4_1_preflight/attempt01_failure.json`. Narrowcorrection comparesall25columns afteridenticalwhitespacenormalization; changednonwhitespace contactcolumn stillrejects. Fullcandidatecoverage remainsmatched. Repeatedactualreaderpreflight succeeds on exactKS/AKpins; reportcounts/digests only, no contact/nameexports. RetainsURLquerysecretguards, browserheaderhonesty, DOMtruncationchecks, failurelifecycles andallpriorformats.

SOURCE_DATA_AND_LICENSE_NOTES: No newGETs/downloads/capture changes. Same18configuredsourcepins. Corrects inaccurateblank-field authoredfixture explicitly without alteringold evidence. Literal0values describe onlyobtainedKSschema, not a generalcodeconvention orlegalballotstatus. BrowserDOM/text normalization removeswhitespaceonly, notmeaningfulcontact/name/party/scope content. No rawcontacts/namedrosters in report.

COST_USD_ACTUAL_OR_ZERO:0; no model calls.

RISKS_AND_LIMITATIONS: Freshindependentreview required beforeactualreadinessexpansion. Preflight is a boundedsource-format probe, not sealedpipelineexecution orscientificresult. Acceptedreadinessremains5states/28unfinished/0finalballots. KSamendments/currentedition, AKsampleballot/lateramendments, MEreconciliation/ORrosterjobs unchanged. Otheracquisitionworkpaused for thisfunctionalfix. Sourceadoption/sample/outcomes/prospectiveclaims remain disabled.

UNRESOLVED_BLOCKERS: Independentclosure IA-E01-V1_4-KS-SCHEMA-001 andfreshv1.4.1executionacceptance; onlythencached18sourceactualreadiness/replay andindependentresultreview. Originalscientific/ballot/selection/geography/asofgates persist.

NEXT_UNBLOCKED_TASK: Auditor independently tests actualall-zeroKSschema/full25columnDOMvisibleagreement andnegatives againstfrozennewpins; afterapproval execute boundedlocalpipeline/replay. No config/source relaxation to hide failures.
