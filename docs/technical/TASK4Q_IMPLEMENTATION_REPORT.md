# TASK4Q Implementation Report

## Outcome

Task 4Q passed.

This task stayed audit-only:

- no quantity implementation was applied
- the active DB was not written
- no ML logic or artifacts changed
- no UI/orchestration work was started

The audit answer is:

- the current quantity contract is still dominant-event-only in live code
- after Task 4P, persisted row `production_minutes` and quantity basis minutes are no longer the same concept
- on the active Jan-Jun 2025 DB, that mismatch is material rather than a documentation-only nuance or a minor residual edge case

Correction note for this recovery run:

- the earlier Task 4Q draft mixed different subsets
- its headline materially misaligned total used the quantity-bearing overlap subset
- its monthly materially misaligned table and top-task materially misaligned counts used a broader overlap-row subset
- it also carried a stale quantity-bearing denominator off by one row
- this corrected report recomputes all published quantity-mismatch totals from one consistent subset:
  - Jan-Jun 2025 overlap rows with `multiple_csi_overlap_flag = 1`
  - restricted to rows with non-null `good_qty` or `scrap_qty`
  - dominant-event quantity basis reconstructed from the stored dominant `csi_source_row_hash`

## Reconstruction Summary

- `CURRENT_REBUILD_STATUS.md` already marks Task 4P passed.
- Task 4P closed minute semantics only and explicitly left quantity semantics unchanged.
- The active runtime DB still resolves through `core/runtime_paths.py:get_database_path()` to `manufacturing_data.db`.
- The smallest safe Task 4Q question was whether dominant-event quantity basis now diverges materially from the landed blended row-minute contract on live Jan-Jun Gold.

## Current Quantity Contract Summary

### Python Gold builder

From `core/gold_fact_builder.py`:

- `_overlay_fact_row_with_csi(...)` still chooses one dominant CSI overlap candidate for row identity/context:
  - `order_id`
  - `order_suffix`
  - `material_code`
  - `task_name`
  - `team_leader`
  - `actual_speed_per_hour`
  - `csi_source_row_hash`
- The same function writes persisted row minute fields from `_build_csi_row_minute_contract(overlaps)`, which may blend and scale multiple CSI candidates into one row-level `production_minutes`.
- `_overlay_fact_row_with_csi(...)` also stores the dominant event's own production contribution in `source_flags["csi_dominant_production_minutes"]`.
- `_csi_quantity_basis_minutes_from_row(...)` reads `csi_dominant_production_minutes` first and falls back to row `production_minutes` only if that dominant-event flag is absent.
- `_build_csi_quantity_updates(...)` allocates `good_qty` / `scrap_qty` by:
  - `quantity_basis_minutes / basis_minutes`
  - allocation method: `csi_production_minutes_share_by_dominant_event`
- `basis_minutes` is the cross-row sum of dominant-event quantity-basis minutes for all rows carrying the same `csi_source_row_hash`.

### SQL repair path

From `core/fact_machine_hour_repair.py`:

- `temp_task4g_csi_row_blend` computes the persisted blended row minute fields.
- `temp_task4g_csi_dominant` keeps the dominant row identity and the dominant event’s own `dominant_production_minutes`.
- `temp_task4g_csi_basis` groups by `source_row_hash` and sums `dominant_production_minutes` into `basis_minutes`.
- The final SQL quantity update writes:
  - `good_qty = event_good_qty * dominant_production_minutes / basis_minutes`
  - `scrap_qty = event_scrap_qty * dominant_production_minutes / basis_minutes`

### Contract conclusion

- Row identity and quantity still follow the dominant event only.
- Persisted row `production_minutes` now follow the blended multi-event minute contract.
- Therefore Task 4P intentionally created a split contract:
  - row operational minutes are blended
  - quantity remains dominant-event-only

## Live DB Diagnostics

### Exact SQL/data-scope diagnostics run

Scope used for all direct DB queries:

- `fact_machine_hour`
- `hour_ts >= '2025-01-01T00:00:00'`
- `hour_ts < '2025-07-01T00:00:00'`
- `multiple_csi_overlap_flag = 1`

Direct SQL run:

