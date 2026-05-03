# TASK4O Implementation Report

## Outcome

Task 4O passed.

This task stayed audit-only. It did not change Gold logic, did not rewrite the active DB, did not retrain ML artifacts, and did not widen into a blending implementation.

The audit answer is:

- the active Jan-Jun 2025 blast radius is material
- the current dominant-event rule is not just a harmless state simplification
- the observed effect is mixed:
  - state/context simplification
  - minute-attribution loss
  - quantity-attribution loss
  - idle suppression in the live Python contract

Because quantity in Task 3C6 intentionally follows the already-selected minute contract, the safest next step is to split future work into two smaller follow-ups:

1. minute semantics first
2. quantity semantics only after the minute contract is accepted

## Reconstruction Summary

- `CURRENT_REBUILD_STATUS.md` already marked Task 4N passed before this run.
- Task 4N already closed the default-team audit and explicitly left multi-event CSI blending as a remaining canonical limitation.
- `core/canonical_materializer.py` shows that historical/backfill Gold on the active DB is rebuilt through `materialize_backfill_month(...)`, which calls `repair_fact_machine_hour_operational_overlays(...)`.
- The active runtime DB path still resolves through `core/runtime_paths.py:get_database_path()` to `manufacturing_data.db`.

## Exact Current Live Code Rule

### Python Gold builder contract

From `core/gold_fact_builder.py`:

- A CSI event is an overlap candidate for a machine-hour when either its inferred setup window or its production window intersects that hour.
- `multiple_csi_overlap_flag` is set when more than one CSI event overlaps the same machine-hour.
- The dominant event is chosen by:
  1. greatest `total_overlap_minutes`
  2. then greatest `production_overlap_minutes`
  3. then lexical `source_row_hash`
- `machine_state` comes only from the dominant event, in this implemented priority:
  1. `setup_changeover`
  2. `production`
  3. `planned_stop`
  4. `unplanned_stop`
- Minute attribution also comes only from the dominant event:
  - safe path: fractional reconciliation from that event’s post-setup window
  - fallback path: dominant-event wall-clock production overlap only
- Quantity also comes only from the dominant event:
  - `good_qty` / `scrap_qty` are allocated by the row’s dominant-event `production_minutes` share
  - method recorded as `csi_production_minutes_share_by_dominant_event`
- Idle logic skips any multi-overlap row entirely via `idle_multiple_csi_overlap`.

### SQL repair path used by the active Jan-Jun DB

From `core/fact_machine_hour_repair.py`:

- The active backfill path uses the same dominant-event ordering:
  1. total overlap desc
  2. production overlap desc
  3. `source_row_hash`
- It writes only the dominant event’s operational context, minute fields, and quantity allocation.
- It sets `multiple_csi_overlap_flag` from `overlap_candidate_count > 1`.
- It does not rebuild idle/source-flag audit markers in the same way the Python builder does.

This means the active Jan-Jun DB and the live Python contract agree on the dominant-event simplification for state/minutes/quantity, but the active DB does not expose idle-skip markers directly.

## Test Cross-Check

Existing tests still lock the dominant-event contract in place:

- `tests/test_gold_fact_builder.py`
  - `test_dominant_event_selection`
  - `test_multi_event_overlap_flagging`
  - `test_csi_planned_stop_minutes_are_allocated_when_reconciliation_is_safe`
  - `test_csi_unplanned_stop_minutes_are_allocated_when_reconciliation_is_safe`
  - `test_csi_good_qty_allocation_sums_back_to_event_total_across_hours`
  - `test_idle_is_skipped_for_multiple_csi_overlap`

Those tests confirm that the current contract is intentional, deterministic, and still live.

## Active DB Blast Radius

### Scope

- Active runtime DB: `manufacturing_data.db`
- Time window audited: `2025-01-01` through `2025-06-30`
- Jan-Jun Gold rows: `378,352`
- Jan-Jun overlap rows with `multiple_csi_overlap_flag = 1`: `43,453`
- Jan-Jun overlap share: `11.4848%`

### Monthly overlap rows

| Month | Overlap rows |
| --- | ---: |
| 2025-01 | 4,894 |
| 2025-02 | 4,862 |
| 2025-03 | 7,863 |
| 2025-04 | 8,254 |
| 2025-05 | 8,816 |
| 2025-06 | 8,764 |

### Affected machines

- distinct affected machines across Jan-Jun: `85`

