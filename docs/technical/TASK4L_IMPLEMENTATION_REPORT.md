# TASK4L Implementation Report

## Outcome

Task 4L passed.

Canonical ML retraining is now reevaluated on the real January through June 2025 Gold span with a time-aware multi-month holdout. The active model and preprocessor were refreshed only after the new Task 4L candidate outperformed the current active Task 4G bundle on the same May-June holdout and passed the existing artifact gate.

## Preflight Repo Check

### Live repo paths inspected before editing

- `CURRENT_REBUILD_STATUS.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `docs/technical/REBUILD_INTENT_AND_SYSTEM_SPEC.md`
- `docs/technical/v1_canonical_schema.md`
- `docs/technical/TASK4G_IMPLEMENTATION_REPORT.md`
- `docs/technical/TASK4I_IMPLEMENTATION_REPORT.md`
- `docs/technical/TASK4J_IMPLEMENTATION_REPORT.md`
- `docs/technical/TASK4K_IMPLEMENTATION_REPORT.md`
- `AGENTS.md`
- `core/canonical_ml_reader.py`
- `core/ml_trainer.py`
- `core/ml_predictor.py`
- `core/runtime_paths.py`
- `modules/ml_module.py`
- `tests/test_canonical_ml_reader.py`
- `tests/test_ml_trainer.py`
- `tests/test_ml_predictor.py`
- `tests/test_ml_module.py`
- active artifact files under `models/`
- the user-provided continuation artifacts:
  - `Terminal Reply for Task4K.rtf`
  - `Prompt for Task4L.txt`
  - `CODEX_REPLY_FORMAT_ADDENDUM.txt`

### Live ledger confirmation

`CURRENT_REBUILD_STATUS.md` confirmed:

- `Task 4K passed`
- Jan-Jun canonical Gold was the active baseline
- Task 4L had not yet been recorded as passed

### Active runtime paths

- active DB: `manufacturing_data.db`
- active model before Task 4L promotion: `models/production_efficiency_model.pkl`
- active preprocessor before Task 4L promotion: `models/production_preprocessor.pkl`

### Preflight grep evidence

Command:

```bash
rg -n "random_forest|xgboost|linear_regression|train_test_split|TimeSeries|time|month" core/ml_trainer.py -S
```

Key pre-change matches:

```text
18:from sklearn.model_selection import train_test_split
57:    "month",
117:    "month_coverage",
158:        self.last_month_coverage: list[str] = []
206:        self.last_month_coverage = self._derive_month_coverage(filtered_df)
231:        df["datetime"] = pd.to_datetime(df["datetime"])
234:        df["month"] = df["datetime"].dt.month
496:        self.models["linear_regression"] = lr_model
518:        self.models["random_forest"] = rf_model
543:            self.models["xgboost"] = xgb_model
676:    X_train, X_test, y_train, y_test = train_test_split(
```

Command:

```bash
rg -n "training_source|artifact_version_id|promotion_success|source == model|predictor_smoke" core/ml_trainer.py core/ml_predictor.py modules/ml_module.py -S
```

Key pre-change matches:

```text
modules/ml_module.py:431:                    "Artifact Version": summary.get("artifact_version_id"),
modules/ml_module.py:434:                    "Promotion Success": summary.get("promotion_success"),
modules/ml_module.py:517:    if result.get("predictor_smoke"):
core/ml_trainer.py:109:    "artifact_version_id",
core/ml_trainer.py:123:    "promotion_success",
core/ml_trainer.py:741:        "training_source": "fact_machine_hour",
core/ml_trainer.py:885:    predictor_smoke = _run_candidate_predictor_smoke(
core/ml_trainer.py:1009:        "artifact_version_id": version_id,
core/ml_trainer.py:1011:        "predictor_smoke": predictor_smoke,
core/ml_trainer.py:1012:        "promotion_success": True,
```

### Jan-Jun Gold month coverage summary

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT canonical_machine_id) AS distinct_machines,
    COUNT(CASE WHEN good_qty > 0 THEN 1 END) AS rows_with_positive_good_qty,
    COUNT(CASE WHEN hours_since_last_maintenance IS NOT NULL THEN 1 END) AS rows_with_maintenance_hours
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
GROUP BY 1
ORDER BY 1;
```

Output:

```text
2025-01|64725|87|22172|15556
2025-02|58461|87|23606|28273
2025-03|64725|87|33378|45204
2025-04|62637|87|33103|50966
2025-05|65165|88|35831|57064
2025-06|62639|87|36115|56178
```

### Task 4K promoted-column verification on Jan-Jun

Command:

```sql
SELECT
    substr(hour_ts,1,7) AS month,
    COUNT(*) AS total_rows,
    COUNT(team_size) AS team_size_nonnull,
    SUM(CASE WHEN has_maintenance_history = 1 THEN 1 ELSE 0 END) AS has_history_true,
    SUM(CASE WHEN maintenance_txn_in_hour = 1 THEN 1 ELSE 0 END) AS maintenance_in_hour_true,
    SUM(CASE WHEN maintenance_distinct_work_order_count_7d > 0 THEN 1 ELSE 0 END) AS count_7d_positive,
    SUM(CASE WHEN maintenance_distinct_work_order_count_30d > 0 THEN 1 ELSE 0 END) AS count_30d_positive,
    SUM(CASE WHEN maintenance_distinct_work_order_in_hour_count > 0 THEN 1 ELSE 0 END) AS in_hour_count_positive,
    SUM(CASE WHEN cumulative_maintenance_count > 0 THEN 1 ELSE 0 END) AS cumulative_positive
FROM fact_machine_hour
WHERE substr(hour_ts,1,7) BETWEEN '2025-01' AND '2025-06'
GROUP BY 1
ORDER BY 1;
```

Output:

```text
2025-01|64725|26325|15556|100|8791|15556|100|15556
2025-02|58461|28357|28273|95|8706|22056|95|28273
2025-03|64725|41692|45204|100|13010|33564|100|45204
2025-04|62637|41138|50966|79|11531|32481|79|50966
2025-05|65165|43069|57064|92|12481|34259|92|57064
2025-06|62639|43948|56178|84|11895|34601|84|56178
```

## What Changed

- `AGENTS.md`
  - added the persistent final-terminal-reply formatting addendum so future Codex windows inherit the ordered audit headings
- `core/ml_trainer.py`
  - changed retraining status and execution to require a real time-aware multi-month split for Task 4L
  - changed training prep to fit preprocessing on train-only rows and transform eval rows with the fitted bundle
  - added Task 4L artifact tagging/provenance fields and `task4l_artifacts/` archive paths
  - added candidate-vs-active holdout artifact evaluation and explicit promote-vs-retain decision logic
  - tightened fact-table loading and row preparation so the Jan-Jun live run completes in practical time
- `modules/ml_module.py`
  - stopped claiming every retraining run refreshes active artifacts
  - exposed the planned train/eval split and artifact decision in the UI result/status path
- `tests/test_ml_trainer.py`
  - added multi-month Task 4L fixtures and assertions for the time-aware split, Task 4L tagging, and non-promotion return path
- `tests/test_ml_module.py`
  - updated module helper coverage for Task 4L time-aware retraining summaries and Task 4L task-tag/provenance expectations

## Time-Aware Evaluation Design

Task 4L uses canonical Gold only.

- training months: `January 2025`, `February 2025`, `March 2025`, `April 2025`
- eval months: `May 2025`, `June 2025`
- rows loaded from `fact_machine_hour`: `378,352`
- rows after hard block: `133,299`
- rows after filtering: `132,549`
- distinct machines retained after filtering: `76`
- train rows: `67,599`
- eval rows: `64,950`

## Model Comparison Summary

Time-aware May-Jun holdout metrics on the Task 4L candidate run:

| model | R² | MAE | RMSE | rows_loaded | rows_after_hard_block | rows_after_filtering | distinct_machines_retained | train months | eval months |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `linear_regression` | `0.0105` | `0.0442` | `0.3005` | `378352` | `133299` | `132549` | `76` | Jan-Apr 2025 | May-Jun 2025 |
| `random_forest` | `0.8065` | `0.0120` | `0.1329` | `378352` | `133299` | `132549` | `76` | Jan-Apr 2025 | May-Jun 2025 |
| `xgboost` | `0.3789` | `0.0202` | `0.2380` | `378352` | `133299` | `132549` | `76` | Jan-Apr 2025 | May-Jun 2025 |

Task 4L answers:

- `xgboost` is no longer the best supported family on the Jan-Jun canonical foundation
- `random_forest` is the strongest supported model family on the Task 4L time-aware holdout
- compared with the earlier January-only random-split Task 4G baseline (`xgboost` `R² 0.2091`, `MAE 0.0118`, `RMSE 0.0777`), the broader Task 4L reevaluation shows materially stronger explanatory power (`R² 0.8065`) with similar MAE, though RMSE is higher on the broader, harder multi-month holdout and should not be compared naively across regimes

## Artifact Decision Summary

Candidate holdout evaluation on the same May-Jun holdout:

- model path: `models/task4l_artifacts/production_efficiency_model.candidate.20260401_000808.pkl`
- rows considered: `64,950`
- rows evaluated on `source == model`: `64,950`
- rows returning non-model source: `0`
- `R² 0.8065`
- `MAE 0.0120`
- `RMSE 0.1329`

Current active Task 4G holdout evaluation on the same May-Jun holdout:

- active model before promotion: `models/production_efficiency_model.pkl`
- rows considered: `64,950`
- rows evaluated on `source == model`: `63,958`
- rows returning non-model source: `992`
- first non-model source row: `024-128 @ 2025-05-02T19:00:00`
- `R² 0.2953`
- `MAE 0.0281`
- `RMSE 0.2555`

Decision:

- promotion gate passed
- candidate outperformed the current active bundle on the same time-aware holdout
- active artifacts were promoted to Task 4L version `20260401_000808`

Active artifact state after promotion:

- active model: `models/production_efficiency_model.pkl`
- active preprocessor: `models/production_preprocessor.pkl`
- active manifest task tag: `Task 4L`
- active selected model: `random_forest`
- backup model: `models/task4l_artifacts/production_efficiency_model.backup.20260401_000808.pkl`
- backup preprocessor: `models/task4l_artifacts/production_preprocessor.backup.20260401_000808.pkl`

Post-promotion active-path smoke:

- sample row: `024-135 @ 2025-01-12T16:00:00`
- prediction source: `model`
- predicted efficiency: `0.008754865518224944`
- confidence: `0.9028894697049799`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/ml_trainer.py modules/ml_module.py tests/test_ml_trainer.py tests/test_ml_module.py
python3 -m unittest tests.test_canonical_ml_reader tests.test_ml_predictor tests.test_ml_trainer tests.test_ml_module
python3 -m unittest tests.test_ml_trainer
```

Results:

- compile checks passed
- focused ML regression suite: `Ran 20 tests ... OK`
- post-performance-patch trainer regression: `Ran 8 tests ... OK`

Real live Task 4L execution proof:

- latest `ml_models` row is now `production_efficiency_20260401_0008 | random_forest | 0.8065397899689 | 0.0120314986012555`
- active manifests now point to Task 4L artifact version `20260401_000808`

## Remaining Limitations

- `task_difficulty` is still derived from `task_name` and still falls back to `Medium` when no mapping is available
- canonical ML still keeps the last-resort `team_size` default when both `team_size` and `manpower` are missing
- direct predictor calls outside the canonical reader path still retain generic optional-parameter defaults
- retraining remains synchronous and user-triggered

## Pass Status

Task 4L should be considered passed.

The Jan-Jun canonical reevaluation is now time-aware and auditable, `random_forest` displaced `xgboost` as the best supported family on the real May-Jun holdout, and the active artifacts were refreshed only after the new candidate beat the previous active Task 4G bundle on the same holdout and passed the promotion gate.