```sql
SELECT COUNT(*) AS overlap_rows,
       SUM(CASE WHEN good_qty IS NOT NULL OR scrap_qty IS NOT NULL THEN 1 ELSE 0 END) AS qty_overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1;

SELECT substr(hour_ts,1,7) AS month, COUNT(*) AS qty_overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
GROUP BY 1
ORDER BY 1;

SELECT COUNT(DISTINCT canonical_machine_id) AS distinct_machines
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL);

SELECT canonical_machine_id, COUNT(*) AS qty_overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
GROUP BY canonical_machine_id
ORDER BY qty_overlap_rows DESC, canonical_machine_id
LIMIT 10;

SELECT COALESCE(NULLIF(TRIM(task_name),''), '<NULL>') AS task_name, COUNT(*) AS qty_overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
GROUP BY 1
ORDER BY qty_overlap_rows DESC, task_name
LIMIT 10;

SELECT COALESCE(NULLIF(TRIM(material_code),''), '<NULL>') AS material_code, COUNT(*) AS qty_overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
GROUP BY 1
ORDER BY qty_overlap_rows DESC, material_code
LIMIT 10;

SELECT COUNT(*)
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND production_minutes > 60;
```

Additional read-only reconstruction diagnostic:

- dominant-event quantity-basis minutes were reconstructed from the live `csi_job_event` rows using the same two-path rule as the current repair/builder contract:
  - safe fractional path:
    - `actual_prod_minutes * (hour_post_setup_overlap_minutes / event_window_minutes)`
  - fallback path:
    - dominant-event wall-clock `production_overlap_minutes`
- materiality threshold:
  - `abs(persisted production_minutes - dominant-event quantity-basis minutes) > 0.5`

### Headline numbers

- overlap rows: `43,453`
- quantity-bearing overlap rows: `31,682`
- distinct machines with quantity-bearing overlap rows: `84`
- overlap rows with `production_minutes > 60`: `6`

### Monthly quantity-bearing overlap rows

| Month | Quantity-bearing overlap rows |
| --- | ---: |
| 2025-01 | 3,837 |
| 2025-02 | 3,717 |
| 2025-03 | 5,470 |
| 2025-04 | 5,865 |
| 2025-05 | 6,560 |
| 2025-06 | 6,233 |

### Top machines

| Machine | Quantity-bearing overlap rows |
| --- | ---: |
| `024-143` | 1,126 |
| `024-147` | 1,096 |
| `024-144` | 1,041 |
| `035-017` | 1,024 |
| `024-142` | 781 |
| `024-141` | 753 |
| `035-018` | 747 |
| `024-110` | 707 |
| `166-002` | 707 |
| `024-117` | 699 |

### Top task names

| Task name | Quantity-bearing overlap rows |
| --- | ---: |
| `印色` | 21,373 |
| `UV(染)` | 2,228 |
| `印色+光水油(染)` | 1,385 |
| `印色+光水油(局部)` | 1,126 |
| `印色+啞水油(染)` | 928 |
| `印色+啞水油(局部)` | 638 |
| `UV(局部)` | 571 |
| `印色+半光啞水油(染)` | 514 |
| `印色+印刷啤` | 461 |
| `印刷啤` | 268 |

### Top material codes

This remains broad and long-tailed. The top material buckets among quantity-bearing overlap rows are still only in the tens:

| Material code | Quantity-bearing overlap rows |
| --- | ---: |
| `PA3002200526-03-01` | 25 |
| `PA1002501179-01-05` | 23 |
| `PA0002101031-01-07` | 18 |
| `PA3002201007-02-01` | 15 |
| `PA0002500072-01-90` | 12 |
| `PF0002403237-02-01` | 12 |
| `PH0002100010-31-01` | 12 |
| `PA0002501038-01-09` | 11 |
| `PA0002501038-01-90` | 11 |
| `PA3002500066-03-01` | 11 |

## Quantity Blast Radius

Using the live dominant-event reconstruction above:

- quantity-bearing overlap rows audited: `31,682`
- materially misaligned quantity-bearing rows: `19,948`
- materially misaligned share of quantity-bearing overlap rows: `62.963197%`
- materially misaligned share of all overlap rows: `45.907072%`
- total absolute drift: `163,530.086072` minutes
- max single-row drift: `224.6261` minutes

Arithmetic check:

- `19,948 / 31,682 = 0.62963197 = 62.963197%`
- `19,948 / 43,453 = 0.45907072 = 45.907072%`

Monthly materially misaligned quantity-bearing rows:

