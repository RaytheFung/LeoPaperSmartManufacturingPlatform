# TASK4S Phase B Metadata Landing Report

## Outcome

Task 4S Phase B metadata-only landing passed.

This landing stayed narrow:

- no `good_qty` / `scrap_qty` semantics changed
- no dominant-event row identity semantics changed
- no full canonical rematerialization ran
- no ML, UI, optimization, maintenance-page, or Task 4T work was started

## Exact Landing Scope

The live write used the already-hardened repair helper unchanged:

- `csi_source_row_hash IS NOT NULL`
- `start_ts = '2025-01-01T00:00:00'`
- `end_ts = '2025-07-01T00:00:00'`
- `overlap_only = True`
- `quantity_rows_only = True`

This means the live landing touched only:

- Jan-Jun 2025
- `multiple_csi_overlap_flag = 1`
- quantity-bearing overlap rows only

Rows without quantity stayed outside the helper scope by default.

## Code And Validation Before Write

Additional Phase B hardening before the live write:

- `tests/test_fact_machine_hour_repair.py`
  - added a focused test proving an overlap row with `csi_source_row_hash` present but both `good_qty` and `scrap_qty` null is excluded by the default helper scope

Validation run before the write:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/fact_machine_hour_repair.py tests/test_fact_machine_hour_repair.py
./.conda311/bin/python -m unittest tests.test_fact_machine_hour_repair
```

Result:

- `Ran 9 tests`
- `OK`

## Backup

Fresh pre-write backup:

- `backups/manufacturing_data_task4s_phaseb_metadata_only_20260402_215301.db`

## Exact Landing Call

```python
repair_fact_machine_hour_quantity_audit_metadata(
    start_ts='2025-01-01T00:00:00',
    end_ts='2025-07-01T00:00:00',
    overlap_only=True,
    quantity_rows_only=True,
)
```

Helper return:

- `target_rows = 31,677`
- `audit_rows = 31,677`
- `preserved_existing_basis_rows = 13,024`
- `newly_reconstructible_rows = 18,647`
- `still_unreconstructible_rows = 0`
- `excluded_anomaly_rows = 6`
- `dominant_identity_conflict_rows = 0`
- `material_misaligned_rows = 19,944`
- `minute_budget_anomaly_rows = 7`

## Before / After Diagnostics

Exact scope for all before/after diagnostics:

```sql
FROM fact_machine_hour
WHERE csi_source_row_hash IS NOT NULL
  AND hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
```

Before landing:

- target rows: `31,677`
- quantity-bearing overlap rows in scope: `31,677`
- rows with null/non-positive `csi_qty_row_basis_minutes`: `18,653`
- rows with positive `csi_qty_row_basis_minutes`: `13,024`
- dominant-identity conflict rows: `0`
- anomaly rows in scope from landed metadata: `1`
- `good_qty` total: `76,513,478.7066695`
- `scrap_qty` total: `0.0`

After landing:

- target rows: `31,677`
- quantity-bearing overlap rows in scope: `31,677`
- rows with null/non-positive `csi_qty_row_basis_minutes`: `6`
- rows with positive `csi_qty_row_basis_minutes`: `31,671`
- dominant-identity conflict rows: `0`
- anomaly rows in scope from landed metadata: `7`
- `good_qty` total: `76,513,478.7066695`
- `scrap_qty` total: `0.0`

Arithmetic:

- null/non-positive basis rows shrank by `18,647`
- positive basis rows increased by `18,647`
- quantity totals were unchanged exactly

## Anomaly Reconciliation

The prompt asked to confirm that the previously visible single anomaly row remains non-problematic and excluded where appropriate.

What actually happened on the landed snapshot:

- anomaly rows in scope increased from `1` to `7`
- reason breakdown after landing:
  - `production_minutes_gt_60`: `6`
  - `negative_operational_minutes`: `1`
- the `6` rows that remain null/non-positive after landing are exactly the `6` `production_minutes_gt_60` anomaly rows
- there are `0` non-anomalous rows still left with null/non-positive landed basis

Interpretation:

- the previously visible single anomaly row did remain non-problematic
- Phase B re-exposed the broader anomaly family that earlier Task 4R diagnostics had already shown (`6` rows with `production_minutes_gt_60`, `1` with `negative_operational_minutes`)
- this did not change quantity totals or dominant-event identity

## Quantity Semantics Confirmation

Confirmed after landing:

- `good_qty` total unchanged
- `scrap_qty` total unchanged
- quantity allocation semantics unchanged
- dominant-event row identity unchanged

This Phase B landing is metadata-only.

## Drift Versus Older Official Task 4S Baseline

The live landed snapshot does not match the older official Task 4S read-only baseline.

Older official Task 4S baseline:

- quantity-bearing overlap rows: `31,681`
- null-basis rows: `12,427`
- anomaly rows: `1`

Current landed Phase B snapshot:

- quantity-bearing overlap rows: `31,677`
- null-basis rows: `6`
- anomaly rows: `7`

This drift is real and should be documented explicitly rather than papered over.

Interpretation:

- row-count drift (`31,681` vs `31,677`) predates the Phase B landing and reflects a changed live snapshot
- null-basis shrink is the actual effect of the Phase B metadata landing
- anomaly visibility now aligns again with the broader Task 4R anomaly family rather than the narrower older Task 4S read-only view

## Recommendation

This narrow metadata-only Phase B landing should now be considered passed.

What remains out of scope:

- any live quantity replacement
- any change to `good_qty` / `scrap_qty`
- any change to dominant-event identity
- any work outside the quantity-only overlap line

Recommended next step:

- retain current live dominant-event quantity semantics for now
- if a later explicit quantity-only follow-up is approved, use this landed metadata scope as the candidate set and keep the remaining `6` anomaly rows excluded unless a separate anomaly rule is explicitly approved