| Month | Affected machines |
| --- | ---: |
| 2025-01 | 81 |
| 2025-02 | 82 |
| 2025-03 | 83 |
| 2025-04 | 82 |
| 2025-05 | 84 |
| 2025-06 | 82 |

### Top affected machines

| Machine | Overlap rows |
| --- | ---: |
| `024-143` | 1,330 |
| `024-147` | 1,228 |
| `024-144` | 1,076 |
| `035-017` | 1,024 |
| `024-141` | 865 |
| `024-089` | 837 |
| `024-142` | 817 |
| `024-140` | 811 |
| `024-074` | 808 |
| `024-150` | 787 |

### Top affected task names

| Task name | Overlap rows |
| --- | ---: |
| `印色` | 25,258 |
| `<NULL>` | 4,101 |
| `UV(染)` | 2,660 |
| `印色+光水油(染)` | 1,983 |
| `印色+光水油(局部)` | 1,687 |
| `印色+啞水油(染)` | 1,374 |
| `印色+啞水油(局部)` | 944 |
| `印色+半光啞水油(染)` | 853 |
| `UV(局部)` | 731 |
| `印色+印刷啤` | 532 |

### Top affected material codes

The distribution is very long-tailed. The single largest bucket is the dominant-event null-context bucket:

- rows with null `task_name`: `4,101`
- rows with null `material_code`: `4,101`

The top non-null material codes only reach the low dozens, which means the blast radius is broad rather than concentrated in one product family.

### State distribution on overlap rows

| Machine state | Overlap rows |
| --- | ---: |
| `setup_changeover` | 27,810 |
| `production` | 15,606 |
| `planned_stop` | 28 |
| `unplanned_stop` | 9 |

This is strong evidence that the dominant-event rule collapses most mixed-overlap hours into setup or production and almost never leaves the final row in a stop-only state.

### Quantity presence on overlap rows

- overlap rows with non-null `good_qty` or `scrap_qty`: `31,681`
- overlap rows without any assigned qty: `11,772`

Monthly quantity presence:

| Month | Overlap rows | Rows with any qty |
| --- | ---: | ---: |
| 2025-01 | 4,894 | 3,836 |
| 2025-02 | 4,862 | 3,717 |
| 2025-03 | 7,863 | 5,470 |
| 2025-04 | 8,254 | 5,865 |
| 2025-05 | 8,816 | 6,560 |
| 2025-06 | 8,764 | 6,233 |

### Planned / unplanned stop presence on overlap rows

- rows with non-null `planned_stop_minutes`: `20,860`
- rows with non-null `unplanned_stop_minutes`: `19,023`
- rows with null `planned_stop_minutes`: `22,593`
- rows with null `unplanned_stop_minutes`: `24,430`

Monthly stop-minute presence:

| Month | Rows with planned stop minutes | Rows with unplanned stop minutes |
| --- | ---: | ---: |
| 2025-01 | 2,342 | 2,359 |
| 2025-02 | 2,293 | 2,216 |
| 2025-03 | 3,470 | 3,414 |
| 2025-04 | 3,884 | 3,684 |
| 2025-05 | 4,489 | 3,867 |
| 2025-06 | 4,382 | 3,483 |

### Idle observability on the active DB

- overlap rows with non-null `idle_minutes`: `0`

This does not mean idle is irrelevant. It means the active Jan-Jun backfill path currently does not persist the Python idle-audit flags on these rows. The live Python contract still explicitly skips multi-overlap rows for idle attribution.

## Real-Row Evidence Against “State Simplification Only”

### Sample A: clear mixed minute + quantity loss

For `024-147 @ 2025-05-29T21:00:00`, the active Gold row keeps only one dominant event:

- dominant event `J250018157`
  - total overlap `60.0`
  - setup `31.8`
  - production `12.5011`
  - planned stop `15.7623`
  - qty `6544`
- discarded non-dominant event `J250018158`
  - total overlap `35.0`
  - setup `25.0`
  - production `10.0`
  - qty `6485`

The live row currently stores:

- `machine_state = setup_changeover`
- only the dominant event’s minutes
- only the dominant event’s quantity allocation

That is not “state simplification only”. It is minute loss and quantity loss.

### Sample B: small but real extra stop + quantity evidence

For `035-017 @ 2025-06-15T20:00:00`:

- dominant event `J250019253`
  - total overlap `59.0167`
  - production `46.0`
  - unplanned stop `13.0`
  - qty `4918`
- discarded non-dominant event `J250019258`
  - total overlap `0.5`
  - production `0.3002`
  - planned stop `0.1209`
  - unplanned stop `0.0786`
  - qty `13711`

