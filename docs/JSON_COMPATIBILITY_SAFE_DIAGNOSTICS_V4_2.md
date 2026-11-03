# Compatibility diagnostics v4.2 candidate

Status: offline candidate, pending independent review. No live release, terminal continuation, new approval, owner initialization or paid execution is provided.

Run03 attempted one POST, recorded no generation ID and retained 340 microdollars as conservative UNCERTAIN consumption. The provider charge and precise failure cause are unknown. Independent retained-record review is in `reports/INDEPENDENT_AUDIT_JSON_COMPATIBILITY_RUN03_UNCERTAIN_V1.json`. The original one-dispatch allowance is exhausted. These changes cannot recover the missing historical HTTP status or make the old command safe to rerun.

The separate `production_compatibility_transport_v4_2.py` preserves fixed endpoints, verified TLS, disabled proxies/redirects, one attempt, socket/cooperative time limits, bounded response reads, strict framing, duplicate/nonfinite JSON refusal and observed close-failure propagation. Its diagnostic includes only closed stage/category strings, an observed integer HTTP status or null, and a close-failure boolean. HTTP error bodies are closed without being read. URLs, reason strings, headers, exception messages, credentials and response bodies are excluded. A 401 status alone does not prove a particular credential defect; a timeout does not establish whether a provider accepted the request.

The separate `production_compatibility_v4_2.py` keeps reservation, reconciliation, auxiliary-usage, uncertainty, cancellation, checkpoint and global owner controls. Its distinct execution/review kind and code contract prevent reuse of a v4.1 executor review. Failure journals and the raised exception carry the same safe diagnostic: executor stage, POST/statistics attempt counts, whether a reservation was recorded, observed ledger reservation/charge values, and known provider cost or null. A reserved stop before POST is distinguished from a stop before reservation and from an attempted POST. Custom exception class names are replaced by a closed fallback. Cancellation still propagates; an unwritable journal does not promise durable diagnostics or allow a retry.

The executed v4/v4.1 transport, executor, terminal launchers, releases, actual journals and owner ledger remain unchanged. The public CLI is not switched to this candidate. No new lifetime cap, reset, refund, billing lookup or request follows from this component.

Acceptance requires independent exact-code review and authored adversarial evidence. The 29 copied regression tests cover financial/usage domains, process death, concurrent dispatch refusal, checkpoint failure, secret-body refusal and HTTP bounds. Ten added tests cover safe HTTP status codes, error-body refusal, timeout/JSON/header distinctions, close failure, cancellation, closed fields, complete fake-HTTP-to-journal reporting, pre-reservation/pre-POST stops, untrusted exception class names and statistics versus response-validation stages. All credentials, OS homes, catalogs, HTTP replies and errors in these tests are authored fixtures.

Reproduce offline:

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_production_compatibility_v4_2 tests.test_compatibility_safe_diagnostics_v4_2 -v
```

After component acceptance, a replacement live test still needs a separately reviewed plan that preserves the unresolved run03 history, explicitly handles the existing uncertainty barrier, and obtains owner authority for any additional dispatch and budget. This candidate supplies no such authority and must not silently replace the exhausted check. E02 research additionally requires accepted population/treatment preparation, a full matched mock run and an approved priced protocol. E01's retrospective statistical baseline remains independently actionable offline.
