# Alabama pure document reconciler v1: authored implementation candidate

Status: PENDING INDEPENDENT CODE / PRIVACY / FIXTURE REVIEW. Methods acceptance is `reports/INDEPENDENT_AUDIT_E01_AL_STANDALONE_V1_METHODS.json`, SHA `e765ea724086ea5ae747cece551c05358d20f7eb6f09c46f63b648efe0abbc18`. The metadata proposal and all earlier v1.9/commit-clarification files remain unchanged.

## Implemented scope

`src/civiclab/e01/alabama_documents_v1.py` provides one public execution boundary, `read_sources(root, contract)`. It verifies source/render/metadata/transcription/audit/release bindings and deterministically reconciles independently transcribed literals. It does not extract PDF text, render images, perform OCR, infer names or call a model. The text-available Republican extraction agreement check remains optional and NOT_IMPLEMENTED; the source-bound audited-transcription route covers the proposed six occurrences without pretending that image-only PDFs have text.

The exact current runtime contract is `configs/e01_al_standalone_runtime_contract_v1_candidate.json`, canonical SHA `8c09beb1fec22a3194ec82d6f30c9662d0392f807b406520e69bc2cefe85dd1d`. All actual transcription/audit paths/hashes/sizes, three release-document paths/hashes/sizes and execution authorizations are null; `approved` is false. The actual contract always refuses before root inspection, source open or any RunStore. Merely setting a flag, adding a caller receipt or changing a digest fails exact metadata admission. There is no production owner/source-authorization factory or actual release in this candidate. Fixtures explicitly patch the trusted canonical constant/import origin for temporary authored inputs; they confer no actual authority.

## Pure admission and binding

The module copies a closed built-in metadata tree (bounded depth/node/string/integer sizes) before admitting its exact canonical digest. It never calls custom serialization/deepcopy hooks. All downstream paths, dates, page roles, unknowns and hash authorities derive from that detached snapshot. Null authority/transcription/audit checks precede root access.

After admitted non-null fixture authority, check module origin, root ancestry and exact current module bytes. Verify pinned proposal/methods/role/audit metadata; five distinct source IDs/paths with exact body hashes/sizes and1MiB ceiling;47 unique complete source-page/render associations with8MiB/image and376MiB total ceilings;64KiB transcript/audit/release ceilings. Stream source/image hashes in64KiB blocks rather than retaining image/PDF bodies. Regular-file, lexical path, containment, symlink and file identity/mtime/size guards apply. No rendering dependencies are needed: this candidate uses Python standard library only. Repeat all bindings and module/root checks after reconciliation before returning a bundle.

Fixture release documents bind the exact source snapshot; the code-review fixture additionally binds module bytes. These fake documents test structural reconciliation, not human approval or authenticity. The disabled real runtime will require separately reviewed actual release/admission design and independently accepted exact code/runtime/transcription/audit pins; there is no automatic authorization obtained by editing the runtime or replacing its canonical constant. Do not treat this authored template as a usable actual-source permission mechanism.

The reader is no-write and creates no RunStore, logger, child success, network connection or directory. It returns no partial result on hash/parse/schema/cancellation failure. Exported errors contain only safe type/static text, with no retained exception cause/context; KeyboardInterrupt/SystemExit propagate without private messages. Recording, failure/partial-write retention and commit/ACK handling belong to a later separately reviewed standalone preflight wrapper, which is NOT_IMPLEMENTED here.

## Transcription and independent audit

A closed local transcript contains exactly six ordered occurrences. Each binds source hash, physical page, render hash, reviewed source role, party context, historical flag and structured document-date evidence. It contains literal office/name text and separate SHA-256 values for their UTF-8 transcription bytes. Those hashes describe transcribed text, not guessed original character encoding in an image PDF.

The separately hash-bound independent audit must attest the exact transcript hash, source snapshot and six occurrence witnesses including name/office UTF-8 hashes, dates, roles and transcription method. Changing/resealing transcript data alone is insufficient. Even with a resealed fixture audit, semantic disagreement between grouped literals, changed historical/date/party/page roles, extra contact/party-class/legal fields and unexpected schemas refuse. The proposed actual independent audit does not yet exist; a fake PASS in a fixture is not real independent review.

