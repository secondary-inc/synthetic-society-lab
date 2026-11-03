# E01 readiness v1.4.1 actual cached-source runs

TASK_ID: E01_BALLOT_READINESS_V1_4_1_ACTUAL

FILES_CHANGED: New `reports/E01_BALLOT_READINESS_V1_4_1_ACTUAL.json` and this receipt only. Seven reviewedcode/config/test pins and all18sourcepins verified beforeexecution; no code/test/config/capture change. Originalversions/runs/sourcecaptures/preflightfailure/auditorfindings preserved.

OUTPUT_ARTIFACTS: Actualrun `e01-79930a81454040a1b9ecc3ede70d1b08`; replay `e01-3da2e755c8f1485ea060f18de13e9309`. Both6artifactledgers sealed; evidence JSON includes exactchecksumfilehashes andallartifactdigests. Named `candidate_rosters.local.json` remains ignored/unbundled; reports include metadata/counts/digests only.

REPRODUCTION_COMMANDS: Verify exactpins in `reports/INDEPENDENT_AUDIT_E01_BALLOT_V1_4_1_CODE_FIXTURES.json`; verify18localbytes/hash. Run twice `PYTHONPATH=src .venv/bin/python -m civiclab.e01.ballots configs/e01_ballot_readiness_v1_4_1.json --root "$PWD"`; verifyeachchecksumledger and compare readiness/localroster bytes exactly. No network required/used.

TESTS_RUN_AND_RESULTS: Current57tests independentlypassed beforeexecution; unchangedcode not redundantlyretested. Sevenreviewedfilepins match;18sourcebytecounts/hashes matchaudit andconfig. Actualrun+replay succeed;12artifacthashes verify, readiness andlocalroster byteidentical. Sevenextractedrosterstates AK/CO/KS/NC/NJ/VA/WY,33regularClassIIslots,26unacquired/unblockedcandidate-sourcejobs. CO6printed/3qualifiedwritein; AK6rows/4printed/2certifiedwritein; KS3rows retainingliteral0/0/0scope. No finalballotsaccepted. Existingcontextobservations unchanged andcontextIDs remainoutside regularquotas. Actual resultcoverage stillpending separateindependentreview; do not promoteacceptedcoveragefromworkerstatement alone.

SOURCE_DATA_AND_LICENSE_NOTES: Existinglocalofficialsourcesonly; no GETs/downloads/headersinvented. KSall25columns crosschecked betweenDOM/visibletext withidenticalwhitespacenormalization; literal0scope notinterpretedasgeneralcodeconvention. AKexactobservedpublicquery/firstvisibleSenatetable scope, registrations/certifications/writeins separate. No namedcandidate/contactvalues inreports orbundles. Maineofficekey/source work remains separate/unincorporated.

COST_USD_ACTUAL_OR_ZERO:0; no modelcalls.

RISKS_AND_LIMITATIONS: Pending independentactualrun/ledger/resultreview. Sourceextractiondoesnotprovefinalballots,currentamendments,independenthistoricalasofbinding orrace sampleacceptance. KSeditionunknown, AKsampleballot/lateramendments, VAlaterallofficecomparison andalloriginalgates remain. No race/candidateexclusion fromwritein/withdrawal/publisherflags, no actualselection, outcomes, sourcepolicyadoption orprospectiveclaim.

UNRESOLVED_BLOCKERS: Independentactualacceptance beforepromotingcoverage;26remainingunacquiredjobs unblocked/incomplete;Mainewithdrawal/replacement/writeinreconciliation andORrosterwork;source/geography/ratingsasof/holdout/comparatorsciencegates.

NEXT_UNBLOCKED_TASK: Auditor independentlyverifiesbothledgers/byteexactreplay andsevenstateobservations. Workerfreezesallv1.4.1filesuntilactualreview; afterreview continue separatelyversionedsource/reconciliationwork. Leadownsstatus/integration.
