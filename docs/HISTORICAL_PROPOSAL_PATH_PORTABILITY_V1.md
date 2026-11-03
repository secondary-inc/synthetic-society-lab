# Historical proposal path portability

The clean restoration of committed snapshot `a856b96` installed successfully,
but its767-test suite failed one assertion after370.189seconds. The test compared
the restored checkout's absolute path with an absolute lexical path recorded in
an earlier, explicitly non-authorizing Wyoming proposal. The proposal never
claimed that its output existed or had been canonicalized.

The correction changes only that static proposal test. It pins the entire
original proposal, checks the historical path's absolute/non-traversal spelling
and exact relative suffix, and retains proposal-only status and false
filesystem-verification checks. It does not rebase the proposal, inspect source
files, resolve an actual output, grant authority or change runtime admission.
The existing default-zero and null-approval tests remain.

The original test is preserved byte for byte at
`tests/fixtures/historical/e02_f_wy_release_proposal_v1_test_original.py.txt`,
SHA256 `24d795a3753d215ecacab0d05e4fefa4c68d34ecdbd07913b4128a2b80a4c180`.
Earlier review records retain their original hashes and scope. They are not
rewritten as reviews of the corrected test. The initial archive, unchanged963
files and failure log remain documented in
`reports/CLEAN_RESTORE_A856B96_767_FIXTURES_FAILURE.json`.

Independent review of the correction is recorded in
`reports/INDEPENDENT_AUDIT_HISTORICAL_PROPOSAL_PATH_PORTABILITY_V1.json`.
Eight tests passed both in the original root and in a distinct relocated
metadata overlay. Four actual-admission default/null-authority refusals also
passed before source I/O. The original full-suite restoration remains failed;
the next acceptance condition is a fresh full suite from a new exact committed
snapshot. This correction does not certify scientific validity, source
completeness, remote CI or the full reproducibility package.
