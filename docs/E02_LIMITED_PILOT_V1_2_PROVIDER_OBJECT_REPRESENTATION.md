# Limited-pilot v1.2 provider-object retention

November 5, 2026. A narrow proposed methods amendment to the accepted v1.1
composite, for the new limited study only. Historical runs, findings, contracts
and raw evidence retain their original meanings. This document grants no live
access or spending authority.

The existing strict model/statistics transport returns the complete parsed JSON
object after its wire-body framing, UTF-8, size, duplicate-key and nonfinite
checks. It does not expose original wire bytes. New study model-response and
generation-statistics artifacts therefore use the explicit representation
**CANONICAL_PARSED_PROVIDER_OBJECT_V1**: exact `common.canonical_bytes` of the
complete returned object, preserving every member and value, including unknown
fields, without adding, dropping, redacting, repairing or sanitizing members.
The exact canonical serializer and transport sources are in K's transitive pins.

For this new study, the closed legacy field names `response_raw_sha256` and
`statistics_raw_sha256` mean SHA-256 of the exact retained canonical artifact
file bytes. They do **not** mean original HTTP wire-body hashes. K.methods must
bind both the accepted base-composite review and the independent review of this
representation amendment, and name CANONICAL_PARSED_PROVIDER_OBJECT_V1. Record
that representation in the private run's retention metadata and public summary.
No reinterpretation applies to the truly raw catalog GET/proof hashes, external
packet-byte hashes, checkpoint-file hashes, request payload bytes or any prior
run/audit.

The transport's 2,000,000-byte wire limit and the journal's 2,000,000-byte
canonical artifact limit are separate enforced limits. Unicode escapes can
expand the canonical representation. Harvest safe known monetary observations
before body serialization/privacy/domain refusal. If complete canonical
serialization is unavailable, too large, unsafe or unsupported, retain only
available safe diagnostics and known costs, explicitly mark the complete body
missing, retain the full conservative reservation and stop the study. Never
truncate or persist a sanitized object while calling it complete. Existing
per-artifact/cumulative/free-space bounds continue to apply.

Commit verification reads the exact bounded file bytes, strictly parses with
duplicate/nonfinite rejection, requires re-canonicalization byte equality, checks
the file hashes, rederives questionnaire output from the complete response and
verifies identity/native-usage/provider/auxiliary/cost consistency with the
financial row and retained statistics. The response representation hash remains
known before RESPONSE_SEEN. The statistics representation hash occurs only in
the later commit witness W; response output remains immutable under the v1.1
ordering correction.

The original wire whitespace, field order, number spellings and Unicode escape
spellings are unavailable through this transport. The study makes no wire-byte
forensic, HTTP-header or TLS attestation claim. Independent implementation tests
must cover complete-member retention, canonical byte equality, Unicode expansion,
serialization/privacy/size refusal, monetary-observation ordering and missing
body behavior. No new transport framework or old-source modification is needed.
