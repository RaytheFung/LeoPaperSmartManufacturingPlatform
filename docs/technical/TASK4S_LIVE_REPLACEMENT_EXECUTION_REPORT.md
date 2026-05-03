# TASK4S Live Replacement Execution Report

## Outcome

This separate quantity-only live replacement execution task passed.

The live execution was completed on the active `manufacturing_data.db`.
Only `good_qty` / `scrap_qty` were updated.
No dominant-event row identity semantics changed.
No non-quantity field changed.
No quantity metadata was relanded.
No rollback was needed.

## Direct-Source-Verified Pre-Write Gate

Exact hardened scope:

```sql
FROM fact_machine_hour
WHERE csi_source_row_hash IS NOT NULL
  AND hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
```

Verified row-unique key:

- `rowid`

Uniqueness proof on the exact scope:

- exact-scope rows: `31,677`
- distinct `rowid`: `31,677`

Approved baseline recheck before write:

- eligible rows: `31,669`
- anomaly-excluded rows: `8`
- eligible dominant groups: `29,846`
- ineligible dominant groups: `2`
- dominant-identity conflict rows: `0`

Concurrent-writer precondition:

- final pre-write `lsof manufacturing_data.db` returned no open holders

## Validation Before Write

Commands run before the live update:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/csi_quantity_shadow.py core/fact_machine_hour_repair.py tests/test_csi_quantity_shadow.py tests/test_fact_machine_hour_repair.py
./.conda311/bin/python -m unittest tests.test_csi_quantity_shadow tests.test_fact_machine_hour_repair
```

Result:

- `Ran 15 tests`
- `OK`

## Backup And Rollback Artifacts

Fresh full SQLite backup:

- `backups/manufacturing_data_task4s_live_qty_replace_20260402_172313.db`

Rollback snapshot DB:

- `backups/task4s_live_qty_replace_rollback_20260402_172313.db`

Rollback snapshot schema:

- `rollback_snapshot(target_rowid PRIMARY KEY, canonical_machine_id, hour_ts, csi_source_row_hash, pre_good_qty, pre_scrap_qty)`

Rollback snapshot key:

- `target_rowid`

## Exact Live Execution Scope

Targeted live update set:

- all `31,669` eligible rows
- across `29,846` fully eligible dominant groups
- excluded rows: `8`
- excluded dominant groups: `2`

Exclusion policy kept fixed:

- any dominant group containing `csi_qty_minute_budget_anomaly_flag = 1` stayed out of scope
- any dominant group with null/non-positive `csi_qty_row_basis_minutes` stayed out of scope
- any dominant group with null/non-positive `production_minutes` stayed out of scope

Live update method:

- built staging for the full eligible dominant-group scope only
- computed replacement quantity from the approved production-share shadow logic
- updated only `good_qty` and `scrap_qty`
- applied the update inside a single explicit transaction

## Before / After Totals

Exact hardened-scope totals before write:

- `good_qty`: `76,513,478.70666972`
- `scrap_qty`: `0.0`

Exact hardened-scope totals after commit:

- `good_qty`: `76,513,478.70666958`
- `scrap_qty`: `0.0`

Interpretation:

- `good_qty` remained conserved within floating-point noise only
- `scrap_qty` remained conserved exactly

## Conservation And Safety Result

Transaction-scoped validations passed:

- target row count matched staging row count exactly
- only approved eligible rows were targeted
- no anomaly-excluded group appeared in the update set
- no non-quantity field changed
- no target row ended with negative `good_qty` or negative `scrap_qty`
- per-dominant-group totals were conserved within tolerance

Per-group conservation result:

- passed

Rollback needed:

- no

## Actual Effect

Actual materially changed rows versus rollback snapshot:

- `3,388`

Post-write residual read-only shadow diagnostics:

- eligible rows: `31,669`
- anomaly-excluded rows: `8`
- eligible dominant groups: `29,846`
- ineligible dominant groups: `2`
- aggregate absolute `good_qty` drift: `2.429852152818768e-10`
- aggregate absolute `scrap_qty` drift: `0.0`
- residual materially changed eligible rows: `0`
- post-write current `good_qty` total: `76,513,478.70666958`
- post-write shadow `good_qty` total: `76,513,478.70666958`
- post-write current `scrap_qty` total: `0.0`
- post-write shadow `scrap_qty` total: `0.0`

Interpretation:

- the eligible live scope now matches the approved production-share contract
- the only remaining out-of-scope rows are the fixed anomaly exclusions

## Top Affected Buckets

Top affected machines by materially changed rows:

- `035-017: 192`
- `024-147: 184`
- `035-018: 144`
- `024-144: 140`
- `166-002: 134`
- `024-143: 124`
- `024-141: 110`
- `024-140: 108`
- `024-110: 88`
- `024-048: 86`

Top affected task names:

- `印色: 2,218`
- `UV(染): 408`
- `印色+光水油(局部): 121`
- `印色+光水油(染): 120`
- `UV(局部): 106`
- `印色+啞水油(染): 100`
- `印色+啞水油(局部): 72`
- `印色+半光啞水油(染): 53`
- `光水油(染): 28`
- `印刷啤: 26`

Top affected material codes:

- `PA0002500072-01-90: 12`
- `PF0002403237-02-01: 12`
- `PA3002500066-03-01: 11`
- `PA0002417944-01-90: 10`
- `PA0002501038-01-09: 9`
- `PF0002302506-08-01: 8`
- `PG0002500221-05-01: 8`
- `PH0002201236-03-01: 6`
- `PB1072100270-02-01: 5`
- `PA2002500150-01-01: 4`

## Exact Reason For Repo Changes

- [`core/fact_machine_hour_repair.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/fact_machine_hour_repair.py): added the guarded Task 4S live execution helper with rowid uniqueness proof, backup/snapshot creation, transaction-scoped staging, quantity-only update logic, invariant checks, and post-write diagnostics.
- [`tests/test_fact_machine_hour_repair.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_fact_machine_hour_repair.py): added focused write-path coverage for the positive live replacement path and the early-abort baseline-mismatch path.
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md): updated the live execution ledger to reflect that the approved narrow quantity replacement is now active on eligible groups only.
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md): indexed this execution report.
- this report records the live write and its exact safety evidence

## Decision

This live execution should now be marked officially passed.