This is a small extra event, but it still proves the current rule can drop both stop detail and quantity-bearing evidence from the same hour.

### Sample C: dominant tie-break simplifies conflicting full-hour context

For `024-143 @ 2025-05-29T21:00:00`:

- event `J250018746`
  - total overlap `60.0`
  - production `60.0`
  - qty `15500`
- event `日保養`
  - total overlap `60.0`
  - production `60.0`
  - no qty

The row keeps only the lexically earlier dominant event and discards the other full-hour context. That is a pure dominant-rule simplification problem even before any blending implementation is considered.

## Decision

### What the current contract most likely causes

Based on the live code semantics plus the active DB evidence above, the current behavior most likely causes mixed effects:

1. state/context simplification
2. minute-attribution loss
3. quantity-attribution loss
4. idle suppression in the Python Gold contract

### Recommended next step

Split future work into two smaller tasks.

Reason:

- The blast radius is too large to justify calling the dominant-event rule “acceptable as-is”.
- A minute-only implementation is the correct first dependency because Task 3C6 quantity already follows the chosen minute basis.
- Folding minute blending and quantity blending into one immediate rewrite would widen scope unnecessarily and make validation harder.

So the recommended sequence is:

1. first follow-up: define and implement the narrowest acceptable multi-event minute contract
2. second follow-up: reassess quantity only after the minute contract is stable

That keeps Task 4O small, preserves honesty, and avoids silently widening into a broad Gold rewrite.

## Exact SQL Diagnostics Run

### 1. Jan-Jun overlap share

```sql
SELECT COUNT(*) AS jan_jun_rows,
       SUM(CASE WHEN multiple_csi_overlap_flag = 1 THEN 1 ELSE 0 END) AS overlap_rows,
       ROUND(100.0 * SUM(CASE WHEN multiple_csi_overlap_flag = 1 THEN 1 ELSE 0 END) / COUNT(*), 4) AS overlap_pct
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01';
```

### 2. Monthly overlap rows

```sql
SELECT substr(hour_ts,1,7) AS month, COUNT(*) AS overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1
GROUP BY 1
ORDER BY 1;
```

### 3. Monthly affected machine counts

```sql
SELECT month, COUNT(DISTINCT canonical_machine_id) AS affected_machines
FROM (
  SELECT substr(hour_ts,1,7) AS month, canonical_machine_id
  FROM fact_machine_hour
  WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
    AND multiple_csi_overlap_flag = 1
)
GROUP BY month
ORDER BY month;
```

### 4. Overall affected machines

```sql
SELECT COUNT(DISTINCT canonical_machine_id) AS affected_machines_overall
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1;
```

### 5. Top affected machines

```sql
SELECT canonical_machine_id, COUNT(*) AS overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1
GROUP BY canonical_machine_id
ORDER BY overlap_rows DESC, canonical_machine_id
LIMIT 15;
```

### 6. Top affected task names

```sql
SELECT COALESCE(task_name, '<NULL>') AS task_name, COUNT(*) AS overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1
GROUP BY COALESCE(task_name, '<NULL>')
ORDER BY overlap_rows DESC, task_name
LIMIT 15;
```

### 7. Top affected material buckets

```sql
SELECT COALESCE(material_code, '<NULL>') AS material_code, COUNT(*) AS overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1
GROUP BY COALESCE(material_code, '<NULL>')
ORDER BY overlap_rows DESC, material_code
LIMIT 15;
```

### 8. State distribution

```sql
SELECT COALESCE(machine_state, '<NULL>') AS machine_state, COUNT(*) AS overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1
GROUP BY COALESCE(machine_state, '<NULL>')
ORDER BY overlap_rows DESC, machine_state;
```

### 9. Quantity presence

```sql
SELECT SUM(CASE WHEN good_qty IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_good_qty,
       SUM(CASE WHEN scrap_qty IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_scrap_qty,
       SUM(CASE WHEN good_qty IS NOT NULL OR scrap_qty IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_any_qty,
       COUNT(*) AS overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1;
```

### 10. Monthly quantity / stop presence

```sql
SELECT substr(hour_ts,1,7) AS month,
       COUNT(*) AS overlap_rows,
       SUM(CASE WHEN good_qty IS NOT NULL OR scrap_qty IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_any_qty,
       SUM(CASE WHEN planned_stop_minutes IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_planned_stop_minutes,
       SUM(CASE WHEN unplanned_stop_minutes IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_unplanned_stop_minutes
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1
GROUP BY 1
ORDER BY 1;
```

