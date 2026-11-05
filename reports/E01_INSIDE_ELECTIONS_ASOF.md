# Inside Elections as-of provenance check

November 3, 2026. Bounded read-only investigation; independent review pending. No change to the analytical cutoff, source policy, Cook proposal, selector or actual sample. No 2026 returns, model calls, payment, archive login, capture submission or publication.

## Publisher version metadata

The actual publisher-offered House URL has `v=1793388069`; interpreted as Unix seconds this is October 30, 2026, 19:21:09 UTC, exactly its captured `generated_at`. Senate `v=1793297246` similarly equals October 29, 2026, 18:07:26 UTC and its `generated_at`. Both captured exports declare last update October 29 at 13:05 -05:00, equivalent to the ordinary ratings pages' displayed 14:05 EDT. These are publisher-declared times, not independent historical observations.

The two equalities are consistent with a generation/cache-busting marker. They do not prove that the parameter selects an immutable version, that repeated requests cannot change content, or that its value cryptographically addresses a body. No inspected public ratings/export page documented such guarantees. The endpoint name includes `latest`; neither that name nor the timestamp resolves its semantics. No modified/missing/random `v` parameters, hidden endpoints or version grids were queried to infer behavior. No subscriber/developer archive was opened. The original exact offered URLs and publisher times remain in the JSON receipt.

The existing House/Senate SHA-256 values continue to identify the saved browser-visible UTF-8 JSON text. They are not relabeled HTTP wire-byte hashes, archived content digests or independent pre-cutoff evidence. Public publication labels, cache query parameters and retrieval on November3 cannot bind the exact text to an earlier cutoff by themselves.

## Independent public archive lookup

The Internet Archive's own [public API documentation](https://archive.org/help/wayback_api.php) describes an Availability API accepting an exact URL and requested timestamp, returning a closest accessible snapshot when available. It explains that an empty snapshot result can mean not archived **or not currently accessible**. Its documentation was read before using the offered public method; the unrelated CDX documentation link was inaccessible through the reader and was not used as permission for guessed queries.

Two bounded requests, one per exact publisher-offered URL with its original `v`, asked for timestamp `20261103045959` (the unchanged cutoff, November3 04:59:59 UTC). Both requests succeeded through the ordinary public index with JSON content. Each returned an empty `archived_snapshots` object, so no candidate snapshot timestamp, archived-body digest or archived/current-body identity could be verified. Requests and responses were observed around November3 11:42:29 UTC. Response byte counts, SHA-256 hashes, server Date/Content-Type, exact request URLs and returned JSON are preserved in `reports/E01_INSIDE_ELECTIONS_ASOF.json`.

The lookup made zero retries, used a 20-second timeout and 64 KiB response ceiling, and did not use wildcard target URLs, altered publisher query strings, paid services, credentials, Save Page Now, challenge solving or archive capture creation. Availability's closest-match semantics would require rejecting a post-cutoff result even if one had been returned. No result is interpreted as a universal proof of historical absence, an archive's full coverage, or a license decision. Other independent evidence could still exist; none is verified here.

## Finding and next step

**Independent pre-cutoff binding remains NOT ESTABLISHED.** We now have a concrete negative availability observation for the exact current export URLs, alongside current publisher-declared metadata and honest text-capture hashes. This is an evidence gap, not an internal-research license block. Do not turn it into an invented earlier archive, relax the cutoff silently, or treat a current commit/hash as an old prospective submission.

Next unblocked work is separate source/method review of the proposed publisher-declared-as-of reconstruction versus strict archived-input requirements. Any change of evidence tier requires an explicit reviewed amendment; this check adopts neither tier, performs no selection and leaves REAL disabled. Independently timestamped snapshots or publisher version evidence can be evaluated if they later become available through permitted routes.

Task contract: E01_INSIDE_ELECTIONS_ASOF_PROVENANCE_CHECK. Files changed: this report and its JSON only. Reproduction: decode the two recorded integers and compare with already cached `generated_at`; follow the cited API documentation and its exact bounded requests, without broadening target scope. Checks: arithmetic equality, two successful public metadata responses, JSON syntax and whitespace; no software implementation or scientific validation. Actual cost: $0; no full publisher content committed. Independent auditor certification is separate.
