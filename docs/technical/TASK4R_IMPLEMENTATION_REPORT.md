# TASK4R Implementation Report

## Outcome

Task 4R passed.

This task stayed metadata-only:

- no `good_qty` / `scrap_qty` allocation rewrite was applied
- no dominant-event identity rewrite was applied
- no ML logic or artifacts changed
- no UI work was started
- no Task 4S work was started

## Reconstruction Summary

- `CURRENT_REBUILD_STATUS.md` already marked Task 4Q passed as an audit-only closeout.
- Task 4Q established that the live overlap quantity contract remained dominant-event-only after Task 4P minute blending.
- The smallest safe Task 4R gap was first-class observability on `fact_machine_hour`, not quantity reallocation.
- A first attempt to reland Jan-Jun through the month-scoped full materializer path was rolled back to the fresh pre-write backup after that route started perturbing live row counts before metadata population completed.
- The final live landing used a narrower metadata-only canonical SQL backfill helper in `core/fact_machine_hour_repair.py` that leaves existing Gold row identity, minutes, and quantities untouched.

## Old Quantity Contract

The pre-Task-4R quantity contract was:

- row identity followed the dominant CSI event through `csi_source_row_hash`
- persisted row `production_minutes` followed the Task 4P blended minute contract
- `good_qty` / `scrap_qty` still used dominant-event production basis minutes
- that dominant-event quantity basis was not exposed as first-class Gold columns

In live code this remained true in both paths:

- `core/gold_fact_builder.py`
- `core/fact_machine_hour_repair.py`

## New Metadata Contract

Task 4R adds these first-class canonical Gold fields:

- `csi_qty_basis_method`
  - explicit statement of the current quantity contract: `csi_dominant_event_production_minutes_share`
- `csi_qty_row_basis_minutes`
  - the row-level dominant-event production basis minutes used by the current quantity contract
- `csi_qty_event_basis_minutes`
  - the cross-row denominator for the same dominant CSI source event
- `csi_qty_minutes_vs_production_diff`
  - signed drift between persisted row `production_minutes` and the quantity basis minutes
- `csi_qty_minutes_vs_production_abs_diff`
  - absolute drift magnitude
- `csi_qty_alignment_status`
  - explicit alignment label such as `aligned` or `material_misaligned`
- `csi_qty_material_misalignment_flag`
  - narrow integer flag for rows where the quantity contract drift is material
- `csi_qty_minute_budget_anomaly_flag`
  - narrow integer flag for suspicious minute-budget states
- `csi_qty_minute_budget_anomaly_reason`
  - reason label such as `production_minutes_gt_60` or `negative_operational_minutes`

Quantity provenance remains the existing first-class `csi_source_row_hash`.

## Why These Fields

- They expose the dominant-event quantity basis directly on Gold rows instead of leaving it buried in repair logic.
- They show the exact split between quantity basis minutes and persisted blended row minutes.
- They make the material Task 4Q mismatch queryable without reconstruction.
- They expose narrow anomaly visibility without claiming to solve quantity allocation.

## Code Changes

- `core/gold_fact_builder.py`
  - added the first-class `csi_qty_*` schema fields
  - builder/materializer quantity overlay now computes the audit metadata alongside unchanged quantity allocation
- `core/fact_machine_hour_repair.py`
  - mirrored the same `csi_qty_*` fields in the full repair path
  - added `repair_fact_machine_hour_quantity_audit_metadata(...)` for narrow metadata-only backfill onto existing Gold rows
- `core/canonical_materializer.py`
  - materializer path now carries the new audit fields when builder-driven quantity overlay is used
- `tests/test_gold_fact_builder.py`
  - added assertions for aligned and materially misaligned metadata cases
- `tests/test_fact_machine_hour_repair.py`
  - added a focused metadata-only backfill test