### 11. Overall stop-minute presence

```sql
SELECT SUM(CASE WHEN planned_stop_minutes IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_planned_stop_minutes,
       SUM(CASE WHEN unplanned_stop_minutes IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_unplanned_stop_minutes,
       SUM(CASE WHEN planned_stop_minutes IS NULL THEN 1 ELSE 0 END) AS rows_with_null_planned_stop_minutes,
       SUM(CASE WHEN unplanned_stop_minutes IS NULL THEN 1 ELSE 0 END) AS rows_with_null_unplanned_stop_minutes,
       COUNT(*) AS overlap_rows
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1;
```

### 12. Null-context rows

```sql
SELECT SUM(CASE WHEN task_name IS NULL OR TRIM(task_name) = '' THEN 1 ELSE 0 END) AS rows_with_null_task_name,
       SUM(CASE WHEN material_code IS NULL OR TRIM(material_code) = '' THEN 1 ELSE 0 END) AS rows_with_null_material_code,
       SUM(CASE WHEN order_id IS NULL OR TRIM(order_id) = '' THEN 1 ELSE 0 END) AS rows_with_null_order_id
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1;
```

### 13. Idle presence on overlap rows

```sql
SELECT SUM(CASE WHEN idle_minutes IS NOT NULL THEN 1 ELSE 0 END) AS overlap_rows_with_idle_minutes
FROM fact_machine_hour
WHERE hour_ts >= '2025-01-01' AND hour_ts < '2025-07-01'
  AND multiple_csi_overlap_flag = 1;
```

### 14. Real-row overlap candidate inspection

Example row `024-147 @ 2025-05-29T21:00:00`:

```sql
WITH base AS (
    SELECT
        f.canonical_machine_id,
        f.hour_ts,
        julianday(f.hour_ts) AS hour_start_jd,
        julianday(datetime(f.hour_ts, '+1 hour')) AS hour_end_jd,
        c.source_row_hash,
        NULLIF(TRIM(c.order_id), '') AS order_id,
        NULLIF(TRIM(c.material_code), '') AS material_code,
        NULLIF(TRIM(c.task_name), '') AS task_name,
        c.good_qty AS event_good_qty,
        c.scrap_qty AS event_scrap_qty,
        c.actual_prod_minutes,
        c.planned_stop_minutes,
        c.unplanned_stop_minutes,
        c.actual_changeover_minutes,
        julianday(c.prod_start_ts) AS prod_start_jd,
        julianday(c.prep_end_ts) AS prep_end_jd,
        julianday(c.prod_end_ts) AS prod_end_jd
    FROM fact_machine_hour f
    JOIN csi_job_event c
      ON c.canonical_machine_id = f.canonical_machine_id
    WHERE f.canonical_machine_id = '024-147'
      AND f.hour_ts = '2025-05-29T21:00:00'
),
computed AS (... same overlap math as the live repair path ...),
scored AS (... same dominant-event minute math as the live repair path ...)
SELECT ...
FROM scored
WHERE (setup_overlap_minutes + production_overlap_minutes) > 0
ORDER BY total_overlap_minutes DESC, production_overlap_minutes DESC, source_row_hash;
```

The same pattern was run for:

- `035-017 @ 2025-06-15T20:00:00`
- `024-143 @ 2025-05-29T21:00:00`

## Validation

- No code changes were needed.
- No DB writes were performed.
- No artifact files were created or promoted.
- Validation was read-only:
  - repo preflight: `git status --short`, `git diff --stat`, `git diff`
  - required code/doc search via `rg`
  - direct code inspection of:
    - `core/gold_fact_builder.py`
    - `core/fact_machine_hour_repair.py`
    - `core/canonical_materializer.py`
    - `core/runtime_paths.py`
    - `tests/test_gold_fact_builder.py`
  - live SQLite diagnostics against `manufacturing_data.db`

## Files Changed

- `docs/technical/TASK4O_IMPLEMENTATION_REPORT.md`

## Remaining Uncertainty

- This audit proves the blast radius is material and mixed, but it does not yet define the exact acceptable minute-blending rule for sequential vs competing CSI events within one hour.
- Because the active Jan-Jun backfill path does not persist Python idle/source-flag audit markers, idle suppression is established from live code semantics rather than from row-level idle flags already stored in the DB.
- I did not implement or benchmark alternative blending algorithms in this task.
