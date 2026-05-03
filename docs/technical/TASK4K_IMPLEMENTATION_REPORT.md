# TASK4K Implementation Report

## Outcome

Task 4K passed.

Operationally meaningful ML inputs that were still trapped in adapter logic are now first-class canonical Gold columns on `fact_machine_hour`, populated in both fresh Gold builds and the SQL repair/backfill path. The active Jan-Jun Gold partitions were repaired in place on `manufacturing_data.db`, and the canonical ML reader/trainer now consume those explicit Gold columns first.

## Preflight Repo Check

### Live repo paths inspected before editing

- `CURRENT_REBUILD_STATUS.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `docs/technical/REBUILD_INTENT_AND_SYSTEM_SPEC.md`
- `docs/technical/v1_canonical_schema.md`
- `docs/technical/TASK4G_IMPLEMENTATION_REPORT.md`
- `docs/technical/TASK4I_IMPLEMENTATION_REPORT.md`
- `docs/technical/TASK4J_IMPLEMENTATION_REPORT.md`
- `/Users/rayfung/Documents/VCC/LeoPaper/TASK4K_INTERRUPTED_HANDOFF.md`
- `/Users/rayfung/Documents/VCC/LeoPaper/TASK4K_CONTINUATION_PROMPT.txt`
- `core/gold_fact_builder.py`
- `core/fact_machine_hour_repair.py`
- `core/canonical_materializer.py`
- `core/canonical_ml_reader.py`
- `core/ml_trainer.py`
- `core/ml_predictor.py`
- `modules/ml_module.py`
- `tests/test_gold_fact_builder.py`
- `tests/test_fact_machine_hour_repair.py`
- `tests/test_canonical_materializer.py`
- `tests/test_canonical_ml_reader.py`
- `tests/test_ml_trainer.py`
- `tests/test_ml_predictor.py`

### Live ledger confirmation

`CURRENT_REBUILD_STATUS.md` confirmed:

- `Task 4J passed`
- the current best next step was still to reduce remaining ML adapter dependence by promoting more inference/training inputs to first-class canonical Gold columns
- Task 4K had not yet been recorded as passed

### Git preflight

Commands run before editing:

```bash
git status --short
git diff --stat
```

Relevant live Task 4K target state before this run:

- tracked and already dirty:
  - `core/ml_predictor.py`
  - `core/ml_trainer.py`
  - `modules/ml_module.py`
- untracked canonical rebuild files already present in the live repo:
  - `core/gold_fact_builder.py`
  - `core/fact_machine_hour_repair.py`
  - `core/canonical_materializer.py`
  - `core/canonical_ml_reader.py`
  - Task 4K test files under `tests/`

Decision:

- continue the live repo state in place
- do not revert prior canonical rebuild work

Tracked diff evidence before this run:

```bash
git diff --stat -- core/ml_predictor.py core/ml_trainer.py modules/ml_module.py
```

Output:

```text
 core/ml_predictor.py |    7 +-
 core/ml_trainer.py   | 1689 ++++++++++++++++++++++++++++++++++++++++----------
 modules/ml_module.py | 1524 ++++++++++++++-------------------------------
 3 files changed, 1852 insertions(+), 1368 deletions(-)
