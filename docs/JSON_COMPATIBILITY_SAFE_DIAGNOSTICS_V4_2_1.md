# Reservation acknowledgement remedy v4.2.1

Offline candidate; independent review pending. No live release, terminal launcher, owner migration or paid authority.

The independent v4.2 probe found that a reservation can be durably appended while the caller receives an exception instead of its receipt. The original executor's diagnostic incorrectly inferred `reservation_recorded: false` from that missing acknowledgement. The owner correctly retained the reservation, charge and dispatch; this was a diagnostic error, not a spending-limit bypass. Original v4.2 source and evidence remain preserved in commit `c568cd7`.

The separate `production_compatibility_v4_2_1.py` changes only executor/review identity, the diagnostic policy, and reservation observation. It reuses the unchanged v4.2 diagnostic transport. If failure occurs at the reservation boundary without a returned receipt, `reservation_recorded` is null and `reservation_observation` is `UNKNOWN_AT_RESERVATION_BOUNDARY`. Missing receipt and unknown amounts do not imply zero consumption. Before the reservation boundary is reached, the observation is false/`RESERVATION_NOT_REACHED`; with an acknowledged receipt it is true/`RECEIPT_ACKNOWLEDGED`. A missing local acknowledgement does not trigger a new reservation, owner recovery write, retry, refund, grant or additional request.

The new review kind and code contract require a separate exact executor review. No existing live release is changed. The original run03 remains one POST attempt, an unresolved UNCERTAIN 340-microdollar conservative charge, unknown provider billing and an exhausted one-dispatch allowance. This remedy cannot establish its historical cause or remove its barrier.

Forty-one authored tests cover the original 29 financial/crash/concurrency/HTTP regressions, ten safe-diagnostic checks and two additional tests. The new tests inject reservation errors both before any append and after the real authored owner has durably appended STARTED. Both must report unknown, while direct ledger inspection verifies the different retained states and zero POST calls. Another test reproduces the preserved original v4.2 misleading false result. Every account, credential, catalog, response and error is authored; no actual owner, key, raw source or network request is used.

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_production_compatibility_v4_2_1 tests.test_compatibility_safe_diagnostics_v4_2_1 -v
```

Any subsequent live test still requires a separately reviewed execution plan, resolution of the existing uncertainty barrier under the research controls, and explicit owner spending/dispatch authorization. These tests provide no authority to bypass that dependency. E01/E02 completion criteria remain unchanged.
