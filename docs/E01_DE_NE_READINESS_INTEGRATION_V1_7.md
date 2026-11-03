# DE/NE readiness integration candidate v1.7

This separately versioned candidate is pending independent integration review. Geometry dependency acceptance authorizes preparation, not recorded readiness runs, coverage promotion or scientific acceptance. The accepted v1.6.1 module/config and historical runs remain unchanged. The six-source standalone contract is retained as immutable history, including its then-pending dependency description.

`src/civiclab/e01/ballots_v1_7.py` wraps the unchanged v1.6.1 validator with a frozen-input configuration at `configs/e01_ballot_readiness_v1_7.json`. It binds the original base config and standalone contract by exact byte hashes, checks all declared helper/input hashes and local import origins, verifies precisely six cached source bodies/paths from that contract, and requires pdfplumber 0.11.9 before Nebraska physical extraction. Source/input checks repeat after parsing. Absolute/traversal/symlink inputs, alternate geometry versions, imported helpers from another checkout, source drift and schema drift are refused.

The base validator retains all ten earlier state objects. DE contributes two general-filed rows whose name/party/status/filing-date literals agree with the linked workbook, plus three separately declared write-ins. The write-in page has no party column; party remains null/UNSPECIFIED. Qualified is a literal source status, not an independent legal conclusion. October 30 update text has no stated timezone.

NE contributes only the first-page bounded U.S. Senate block. Wrapped party labels remain exact; Republican is R, and Legal Marijuana NOW, Nebraska Working People, America First and By Petition remain UNSPECIFIED. No Democratic row is invented. September 11 printed edition and September 16 PDF creation/modification metadata remain distinct. The source's Final title does not mean we accept a final ballot. City/contact fields are never exported by the helper.

The dedicated fixture suite exercises the actual DE reader and actual NE physical reader against authored boxes/fake pdfplumber only. Baseline validation is deliberately stubbed with ten authored prior objects in these lifecycle fixtures, while earlier baseline parser tests run separately. Synthetic source hashes and import origins are patched explicitly within temporary fixture roots; no fixture enables a real acquisition or paid path. The actual cached preflight separately validates original sources and the ten real existing state objects in memory, without RunStore or named output files.

Success artifacts use the existing public readiness/local-only roster split. Arbitrary metadata is refused before RunStore; admitted hash/parser/runtime/cancellation failures record only exception type and a sealed failure summary. The replication pack refuses the `.local.` roster artifact. No dashboard/shared CLI/CI/common code changed.

## Acceptance criteria and current evidence

- Exact source/config/helper identity and runtime admission: worker fixtures/preflight pass; independent integration acceptance pending.
- Literal DE statuses/dates/write-in context, NE printed/metadata dates/labels: worker fixtures and cached source preflight pass; independent review pending.
- Ten accepted prior state objects preserved: exact canonical hashes match the accepted v1.6.1 run, whose six checksummed artifacts were reverified.
- Immutable failure/cancellation records and metadata/private-roster guards: eight new authored integration tests pass, including drift across each of six sources and all three cancellation/error classes for both readers.
- Recorded v1.7 readiness/replay and independent post-run review: NOT RUN, pending independent integration acceptance.
- Latest amendments, legal final ballots, geography, source-policy adoption, race selection and 2026 outcome evaluation: unresolved; no authority or completion inferred.

After independent approval, the separate entry point is `python -m civiclab.e01.ballots_v1_7 configs/e01_ballot_readiness_v1_7.json --root .` from a reviewed geometry environment. Do not execute it merely because this document lists it. No recorded run is authorized by this candidate receipt.