- `tests/test_canonical_materializer.py`
  - added assertions that the materializer path carries the same metadata

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/gold_fact_builder.py core/fact_machine_hour_repair.py core/canonical_materializer.py tests/test_gold_fact_builder.py tests/test_fact_machine_hour_repair.py tests/test_canonical_materializer.py
./.conda311/bin/python -m unittest tests.test_gold_fact_builder tests.test_fact_machine_hour_repair tests.test_canonical_materializer
```

Result:

- `Ran 85 tests in 1.355s`
- `OK`

## Live DB Landing Path

- active DB path: `manufacturing_data.db`
- fresh pre-write backup:
  - `backups/manufacturing_data_task4r_backup_20260402_035058.db`
- final landing path:
  - `repair_fact_machine_hour_quantity_audit_metadata(start_ts='2025-01-01T00:00:00', end_ts='2025-07-01T00:00:00')`
- landing scope:
  - Jan-Jun 2025
  - `multiple_csi_overlap_flag = 1`
  - existing rows with non-null `csi_source_row_hash`

Why this was the final landed route:

- it is a real canonical repair-module path
- it backfills only the new metadata columns
- it preserves live quantity semantics and overlap counts
- it avoided the broader risk of another full-table or full-month rewrite on the active DB

## Before / After Diagnostics

Scope for all live SQL:

- `fact_machine_hour`
- `hour_ts >= '2025-01-01T00:00:00'`
- `hour_ts < '2025-07-01T00:00:00'`
- `multiple_csi_overlap_flag = 1`

Before landing from the restored pre-write backup:

- overlap rows: `43,449`
- quantity-bearing overlap rows: `31,682`
- new `csi_qty_*` columns on active DB: absent
- overlap `good_qty` sum: `76,521,892.78259052`
- overlap `scrap_qty` sum: `0.0`

After final metadata-only landing:

- overlap rows: `43,449`
- overlap rows with `csi_source_row_hash`: `43,449`
- quantity-bearing overlap rows: `31,682`
- rows with landed `csi_qty_basis_method`: `35,869`
- rows with landed `csi_qty_row_basis_minutes`: `35,869`
- rows with landed `csi_qty_event_basis_minutes`: `35,869`
- rows with landed `csi_qty_alignment_status`: `35,869`
- rows with landed `csi_qty_material_misalignment_flag`: `35,869`
- rows with landed `csi_qty_minute_budget_anomaly_flag`: `35,869`
- quantity-bearing overlap rows with landed quantity-audit metadata: `31,682`
- materially misaligned rows from landed metadata: `19,948`
- minute-budget anomaly rows from landed metadata: `7`
  - `6` rows with `production_minutes_gt_60`
  - `1` row with `negative_operational_minutes`
- overlap `good_qty` sum after landing: `76,521,892.78259052`
- overlap `scrap_qty` sum after landing: `0.0`

Conclusion:

- overlap counts stayed unchanged
- quantity-bearing overlap counts stayed unchanged
- overlap quantity totals stayed unchanged
- Task 4R added observability only

## Representative Row Evidence

- `035-017 @ 2025-06-03T05:00:00`
  - `production_minutes = 54.36760896495606`
  - `good_qty = 1550.0`
  - `csi_qty_row_basis_minutes = 18.0`
  - `csi_qty_event_basis_minutes = 18.0`
  - `csi_qty_minutes_vs_production_abs_diff = 36.36760896495606`
  - `csi_qty_alignment_status = material_misaligned`
- `035-018 @ 2025-02-17T15:00:00`
  - `production_minutes = 53.787058030794725`
  - `good_qty = 1607.0`
  - `csi_qty_row_basis_minutes = 16.890202582335295`
  - `csi_qty_event_basis_minutes = 16.890202582335295`
  - `csi_qty_minutes_vs_production_abs_diff = 36.89685544845943`
  - `csi_qty_alignment_status = material_misaligned`
- `166-002 @ 2025-04-17T14:00:00`
  - `production_minutes = 276.57559944183396`
  - `good_qty = 130.7339444849789`
  - `csi_qty_row_basis_minutes = 51.94954109797846`
  - `csi_qty_event_basis_minutes = 363.646788847012`
  - `csi_qty_minutes_vs_production_abs_diff = 224.6260583438555`
  - `csi_qty_alignment_status = material_misaligned`
  - `csi_qty_minute_budget_anomaly_reason = production_minutes_gt_60`

## Remaining Limitations

- Task 4R does not change quantity allocation semantics.
- `7,580` overlap rows still have null landed quantity-basis metadata because they do not carry reconstructible positive dominant production basis minutes; however all `31,682` quantity-bearing overlap rows are covered.
- The landed anomaly flag is intentionally narrow and diagnostic only.
- The abandoned full materializer attempt was rolled back and is not the active landed state.

## Recommended Next Task Boundary

If further overlap quantity work is approved, the next task should stay quantity-only:

- decide whether dominant-event quantity semantics should be retained or replaced
- if replacement is approved, use the landed `csi_qty_*` metadata to implement and validate proportional quantity allocation
- keep ML, UI, and Task 4S out of scope until that quantity decision is complete