Identity compares trimmed/collapsed whitespace only; original display literals and hashes remain unchanged. Punctuation, accents and case are significant. Every occurrence is retained: state Democratic3/8/9 and party Democratic2 produce one four-occurrence document group; state Republican2 and party Republican2 produce a two-occurrence document group. These are source-context groups, not a certified exhaustive ballot, distinct-person count, active-candidate list, legal nominees or forecasting D/R pair. No normalization to party_class or default replacement occurs.

The final private payload annotates each occurrence with the bound independent-audit SHA after audit verification. This avoids a circular transcript-hash/audit-hash dependency: the input transcript does not hash a future audit of itself; the verified output carries that provenance. It retains the41 other page associations as reviewed role exclusions. Independent state-office-only, internal committee, House-only and historical conditional-primary entries cannot become federal Senate occurrences.

## Dates, unknowns and outputs

Document signature/amendment/history/receipt dates remain typed, separately linked evidence; they are not candidate filing dates or pre-results timestamps. Historical Democratic page8's partly unread received stamp is UNKNOWN; page9's observed July1 stamp is distinct. Partial stamps on excluded pages11/13 remain unguessed in the role inventory. Generic unread/unused occurrence stamps remain unadjudicated rather than inferred from neighboring pages. Current source collection does not establish as-of admissibility.

`DocumentBundle` hides values in repr and stores serialized detached private/public payloads. Each access returns a fresh object. Only `private_payload()` contains occurrence/group names and offices; external recording must use ignored `.local.json` paths. Public diagnostics have a closed explicit schema and validator: source hashes/counts,47 page associations, six observed occurrences, two document-supported groups, two historical occurrences, six fixed source roles and four exact typed UNKNOWNs. Unknown schemas/roles/additional fields, boolean count coercions, name extensions and adoption flags refuse. No name/contact/full-text export or live HTTP/viewer integration is added.

Final printed ballot, write-in, independent legal-nominee adjudication and latest-amendment completeness remain UNKNOWN. Both source-adoption and coverage-promotion flags are false; final ballots/cost/model calls are zero. Existing reproduction package guards refuse private `.local.json` artifacts in an authored recording fixture. No source redistribution or publication authority follows.

## Executed authored fixtures

The final evidence JSON records exact code/runtime/test pins, versions, commands and unchanged protected files. Reproduction:

```
PYTHONPATH=src .venv/bin/python -m unittest tests.test_e01_alabama_documents_v1 -q
PYTHONPATH=src data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11 -m unittest tests.test_e01_alabama_documents_v1 -q
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e01*.py' -q
```

All source/image/transcript/audit/release bytes in these tests are authored temporary fixtures; actual PDFs/renders/private references are never read or hashed. Fixtures test pure exact replay, six occurrence retention,41 exclusions, display UTF-8 hashes, whitespace-only comparison, accent/punctuation/case/office/missing-literal disagreement, null authority, custom hooks/nonfinite/duplicate JSON, historical/role/date/stamp/contact/legal mutations, missing/duplicate/reordered/collapsed occurrences, coedited audit witnesses, code/release/transcript binding, source/render coedits at raw-read attempts0/5/25/51/52/103 with fixed original authority, transcript/audit changes between passes, path/symlink/origin/missing/size failures, cancellation/SystemExit and safe error context. Public-schema/unknown coercion/adoption checks, private package refusal and seven simulated existing-viewer private/traversal/query path404 guards are included. The handler fixture uses no sockets or actual HTTP requests and asserts refusal before file access. These are engineering tests, not independent scientific or actual-source acceptance.

## Remaining gates

Independent exact code/privacy/fixture review; explicit bounded source/render/transcription release; independent literal transcription audit; separately reviewed actual admission/runtime amendment; authorized standalone recorded preflight/replay and post-run review; later readiness integration. The code does not self-release any stage. Actual source access, transcript, independent literal audit, recording wrapper, optional text extractor and actual-source feasibility remain incomplete. Approved experimental spend stays$0, and accepted coverage remains **12 document states / 21 unfinished jobs / zero final ballots**. No GET/UI/render/OCR/model action, actual helper invocation, source-policy/legal/final/latest/geography/selection/forecast/publication claim or coverage promotion occurred.
