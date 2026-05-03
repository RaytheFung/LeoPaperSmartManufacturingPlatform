# TASK4M Implementation Report

## Outcome

Task 4M passed.

The next ML-adapter cleanup milestone was completed without redoing Task 4L retraining. Canonical ML no longer defaults unmapped `task_name` rows to `Medium`, the Jan-Jun finishing-only task families are now mapped explicitly, and direct predictor calls no longer fabricate literal placeholder machine/team/material values before feature preparation.

## Preflight Repo Check

### Live repo paths inspected before editing

- `AGENTS.md`
- `CURRENT_REBUILD_STATUS.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `docs/technical/REBUILD_INTENT_AND_SYSTEM_SPEC.md`
- `docs/technical/v1_canonical_schema.md`
- `docs/technical/TASK4L_IMPLEMENTATION_REPORT.md`
- `core/canonical_ml_reader.py`
- `core/ml_predictor.py`
- `core/ml_trainer.py`
- `modules/ml_module.py`
- `tests/test_canonical_ml_reader.py`
- `tests/test_ml_predictor.py`
- `tests/test_ml_trainer.py`
- `tests/test_ml_module.py`

### Live ledger confirmation

`CURRENT_REBUILD_STATUS.md` confirmed:

- `Task 4L passed`
- the current best next step was still the narrow ML-adapter cleanup around `task_difficulty`, exceptional missing-crew fallback, and generic direct-call predictor defaults
- the active artifact bundle was still the Task 4L Jan-Jun reevaluation result

### Git preflight

Commands run before editing:

```bash
git status --short
git diff --stat
git diff
```

Decision:

- continue the live rebuild state in place
- do not revert unrelated existing diffs
- keep this milestone code-and-doc only unless validation proved a live retrain was necessary

## Exact Diagnostics That Drove Scope

### Pre-change task-difficulty fallback dependence on the active DB

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS ml_base_rows,
    SUM(CASE WHEN derive_task_difficulty(task_name) IS NULL THEN 1 ELSE 0 END) AS unmapped_task_rows,
    COUNT(DISTINCT CASE WHEN derive_task_difficulty(task_name) IS NULL THEN canonical_machine_id END) AS machines_with_unmapped_tasks
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
  AND good_qty > 0
  AND energy_total_kwh > 0
  AND hours_since_last_maintenance IS NOT NULL
GROUP BY 1
ORDER BY 1;
```

Pre-change output:

```text
2025-01|3945|102|3
2025-02|12577|1130|7
2025-03|24328|1836|10
2025-04|27449|2698|14
2025-05|32117|2711|15
2025-06|32883|2194|14
```

Dominant unmapped task families before Task 4M:

```text
UV(染)|6521
UV(局部)|2043
啞水油(染)|876
特別水油(染)|565
啞水油(局部)|204
特別水油(局部)|158
仿啤牌油|130
啞UV(染)|121
```

### Candidate-level impact before Task 4M

Command:

```sql
WITH base AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY substr(hour_ts,1,7), canonical_machine_id
               ORDER BY hour_ts DESC
           ) AS rn
    FROM fact_machine_hour
    WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
      AND good_qty > 0
      AND energy_total_kwh > 0
      AND hours_since_last_maintenance IS NOT NULL
), latest AS (
    SELECT * FROM base WHERE rn = 1
)
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS candidate_rows,
    SUM(CASE WHEN derive_task_difficulty(task_name) IS NULL THEN 1 ELSE 0 END) AS candidate_unmapped_task_rows
FROM latest
GROUP BY 1
ORDER BY 1;
```

Pre-change output:

```text
2025-01|24|2
2025-02|52|4
2025-03|62|5
2025-04|70|7
2025-05|76|7
2025-06|75|5
```

### Missing-crew fallback blast radius that was intentionally not removed in this milestone

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS ml_base_rows,
    SUM(CASE WHEN ((team_size IS NULL OR team_size <= 0) AND (manpower IS NULL OR manpower <= 0)) THEN 1 ELSE 0 END) AS rows_requiring_team_fallback,
    COUNT(DISTINCT CASE WHEN ((team_size IS NULL OR team_size <= 0) AND (manpower IS NULL OR manpower <= 0)) THEN canonical_machine_id END) AS machines_requiring_team_fallback
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
  AND good_qty > 0
  AND energy_total_kwh > 0
  AND hours_since_last_maintenance IS NOT NULL