```

## Exact Preflight Evidence

### Required grep evidence before implementation

Command:

```bash
rg -n "source_flags|adapter|default|cumulative_maintenance_count|maintenance_intensity_30d|last_maintenance_type|team_size|task_complexity" core/ml_trainer.py core/ml_predictor.py core/canonical_ml_reader.py -S
```

Key preflight matches:

```text
core/canonical_ml_reader.py:310:        source_flags = self._load_source_flags(row.get("source_flags"))
core/canonical_ml_reader.py:318:                team_size = self._float_or_none(defaults.get("team_size"))
core/canonical_ml_reader.py:334:        maintenance_intensity_30d = self._float_or_none(
core/canonical_ml_reader.py:340:        cumulative_maintenance_count = self._float_or_none(
core/ml_trainer.py:359:        source_flags = CanonicalMLReader._load_source_flags(row.get("source_flags"))
core/ml_trainer.py:368:                team_size = float(self.adapter_defaults.get("team_size", 3.0))
core/ml_trainer.py:392:        maintenance_intensity_30d = CanonicalMLReader._float_or_none(
core/ml_trainer.py:398:        cumulative_maintenance_count = CanonicalMLReader._float_or_none(
core/ml_trainer.py:413:        maintenance_in_hour = int(bool(source_flags.get("maintenance_txn_in_hour")))
```

Command:

```bash
rg -n "maintenance_txn_in_hour|has_maintenance_history|maintenance_distinct_work_order_count_7d|maintenance_distinct_work_order_count_30d|maintenance_distinct_work_order_in_hour_count|last_maintenance_work_order_type|hours_since_last_maintenance|days_since_last_maintenance|team_size|manpower" core/gold_fact_builder.py core/fact_machine_hour_repair.py -S
```

Key preflight matches:

```text
core/gold_fact_builder.py:75:                team_size REAL,
core/gold_fact_builder.py:76:                manpower REAL,
core/gold_fact_builder.py:1457:            "has_maintenance_history": bool(history_events),
core/gold_fact_builder.py:1458:            "maintenance_txn_in_hour": bool(current_hour_events),
core/gold_fact_builder.py:1459:            "maintenance_distinct_work_order_count_30d": cls._count_distinct_work_orders(last_30d_events),
core/gold_fact_builder.py:1460:            "maintenance_distinct_work_order_count_7d": cls._count_distinct_work_orders(last_7d_events),
core/gold_fact_builder.py:1461:            "maintenance_distinct_work_order_in_hour_count": cls._count_distinct_work_orders(current_hour_events),
core/fact_machine_hour_repair.py:121:                last_maintenance_work_order_type = NULL,
core/fact_machine_hour_repair.py:122:                manpower = NULL,
core/fact_machine_hour_repair.py:123:                hours_since_last_maintenance = NULL,
core/fact_machine_hour_repair.py:124:                days_since_last_maintenance = NULL,
```

### Active DB coverage before implementation

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS total_rows,
    COUNT(team_size) AS team_size_nonnull,
    COUNT(manpower) AS manpower_nonnull,
    COUNT(CASE WHEN last_maintenance_work_order_type IS NOT NULL AND trim(last_maintenance_work_order_type) <> '' THEN 1 END) AS last_maintenance_type_nonblank,
    COUNT(hours_since_last_maintenance) AS hours_since_nonnull,
    COUNT(days_since_last_maintenance) AS days_since_nonnull
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
GROUP BY 1
ORDER BY 1;
```

Output before this run:

```text
month    total_rows  team_size_nonnull  manpower_nonnull  last_maintenance_type_nonblank  hours_since_nonnull  days_since_nonnull
2025-01  64725       0                  26432             15556                           15556                15556
2025-02  58461       0                  28413             28273                           28273                28273
2025-03  64725       0                  41892             45204                           45204                45204
2025-04  62637       0                  41251             50966                           50966                50966
2025-05  65165       0                  43179             57064                           57064                57064
2025-06  62639       0                  44044             56178                           56178                56178
```

### Exact evidence that maintenance-count flags were absent from `source_flags`

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS total_rows,
    COUNT(CASE WHEN json_extract(source_flags, '$.has_maintenance_history') IS NOT NULL THEN 1 END) AS has_history_key_rows,
    COUNT(CASE WHEN json_extract(source_flags, '$.maintenance_txn_in_hour') IS NOT NULL THEN 1 END) AS maintenance_in_hour_key_rows,
    COUNT(CASE WHEN json_extract(source_flags, '$.maintenance_distinct_work_order_count_7d') IS NOT NULL THEN 1 END) AS count_7d_key_rows,
    COUNT(CASE WHEN json_extract(source_flags, '$.maintenance_distinct_work_order_count_30d') IS NOT NULL THEN 1 END) AS count_30d_key_rows,
    COUNT(CASE WHEN json_extract(source_flags, '$.maintenance_distinct_work_order_in_hour_count') IS NOT NULL THEN 1 END) AS in_hour_count_key_rows
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
GROUP BY 1
ORDER BY 1;
```

Output before this run:

```text
month    total_rows  has_history_key_rows  maintenance_in_hour_key_rows  count_7d_key_rows  count_30d_key_rows  in_hour_count_key_rows
2025-01  64725       0                     0                             0                  0                   0
2025-02  58461       0                     0                             0                  0                   0
2025-03  64725       0                     0                             0                  0                   0
2025-04  62637       0                     0                             0                  0                   0
2025-05  65165       0                     0                             0                  0                   0
2025-06  62639       0                     0                             0                  0                   0
```

## Promoted Gold Columns

Task 4K promoted these operationally meaningful fields into first-class canonical Gold columns:

- `team_size`
- `has_maintenance_history`
- `maintenance_txn_in_hour`
- `maintenance_distinct_work_order_count_7d`
- `maintenance_distinct_work_order_count_30d`
- `maintenance_distinct_work_order_in_hour_count`
- `cumulative_maintenance_count`

Definition notes:

- `team_size` = rounded positive MES `manpower`; non-positive manpower stays null
- `cumulative_maintenance_count` = distinct maintenance work orders observed strictly before the machine-hour within loaded canonical maintenance history

Fields intentionally not promoted:

- `task_complexity`
- `machine_type_encoded`
- `maintenance_urgency`
- `needs_maintenance`
- label encodings and other model-engineered variables

## What Changed

### Gold / repair layer

- `core/gold_fact_builder.py`
  - added the promoted columns to `fact_machine_hour`
  - populates `team_size` from MES `manpower`
  - populates explicit maintenance history/count fields during fresh Gold builds
  - keeps the internal maintenance-state / idle logic compatible with the promoted columns
- `core/fact_machine_hour_repair.py`
  - ensures the promoted columns exist on existing active DBs
  - populates `team_size` during SQL MES repair
  - computes maintenance-history/count columns for every repaired row on the active Gold table

### Canonical ML path

- `core/canonical_ml_reader.py`
  - now reads promoted maintenance/count columns directly from Gold
  - no longer parses promoted maintenance fields from `source_flags`
  - no longer sources `cumulative_maintenance_count` from the saved preprocessor defaults
- `core/ml_trainer.py`
  - now reads `maintenance_txn_in_hour`, `maintenance_distinct_work_order_count_30d`, `cumulative_maintenance_count`, and `last_maintenance_work_order_type` directly from Gold
  - keeps `source_flags` only as diagnostic payload in the training dataframe
  - no longer uses preprocessor defaults for `cumulative_maintenance_count`
- `modules/ml_module.py`
  - updated the user-facing canonical ML contract notes to reflect the new Gold columns

### Supporting tests / docs

- updated focused Gold, repair, materializer, canonical ML reader, and trainer tests
- updated:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/REBUILD_DOCS_INDEX.md`
  - `docs/technical/v1_canonical_schema.md`

`core/canonical_materializer.py` was inspected but did not require a code change because its fresh-build path already delegates to the live Gold builder and its backfill path already delegates to the SQL repair path, both of which now honor the promoted columns.

## Active DB Execution

### Safety backup

- active DB before Task 4K repair:
  - `manufacturing_data.db`
- safety copy created:
  - `artifacts/db_snapshots/manufacturing_data.task4k_active_backup_20260331_190430.db`

### Active repair command

```bash
python3 - <<'PY'
import json
from core.gold_fact_builder import GoldFactBuilder
from core.fact_machine_hour_repair import repair_fact_machine_hour_operational_overlays

db_path = 'manufacturing_data.db'
GoldFactBuilder(db_path)
result = repair_fact_machine_hour_operational_overlays(db_path)
print(json.dumps(result, ensure_ascii=False, indent=2))
PY
```

Repair result:

```json
{
  "before": {
    "fact_rows": 378352,
    "rows_with_team_size": 0,
    "rows_with_maintenance_history": 0,
    "rows_with_maintenance_txn_in_hour": 0,
    "rows_with_maintenance_count_30d": 0,
    "rows_with_cumulative_maintenance_count": 0
  },
  "after": {
    "fact_rows": 378352,
    "rows_with_team_size": 224529,
    "rows_with_maintenance_history": 253241,
    "rows_with_maintenance_txn_in_hour": 550,
    "rows_with_maintenance_count_30d": 172517,
    "rows_with_cumulative_maintenance_count": 253241
  },
  "maintenance_metrics_rows": 378352
}
```

### Schema proof after the active repair

Command:

```sql
PRAGMA table_info(fact_machine_hour);
```

New Gold columns present on the active DB:

- `team_size`
- `has_maintenance_history`
- `maintenance_txn_in_hour`
- `maintenance_distinct_work_order_count_7d`
- `maintenance_distinct_work_order_count_30d`
- `maintenance_distinct_work_order_in_hour_count`
- `cumulative_maintenance_count`

## Jan-Jun Coverage Proof For Each Promoted Column

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS total_rows,
    COUNT(team_size) AS team_size_nonnull,
    ROUND(AVG(team_size), 3) AS team_size_avg,
    MIN(team_size) AS team_size_min,
    MAX(team_size) AS team_size_max,
    COUNT(has_maintenance_history) AS has_history_nonnull,
    SUM(CASE WHEN has_maintenance_history = 1 THEN 1 ELSE 0 END) AS has_history_true_rows,
    COUNT(maintenance_txn_in_hour) AS maintenance_in_hour_nonnull,
    SUM(CASE WHEN maintenance_txn_in_hour = 1 THEN 1 ELSE 0 END) AS maintenance_in_hour_true_rows,
    COUNT(maintenance_distinct_work_order_count_7d) AS count_7d_nonnull,
    SUM(CASE WHEN maintenance_distinct_work_order_count_7d > 0 THEN 1 ELSE 0 END) AS count_7d_positive_rows,
    ROUND(AVG(maintenance_distinct_work_order_count_7d), 3) AS count_7d_avg,
    MAX(maintenance_distinct_work_order_count_7d) AS count_7d_max,
    COUNT(maintenance_distinct_work_order_count_30d) AS count_30d_nonnull,
    SUM(CASE WHEN maintenance_distinct_work_order_count_30d > 0 THEN 1 ELSE 0 END) AS count_30d_positive_rows,
    ROUND(AVG(maintenance_distinct_work_order_count_30d), 3) AS count_30d_avg,
    MAX(maintenance_distinct_work_order_count_30d) AS count_30d_max,
    COUNT(maintenance_distinct_work_order_in_hour_count) AS in_hour_count_nonnull,
    SUM(CASE WHEN maintenance_distinct_work_order_in_hour_count > 0 THEN 1 ELSE 0 END) AS in_hour_count_positive_rows,
    ROUND(AVG(maintenance_distinct_work_order_in_hour_count), 3) AS in_hour_count_avg,
    MAX(maintenance_distinct_work_order_in_hour_count) AS in_hour_count_max,
    COUNT(cumulative_maintenance_count) AS cumulative_nonnull,
    SUM(CASE WHEN cumulative_maintenance_count > 0 THEN 1 ELSE 0 END) AS cumulative_positive_rows,
    ROUND(AVG(cumulative_maintenance_count), 3) AS cumulative_avg,
    MAX(cumulative_maintenance_count) AS cumulative_max
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
GROUP BY 1
ORDER BY 1;
```

Output:

```text
month    total_rows  team_size_nonnull  team_size_avg  team_size_min  team_size_max  has_history_nonnull  has_history_true_rows  maintenance_in_hour_nonnull  maintenance_in_hour_true_rows  count_7d_nonnull  count_7d_positive_rows  count_7d_avg  count_7d_max  count_30d_nonnull  count_30d_positive_rows  count_30d_avg  count_30d_max  in_hour_count_nonnull  in_hour_count_positive_rows  in_hour_count_avg  in_hour_count_max  cumulative_nonnull  cumulative_positive_rows  cumulative_avg  cumulative_max
2025-01  64725       26325              2.513          1.0            5.0            64725                15556                  64725                        100                            64725             8791                    0.180         4             64725              15556                    0.390          5              64725                  100                          0.002              2                  64725               15556                     0.390           5
2025-02  58461       28357              2.533          1.0            5.0            58461                28273                  58461                        95                             58461             8706                    0.167         3             58461              22056                    0.553          5              58461                  95                           0.002              2                  58461               28273                     0.873           5
2025-03  64725       41692              2.536          1.0            4.0            64725                45204                  64725                        100                            64725             13010                   0.233         3             64725              33564                    0.839          7              64725                  100                          0.002              2                  64725               45204                     1.612           7
2025-04  62637       41138              2.492          1.0            4.0            62637                50966                  62637                        79                             62637             11531                   0.208         3             62637              32481                    0.806          5              62637                  79                           0.001              2                  62637               50966                     2.334           8
2025-05  65165       43069              2.521          1.0            7.0            65165                57064                  65165                        92                             65165             12481                   0.221         3             65165              34259                    0.851          6              65165                  92                           0.001              2                  65165               57064                     3.130           10
2025-06  62639       43948              2.533          1.0            4.0            62639                56178                  62639                        84                             62639             11895                   0.227         4             62639              34601                    0.929          6              62639                  84                           0.001              2                  62639               56178                     3.976           12
```

Interpretation:

- `team_size` is now populated wherever MES `manpower` was present and positive
- all promoted maintenance-history/count columns now exist on every Jan-Jun row
- `has_maintenance_history`, `maintenance_txn_in_hour`, and the count columns now carry meaningful non-zero coverage rather than adapter-only or absent values
- `cumulative_maintenance_count` now grows month by month as expected

## Source Flags After Task 4K

The promoted maintenance keys remain absent from `source_flags` on the active Jan-Jun Gold rows after the repair:

```text
month    total_rows  has_history_key_rows  maintenance_in_hour_key_rows  count_7d_key_rows  count_30d_key_rows  in_hour_count_key_rows
2025-01  64725       0                     0                             0                  0                   0
2025-02  58461       0                     0                             0                  0                   0
2025-03  64725       0                     0                             0                  0                   0
2025-04  62637       0                     0                             0                  0                   0
2025-05  65165       0                     0                             0                  0                   0
2025-06  62639       0                     0                             0                  0                   0
```

That is now acceptable because the canonical ML reader/trainer no longer depend on those promoted inputs being present in `source_flags`.

## Trainer-Side Smoke

Targeted smoke using a real active Gold row and the real `MLDataPreparer.load_data()` path on a tiny temp DB seeded from that active row:

```json
{
  "fact_row": {
    "canonical_machine_id": "024-063",
    "hour_ts": "2025-01-02T13:00:00",
    "team_size": 2.0,
    "maintenance_txn_in_hour": 0,
    "maintenance_distinct_work_order_count_30d": 2,
    "cumulative_maintenance_count": 2,
    "last_maintenance_work_order_type": "CM"
  },
  "training_row": {
    "machine_id": "024-063",
    "hour_ts": "2025-01-02T13:00:00",
    "team_size": 2.0,
    "maintenance_in_hour": 0,
    "maintenance_intensity_30d": 2.0,
    "cumulative_maintenance_count": 2.0,
    "last_maintenance_type": "CM",
    "adapter_notes": ""
  }
}
```

This proves the promoted Gold fields now flow directly into the trainer-side preparation path without needing `source_flags` parsing or a default-only fallback.

## Adapter Dependence Summary

### Removed / reduced adapter-derived fields

- `team_size`
  - before: explicit Gold column existed but active Jan-Jun coverage was zero, so ML logic regularly fell back to `manpower` or a saved preprocessor default
  - after: fresh builds and SQL repair populate `team_size` directly from MES/manpower
- `last_maintenance_type`
  - before: reader/trainer fell back to `source_flags.maintenance_last_work_order_type`
  - after: reader/trainer use explicit `last_maintenance_work_order_type`
- `maintenance_intensity_30d`
  - before: reader/trainer read `source_flags.maintenance_distinct_work_order_count_30d`
  - after: reader/trainer use explicit `maintenance_distinct_work_order_count_30d`
- `cumulative_maintenance_count`
  - before: reader/trainer used a preprocessor default or proxy path
  - after: reader/trainer use explicit `cumulative_maintenance_count`
- `maintenance_in_hour`
  - before: trainer read `source_flags.maintenance_txn_in_hour`
  - after: trainer uses explicit `maintenance_txn_in_hour`

### Adapter-derived fields intentionally remaining

- `task_difficulty`
  - still derived from `task_name`
  - remains outside Gold because it is a model-facing interpretation, not a canonical source fact
- `team_size` last-resort fallback
  - reader/trainer still allow `team_size <- rounded manpower <- preprocessor default`
  - this only applies when the row still lacks both explicit `team_size` and explicit `manpower`
- predictor direct-call defaults
  - `core/ml_predictor.py` still has generic optional-parameter defaults for non-canonical callers
  - canonical reader/trainer paths now supply the promoted fields explicitly

## Changed Files And Reasons

- `core/gold_fact_builder.py`
  - add promoted Gold columns and populate them during fresh builds
- `core/fact_machine_hour_repair.py`
  - populate promoted Gold columns during SQL repair/backfill on existing active DBs
- `core/canonical_ml_reader.py`
  - consume explicit Gold maintenance/team fields first
- `core/ml_trainer.py`
  - consume explicit Gold maintenance/team fields first
- `modules/ml_module.py`
  - update canonical ML contract notes shown in the app
- `tests/test_gold_fact_builder.py`
  - prove fresh Gold overlays populate/preserve promoted columns
- `tests/test_fact_machine_hour_repair.py`
  - prove repair/backfill populates promoted columns
- `tests/test_canonical_materializer.py`
  - prove backfill path writes promoted columns on the repaired month
- `tests/test_canonical_ml_reader.py`
  - prove reader uses explicit Gold maintenance columns first
- `tests/test_ml_trainer.py`
  - prove trainer uses explicit Gold maintenance columns first
- `CURRENT_REBUILD_STATUS.md`
  - record Task 4K as passed and narrow the remaining ML adapter gaps
- `docs/technical/REBUILD_DOCS_INDEX.md`
  - index this report
- `docs/technical/v1_canonical_schema.md`
  - record the new Gold columns

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile \
  core/gold_fact_builder.py \
  core/fact_machine_hour_repair.py \
  core/canonical_ml_reader.py \
  core/ml_trainer.py \
  modules/ml_module.py \
  tests/test_gold_fact_builder.py \
  tests/test_fact_machine_hour_repair.py \
  tests/test_canonical_materializer.py \
  tests/test_canonical_ml_reader.py \
  tests/test_ml_trainer.py \
  tests/test_ml_module.py \
  tests/test_ml_predictor.py

python3 -m unittest \
  tests.test_gold_fact_builder \
  tests.test_fact_machine_hour_repair \
  tests.test_canonical_materializer \
  tests.test_canonical_ml_reader \
  tests.test_ml_trainer \
  tests.test_ml_module \
  tests.test_ml_predictor
```

Results:

- compile check: passed
- focused regressions: `Ran 92 tests in 1.556s` and `OK`
- active DB repair/backfill: completed successfully on `manufacturing_data.db`

## Status Delta

- Task 4K passed.
- Operationally meaningful ML maintenance-history/count inputs and `team_size` are now first-class canonical Gold columns.
- Jan-Jun active Gold coverage was repaired in place to populate those columns.
- Canonical ML reader and retraining no longer depend on `source_flags` or preprocessor-default-only logic for the promoted fields.
