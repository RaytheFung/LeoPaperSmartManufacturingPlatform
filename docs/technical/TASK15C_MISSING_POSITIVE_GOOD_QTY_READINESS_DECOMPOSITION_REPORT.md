# Task15C Missing Positive Good Qty Readiness Decomposition Report

## 1. accepted baseline used

- Accepted live baseline remained:
  - `Task14F passed`
  - `Task15A passed`
- Active live bundle remained unchanged:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
- Default runtime DB path remained the repo-local:
  - `manufacturing_data.db`

## 2. task boundary kept

- Task15C stayed narrow:
  - no DB writes
  - no ETL/materialization rerun
  - no retraining
  - no artifact promotion
  - no predictor-contract broadening
  - no Gold quantity-semantic rewrite
- The task only changed ML readiness / reporting logic on the routed canonical path.

## 3. taxonomy introduced

- The former single blocked reason `missing_positive_good_qty` is now decomposed into:
  - `missing_positive_good_qty_nonproductive_state`
  - `missing_positive_good_qty_production_state`
  - `missing_positive_good_qty_insufficient_context`
- The taxonomy stays intentionally narrow:
  - nonproductive states such as `setup_changeover`, `planned_stop`, and `unplanned_stop` are separated as honest no-good-qty-expected rows
  - `production` rows with zero / missing `good_qty` remain blocked but are now isolated as the narrow production-state quantity gap slice
  - rows without enough state context stay blocked as insufficient-context rows
- Eligibility did not broaden:
  - the same rows remain blocked
  - only the reporting taxonomy changed

## 4. code changes applied

- `core/canonical_ml_reader.py`
  - added one shared narrow classifier for missing / non-positive `good_qty`
  - inference-side blocked rows now use the new subreasons
- `core/ml_trainer.py`
  - mirrored the same taxonomy on the training-side blocked rows
  - kept all prior blocking boundaries intact
- `core/ml_review_queue.py`
  - added blocked-reason metadata for labels, families, and descriptions
  - blocked summaries now surface the decomposed readiness loss cleanly
- `modules/ml_module.py`
  - updated the selected-month readiness surface to explain the decomposition
  - updated the blocked summary chart to use readable labels
  - updated the blocked-detail table to keep both label and raw reason code visible
  - corrected the directly touched active-artifact caption from stale `Task 4L` wording to the accepted `Task 14F` state

## 5. read-only live DB evidence

- Validation month used:
  - `February 2026`
- Repo-local DB diagnostics confirmed the former single `missing_positive_good_qty` month slice was:
  - total former bucket = `38,624`
  - `missing_positive_good_qty_insufficient_context` = `33,170`
  - `missing_positive_good_qty_nonproductive_state` = `5,318`
  - `missing_positive_good_qty_production_state` = `136`
- Post-June window (`July 2025` -> `February 2026`) decomposition was:
  - total former bucket = `258,735`
  - `missing_positive_good_qty_insufficient_context` = `188,938`
  - `missing_positive_good_qty_nonproductive_state` = `68,972`
  - `missing_positive_good_qty_production_state` = `825`
  - remaining post-June non-`good_qty` blocker outside that family = `missing_hours_since_last_maintenance` `4,725`
  - residual post-June unmapped-task blocker = `1`

## 6. validation result

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
- Focused test proof points now cover:
  - the new subreason taxonomy appearing on both inference and training paths
  - rows staying blocked rather than becoming newly inferable / trainable
  - the readiness/reporting layer using readable decomposed blocker labels

## 7. live DB / artifact safety

- Repo-local DB remained unchanged:
  - SHA1 after Task15C validation = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
- Active artifact fingerprints remained unchanged:
  - model `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - preprocessor `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - model provenance `d23648bb1fb24b9e830ba6586df5ed4faf02645522b085293e968f3a76774ff5`
  - preprocessor provenance `66cbdb505ef3c577a0523efabf8881d6f6b104470fc17ff203f44f520d3a7611`

## 8. closeout decision

- Result: **Task15C passed**
- Why it passed:
  - the taxonomy stayed narrow and evidence-backed
  - no DB write occurred
  - no training/inference eligibility broadened
  - the reporting surface now shows the decomposed blocked loss
  - focused validation passed on both tests and repo-local read-only DB evidence