GROUP BY 1
ORDER BY 1;
```

Output:

```text
2025-01|3945|157|17
2025-02|12577|442|39
2025-03|24328|906|58
2025-04|27449|1077|65
2025-05|32117|1157|73
2025-06|32883|1099|70
```

Decision:

- remove the `Medium` fallback only after expanding real task-family coverage
- do not remove the final `team_size` fallback in the same run because the active DB still depends on it heavily

## What Changed

- `core/canonical_ml_reader.py`
  - expanded `_derive_task_difficulty(...)` to classify the observed finishing-only families (`UV`, `水油`, `啞油`, `特別UV`, `GP-LED...`, related oil/coating labels) as `Easy` when no print keyword is present
  - removed the canonical `Medium` default for unmapped task names
  - rows that still cannot be mapped are now blocked honestly with `blocked_reason = unmapped_task_name`
- `core/ml_trainer.py`
  - mirrored the same no-default task-difficulty rule in canonical training preparation
  - retained the existing exceptional `team_size` fallback path unchanged
- `core/ml_predictor.py`
  - stopped fabricating literal placeholder categorical inputs like `024-001`, `Default`, and `DEFAULT`
  - direct predictor entry points now normalize missing categories to `unknown`
  - missing optional numeric inputs now use learned feature defaults rather than hard-coded generic values where possible
  - missing direct-call task difficulty now falls back to the learned `task_complexity` default instead of an implicit literal label
- `modules/ml_module.py`
  - updated the ML contract notes to describe the new task-family mapping and the still-open crew fallback honestly
- `tests/test_canonical_ml_reader.py`
  - added coverage for `UV(染)` mapping and unmapped-task blocking
- `tests/test_ml_trainer.py`
  - added coverage proving canonical training now blocks unmapped task names instead of defaulting them to `Medium`
- `tests/test_ml_predictor.py`
  - added coverage proving direct predictor feature preparation uses `unknown` categorical buckets and learned defaults for missing direct-call inputs

## Post-Change Live Diagnostics

### Jan-Jun unmapped task rows after Task 4M

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS ml_base_rows,
    SUM(CASE WHEN derive_task_difficulty(task_name) IS NULL THEN 1 ELSE 0 END) AS unmapped_task_rows,
    COUNT(DISTINCT CASE WHEN derive_task_difficulty(task_name) IS NULL THEN canonical_machine_id END) AS machines_with_unmapped_tasks
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
  AND good_qty > 0
  AND energy_total_kwh > 0
  AND hours_since_last_maintenance IS NOT NULL
GROUP BY 1
ORDER BY 1;
```

Post-change output:

```text
2025-01|3945|0|0
2025-02|12577|0|0
2025-03|24328|0|0
2025-04|27449|0|0
2025-05|32117|0|0
2025-06|32883|0|0
```

### Candidate-level task-label coverage after Task 4M

```text
2025-01|24|0
2025-02|52|0
2025-03|62|0
2025-04|70|0
2025-05|76|0
2025-06|75|0
```

## Live DB / Artifact Impact

Task 4M did not run live retraining and did not mutate the active DB contents deliberately.

Verified active state after this run:

- latest `ml_models` row remains `production_efficiency_20260401_0020 | random_forest | 0.8065397899688995 | 0.012031498601255491`
- `models/production_efficiency_model.provenance.json` still reports:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
  - `artifact_state = active`
- `models/production_preprocessor.provenance.json` remains aligned to the same Task 4L active bundle

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/canonical_ml_reader.py core/ml_predictor.py core/ml_trainer.py modules/ml_module.py tests/test_canonical_ml_reader.py tests/test_ml_predictor.py tests/test_ml_trainer.py tests/test_ml_module.py
python3 -m unittest tests.test_canonical_ml_reader tests.test_ml_predictor tests.test_ml_trainer tests.test_ml_module
```

Results:

- compile checks passed
- focused canonical ML regression suite: `Ran 23 tests ... OK`

## Remaining Limitations

- canonical ML still keeps the last-resort `team_size` fallback when both canonical `team_size` and canonical `manpower` are missing
- retraining remains synchronous and user-triggered
- historical backfill remains synchronous and month-by-month
- other previously accepted non-ML rebuild limitations remain unchanged

## Pass Status

Task 4M should be considered passed.

This milestone removed the remaining canonical `task_difficulty` default safely, eliminated the real Jan-Jun unmapped task families from the active ML path, and reduced direct predictor default fabrication without reopening Task 4L retraining or changing the active artifact bundle.