| Month | Quantity-bearing overlap rows | Materially misaligned rows |
| --- | ---: | ---: |
| 2025-01 | 3,837 | 2,487 |
| 2025-02 | 3,717 | 2,478 |
| 2025-03 | 5,470 | 3,420 |
| 2025-04 | 5,865 | 3,583 |
| 2025-05 | 6,560 | 4,134 |
| 2025-06 | 6,233 | 3,846 |

Monthly-sum check:

- `2,487 + 2,478 + 3,420 + 3,583 + 4,134 + 3,846 = 19,948`

Top machines by materially misaligned rows:

| Machine | Materially misaligned rows |
| --- | ---: |
| `035-017` | 987 |
| `024-143` | 870 |
| `024-144` | 799 |
| `035-018` | 711 |
| `024-142` | 636 |

Top task names by materially misaligned rows:

| Task name | Materially misaligned rows |
| --- | ---: |
| `印色` | 13,459 |
| `UV(染)` | 2,083 |
| `印色+光水油(染)` | 694 |
| `印色+光水油(局部)` | 551 |
| `UV(局部)` | 448 |

## Representative Row Evidence

### Sample A: extreme drift and impossible persisted production

`166-002 @ 2025-04-17T14:00:00`

- `order_id = J250010360`
- `task_name = UV(染)`
- `material_code = PC0002500169-06-01`
- persisted `production_minutes = 276.575599`
- `good_qty = 130.733944`
- dominant event:
  - `csi_source_row_hash = c5ddf241...`
  - event `actual_prod_minutes = 453.0`
  - event `planned_stop_minutes = 60.0`
  - event `unplanned_stop_minutes = 10.0`
- reconstructed dominant-event quantity-basis minutes: `51.9495`
- absolute drift: `224.6261`

### Sample B: quantity still tied to a small dominant basis while row minutes are much larger

`035-018 @ 2025-02-17T15:00:00`

- `order_id = J250000856`
- `task_name = UV(染)`
- `material_code = PB1022500020-01-01`
- persisted `production_minutes = 53.787057`
- `good_qty = 1607.0`
- dominant event:
  - `csi_source_row_hash = 0f381855...`
  - event `actual_prod_minutes = 18.0`
  - event `unplanned_stop_minutes = 2.0`
- reconstructed dominant-event quantity-basis minutes: `16.8902`
- absolute drift: `36.897`

### Sample C: same pattern on another live UV row

`035-017 @ 2025-06-03T05:00:00`

- `order_id = J250015657`
- `task_name = UV(染)`
- `material_code = PB1062500219-01-01`
- persisted `production_minutes = 54.367609`
- `good_qty = 1550.0`
- dominant event:
  - `csi_source_row_hash = cf9ec4ec...`
  - event `actual_prod_minutes = 18.0`
  - event `planned_stop_minutes = 0.0`
  - event `unplanned_stop_minutes = 0.0`
- reconstructed dominant-event quantity-basis minutes: `18.0`
- absolute drift: `36.3676`

## Test Coverage Cross-Check

Existing tests already lock the current quantity contract in place:

- `tests/test_gold_fact_builder.py`
  - cross-hour `good_qty` / `scrap_qty` sums back to event totals
  - multi-event blended minutes do not rewrite dominant quantity basis
  - zero/missing quantity behavior remains stable
- `tests/test_fact_machine_hour_repair.py`
  - SQL repair populates quantity and preserves dominant quantity under multi-event minute blending
- `tests/test_canonical_materializer.py`
  - backfill/materialization preserves the dominant quantity contract

No new helper or unit test was required for this audit-only task.

## Recommendation

This is a material semantic mismatch worth a follow-up implementation, not just a documentation update.

The recommended next follow-up is a two-step quantity-only track:

1. add explicit quantity-audit metadata first
2. only after that metadata and contract are accepted, consider quantity-only proportional allocation

Why this is the safer recommendation:

- the mismatch is large enough to justify more than a wording change
- the active DB does not currently expose the quantity-basis audit flags that would make live drift obvious row-by-row
- adding audit metadata first keeps the next step narrow, observable, and reversible
- it avoids jumping straight from minute blending to a full quantity rewrite without first making the contract fully inspectable on live Gold

## Validation

- No code changes were needed for Task 4Q.
- No DB writes were performed.
- No py_compile or test run was required because no helper/test/code file changed.
