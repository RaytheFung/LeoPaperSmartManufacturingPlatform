# TASK4I Implementation Report

## Outcome

Task 4I passed.

Formal historical backfill is no longer just scaffolding. February 2025 now exists in canonical Gold on the active runtime DB, and the active rerun preserved the same row count and overlay coverage on a second pass.

## What changed

- `core/canonical_materializer.py`
  Historical month materialization now completes Gold by writing the canonical energy backbone for the target month and then invoking the SQL overlay repair path on the shared DB.
- `core/gold_fact_builder.py`
  The Gold builder now has lower-overhead machine-ordered CSI batching and dict-safe `source_flags` handling for in-memory overlay work.
- `tests/test_canonical_materializer.py`
  Historical backfill coverage now asserts the repaired full-overlay execution path instead of the old `energy_backbone_only` behavior.

## Exact blocker and fix

Task 4I had stalled in two separate ways:

1. The formal historical runner still called `materialize_backfill_month(...)` with `gold_materialization_mode = energy_backbone_only`.
2. The attempted Python full-overlay rewrite was too slow on real February data to be a practical recovery path.

The final fix was to keep the month-scoped historical runner but change its Gold completion strategy:

- write the month-scoped canonical energy backbone first
- immediately run `repair_fact_machine_hour_operational_overlays(...)`
- read the repaired month back from `fact_machine_hour` as the completed historical Gold result

This uses the already-proven SQL overlay reconstruction path against populated canonical Silver tables and avoids depending on legacy `unified_view`.

## Live DB proof

Active DB:
- `manufacturing_data.db`

Safety backup before the active repair pass:
- `artifacts/db_snapshots/manufacturing_data.task4j_active_backup_20260331_052357.db`

### Before active repair

February 2025 existed only as a partial Gold backbone:

- `fact_machine_hour` rows: `58,461`
- non-null `good_qty`: `0`
- non-null `team_leader`: `0`
- non-null `manpower`: `0`
- non-null `hours_since_last_maintenance`: `0`

### After active repair

February 2025 on the active DB now has:

- `fact_machine_hour` rows: `58,461`
- distinct machines: `87`
- non-null `good_qty`: `23,692`
- positive `good_qty`: `23,606`
- non-null `team_leader`: `31,640`
- non-null `manpower`: `28,413`
- non-null `hours_since_last_maintenance`: `28,273`
- non-null `order_id`: `31,936`
- non-null `material_code`: `29,503`
- non-null `csi_source_row_hash`: `31,936`
- non-null `mes_source_row_hash`: `28,413`

Representative repaired active rows:

- `024-003 @ 2025-02-06T00:00:00`: `production`, `J240042866`, `good_qty 553.363173067222`, `team_leader 李華`, `manpower 2.0`
- `024-003 @ 2025-02-10T18:00:00`: `setup_changeover`, `J240045171`, `good_qty 1185.0`, `team_leader 任建樂`, `manpower 2.0`, `hours_since_last_maintenance 2.38023416697979`, `last_maintenance_work_order_type AM`

## Working-copy proof

Fresh working-copy DB:
- `artifacts/db_snapshots/manufacturing_data.task4j_working_20260331_051935.db`

The same February month was proven on the working copy before the active rerun. Its repaired February coverage matches the active pass:

- rows: `58,461`
- non-null `good_qty`: `23,692`
- non-null `team_leader`: `31,640`
- non-null `manpower`: `28,413`
- non-null `hours_since_last_maintenance`: `28,273`

## Idempotence

The active DB was rerun a second time after the first repaired pass.

The February 2025 partition remained unchanged on the metrics that matter:

- rows: `58,461`
- non-null `good_qty`: `23,692`
- positive `good_qty`: `23,606`
- non-null `team_leader`: `31,640`
- non-null `manpower`: `28,413`
- non-null `hours_since_last_maintenance`: `28,273`

No duplication occurred, and the live month still reads as exactly one canonical row per `canonical_machine_id x hour_ts`.

## Canonical reader proof

`CanonicalGoldReader` now reports:

- available months: `['February 2025', 'January 2025']`
- February page rows: `58,461`
- February distinct machines: `87`

Sample reader output:

- `1262-10015 @ 2025-02-03T11:00:00`: `setup_changeover`, `J240045667`, `good_qty 615.0`, `team_leader 李振華`, `manpower 1.0`
- `024-057 @ 2025-02-03T13:00:00`: `setup_changeover`, `J240042579`, `good_qty 1260.0`, `team_leader 張剛`, `manpower 1.0`
- `024-071 @ 2025-02-03T13:00:00`: `setup_changeover`, `J250001000`, `good_qty 731.0`, `team_leader 關志敏`, `manpower 2.0`

## Validation

Commands run:

- `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/canonical_materializer.py core/fact_machine_hour_repair.py tests/test_canonical_materializer.py tests/test_fact_machine_hour_repair.py`
- `python3 -m unittest tests.test_canonical_materializer tests.test_fact_machine_hour_repair tests.test_canonical_gold_reader`

Result:

- `Ran 17 tests ... OK`

## Remaining limitations

- Historical backfill still runs synchronously and month-by-month.
- The SQL repair helper rebuilds operational overlays across the current Gold table, not only the target month.
- `maintenance_minutes` remains intentionally unclaimed.
- Multi-event CSI blending and MES quantity fallback remain out of scope.

## Status delta

- Task 4I passed.
- Formal historical backfill into canonical Silver + Gold is now proven on a real historical month in the active runtime DB.
- February 2025 is now a live canonical month alongside January 2025.
