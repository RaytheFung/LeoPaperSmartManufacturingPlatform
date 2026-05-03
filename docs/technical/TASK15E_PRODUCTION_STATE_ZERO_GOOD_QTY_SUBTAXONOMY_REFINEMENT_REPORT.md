# Task15E Production-State Zero Good Qty Subtaxonomy Refinement Report

## 1. accepted baseline used

- Accepted live baseline remained:
  - `Task14F passed`
  - `Task15A passed`
  - `Task15C passed`
  - `Task15D` completed as read-only evidence audit
- Active live bundle remained unchanged:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
- Default runtime DB path remained the repo-local:
  - `manufacturing_data.db`

## 2. task boundary kept

- Task15E stayed narrow:
  - no DB writes
  - no ETL/materialization rerun
  - no retraining
  - no artifact promotion
  - no predictor-contract broadening
  - no Gold quantity-semantic rewrite
- The task only refined production-state blocked taxonomy on the routed canonical ML readiness/reporting path.

## 3. subtaxonomy landed

- The former production-state parent bucket `missing_positive_good_qty_production_state` is now refined into:
  - `missing_positive_good_qty_production_state_likely_state_label_contradiction`
  - `missing_positive_good_qty_production_state_likely_quantity_overlay_gap`
  - `missing_positive_good_qty_production_state_likely_order_or_material_context_conflict`
  - `missing_positive_good_qty_production_state_likely_source_quality_or_anomaly_case`
- The parent production-state bucket is retained only as a conservative fallback if current row context is ever insufficient for a narrower production-state subreason.
- All affected rows remain blocked.

## 4. code changes applied

- `core/canonical_ml_reader.py`
  - added the production-state zero-good-qty subtaxonomy constants
  - added one shared classifier that uses existing row context only
  - updated inference-side blocking to call that shared classifier
- `core/ml_trainer.py`
  - widened the read-only trainer input query to include the row-context fields needed for the same subtaxonomy
  - mirrored the same classifier on both the bulk trainer path and `_build_training_row()`
- `core/ml_review_queue.py`
  - added readable labels and descriptions for the new production-state subreasons
- `modules/ml_module.py`
  - updated the selected-month readiness wording and audit-contract wording so the new production-state subtaxonomy is visible without redesigning the page
- `tests/test_ml_trainer.py`
  - added focused mirrored-subtaxonomy coverage including the conservative production-state fallback
- `tests/test_ml_module.py`
  - updated the blocked-reason snapshot test to use readable production-state subreason labels
- `tests/test_ml_review_queue.py`
  - updated blocked-summary label coverage for the new production-state subreasons

## 5. validation result

- `py_compile` passed on:
  - `core/canonical_ml_reader.py`
  - `core/ml_trainer.py`
  - `core/ml_review_queue.py`
  - `modules/ml_module.py`
  - `tests/test_ml_trainer.py`
  - `tests/test_ml_module.py`
  - `tests/test_ml_review_queue.py`
- Focused unit tests passed:
  - `tests.test_ml_trainer`
  - `tests.test_ml_module`
  - `tests.test_ml_review_queue`
- Repo-local read-only DB validation confirmed the exact Task15D target slice remained:
  - total target slice = `825`
  - all `825` rows stayed blocked on the inference path
  - all `825` rows stayed blocked on the trainer path
  - inference-side and trainer-side subreason counts matched exactly:
    - `likely_state_label_contradiction = 725`
    - `likely_quantity_overlay_gap = 85`
    - `likely_order_or_material_context_conflict = 14`
    - `likely_source_quality_or_anomaly_case = 1`
  - production-state parent fallback rows on the live target slice = `0`

## 6. live DB / live artifact safety

- Repo-local DB contents remained untouched.
- No write-capable SQL path was executed.
- No ETL/materialization path was executed.
- No canonical semantics changed.
- Live Task14F artifacts remained unchanged.

## 7. closeout decision

- Result: **Task15E passed**
- Why it passed:
  - the change stayed narrow
  - the new production-state subtaxonomy is evidence-backed by Task15D plus fresh repo-local validation
  - all affected rows remain blocked
  - no training/inference eligibility broadened
  - focused validation passed
