# TASK4S Post-Quantity ML Artifact Refresh Audit Report

## Outcome

This separate post-Task4S canonical ML artifact refresh audit passed.

Scope stayed ML-only:

- no live DB write was performed
- no live artifact path under `models/` was overwritten
- no model/preprocessor promotion ran
- no maintenance / optimization / energy page code was touched
- no Task 4S quantity logic was reopened

Direct-source-verified conclusion:

- the active Task 4L bundle is still the correct live bundle to keep
- a fresh candidate retrained on the current canonical Jan-Jun trainer path did not beat the current active Task 4L artifacts on the same May-Jun holdout
- a separate artifact-promotion task is not justified now

## Live Repo And Artifact Preflight

Direct-source-verified live repo paths audited from the real repo tree:

- [`core/ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py)
- [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
- [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py)
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
- [`tests/test_ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_trainer.py)
- [`tests/test_ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_predictor.py)
- [`tests/test_canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_ml_reader.py)
- [`models/production_efficiency_model.provenance.json`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/models/production_efficiency_model.provenance.json)
- [`models/production_preprocessor.provenance.json`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/models/production_preprocessor.provenance.json)

Active artifact summary:

- active model path: `models/production_efficiency_model.pkl`
- active preprocessor path: `models/production_preprocessor.pkl`
- active manifest task tag: `Task 4L`
- active artifact version: `20260401_000808`
- active selected model: `random_forest`
- active evaluation strategy in the manifest: `time_aware_multi_month_holdout`
- active manifest train months: `January 2025` through `April 2025`
- active manifest eval months: `May 2025` and `June 2025`

Live status helper summary on the current repo/runtime state:

- current trainer-path rows loaded: `378,352`
- current rows after hard block: `133,301`
- current rows after filtering: `132,551`
- current distinct machines after filtering: `76`
- current month coverage: `January 2025` through `June 2025`
- current residual `team_size_from_preprocessor_default` rows: `72` across `16` machines

Direct-source-verified trainer source-path audit:

- [`core/ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py) reads training rows from canonical `fact_machine_hour` only
- `rg -n "unified_view|three_way_matches" core/ml_trainer.py` returned no matches

Residual caution:

- [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) still contains separate legacy helper lookups outside the formal canonical trainer path, as already documented in the downstream impact audit
- this task audited the formal canonical trainer / predictor-bundle path only

## Post-Task4S Canonical ML Data Shift

### Direct-source-verified current trainer hard-block base

Read-only rowid comparison between the active DB and the pre-Task4S execution backup on the current hard-block trainer base:

- active base definition: `good_qty > 0`, `energy_total_kwh > 0`, `hours_since_last_maintenance IS NOT NULL`
- rows compared: `133,301`
- rows whose `production_qty = good_qty` changed: `2,563`
- rows whose derived `kwh_per_unit` changed: `2,563`
- rows whose `task_name` changed: `0`
- rows whose `hours_since_last_maintenance` changed: `0`
- rows whose `canonical_machine_id` changed: `0`

Month-by-month hard-block shift summary:

| month | rows compared | rows with `production_qty` changed | rows with `kwh_per_unit` changed |
| --- | ---: | ---: | ---: |
| `2025-01` | `3,945` | `49` | `49` |
| `2025-02` | `12,577` | `236` | `236` |
| `2025-03` | `24,328` | `391` | `391` |
| `2025-04` | `27,450` | `532` | `532` |
| `2025-05` | `32,118` | `704` | `704` |
| `2025-06` | `32,883` | `651` | `651` |

### Direct-source-verified current filtered trainer base

Read-only rowid comparison on the stricter current post-filter trainer base:

- filtered base definition used in this audit:
  - `good_qty >= 1`
  - `energy_total_kwh >= 0.25`
  - `hours_since_last_maintenance IS NOT NULL`
  - `(energy_total_kwh / good_qty) <= 20`
- active filtered rows: `132,551`
- backup filtered rows: `132,551`
- rows compared after rowid join: `132,550`
- rows whose `production_qty = good_qty` changed: `2,559`
- rows whose derived `kwh_per_unit` changed: `2,559`
- rows whose `task_name` changed: `0`
- rows whose `hours_since_last_maintenance` changed: `0`
- rows whose `canonical_machine_id` changed: `0`

Month-by-month filtered shift summary:

| month | rows compared | rows with `production_qty` changed | rows with `kwh_per_unit` changed |
| --- | ---: | ---: | ---: |
| `2025-01` | `3,945` | `49` | `49` |
| `2025-02` | `12,542` | `236` | `236` |
| `2025-03` | `24,042` | `391` | `391` |
| `2025-04` | `27,071` | `530` | `530` |
| `2025-05` | `32,096` | `703` | `703` |
| `2025-06` | `32,854` | `650` | `650` |

Direct-source-verified filtered-base eligibility judgment:

- net filtered-row count change: `0`
- distinct-machine coverage change: `0`
- month coverage change: `0`
- eligibility did not change materially on net

Boundary effect that explains the tiny filtered-base membership shuffle:

- one row entered the filtered base in active May 2025:
  - `rowid 613320`, machine `024-141`
  - backup `good_qty 0.964348334307423`, `kwh_per_unit 68.44`
  - active `good_qty 1003.43708761539`, `kwh_per_unit 0.0657739292423857`
- one row left the filtered base in active June 2025:
  - `rowid 629708`, machine `024-003`
  - backup `good_qty 5.85961342828077`, `kwh_per_unit 1.97965277777778`
  - active `good_qty 0.169605183551959`, `kwh_per_unit 68.3941360580311`

Evidence-based interpretation:

- Task 4S clearly changed canonical ML numeric inputs on a non-trivial but still minority slice of the trainer base
- the change remained concentrated in `good_qty` / derived efficiency rather than in task labels, maintenance-recency coverage, or machine coverage
- the current `rows_after_filtering` difference between the Task 4L manifest (`132,549`) and the current live trainer status (`132,551`) is not explained by Task 4S quantity shift alone, because the active-vs-backup filtered-row total is flat on the current code path; this strongly suggests later post-Task4L ML-path logic changes account for that extra `+2`

## Candidate Retraining Audit Run

Because [`core/ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py) still writes `ml_models` metadata when training runs, the candidate evaluation was staged on a temp copy of the active DB rather than on the live runtime DB.

Direct-source-verified temp-run setup:

- temp DB: a copy of the active `manufacturing_data.db`
- active model/preprocessor paths were not overwritten
- candidate artifacts were written only to temp candidate paths under the temp directory
- the temp DB `ml_models` row count increased from `18` to `19` inside the temp copy only

Direct-source-verified current candidate training regime:

- training source: canonical `fact_machine_hour` only
- evaluation strategy: `time_aware_multi_month_holdout`
- train months: `January 2025`, `February 2025`, `March 2025`, `April 2025`
- eval months: `May 2025`, `June 2025`
- rows loaded: `378,352`
- rows after hard block: `133,301`
- rows after filtering: `132,551`
- distinct machines retained: `76`
- train rows: `67,600`
- eval rows: `64,951`
- selected model family: `random_forest`

Candidate model-family metrics on the current holdout:

| model | R² | MAE | RMSE |
| --- | ---: | ---: | ---: |
| `linear_regression` | `0.010749582308933525` | `0.043793161901624446` | `0.29733257643938993` |
| `random_forest` | `0.800867195516742` | `0.011979124248994758` | `0.13340152000131822` |
| `xgboost` | `0.44162313023076083` | `0.02222209655338852` | `0.22338452439984316` |

## Candidate Vs Active Holdout Comparison

Direct-source-verified same-holdout predictor-bundle comparison on the temp DB copy:

| bundle | rows considered | rows evaluated on `source == model` | rows returning non-model source | R² | MAE | RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current active Task 4L bundle | `64,951` | `64,951` | `0` | `0.8048873803560286` | `0.011954868340209885` | `0.1320480684600202` |
| fresh non-promoted candidate | `64,951` | `64,951` | `0` | `0.800867195516742` | `0.011979124248994758` | `0.13340152000131822` |

Direct-source-verified judgment:

- the active Task 4L bundle beat the fresh candidate on all three holdout metrics
- the candidate did not outperform the active bundle on the same eval regime
- there is no current evidence basis for a promotion task

## Predictor Compatibility Smoke

Direct-source-verified candidate smoke:

- candidate model loaded through [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py): passed
- candidate preprocessor loaded through [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py): passed
- first successful canonical smoke prediction returned `source == model`: yes
- smoke sample month: `January 2025`
- smoke sample machine: `024-135`
- sample hour: `2025-01-12T16:00:00`
- sample predicted efficiency: `0.008801926778181656`
- smoke confidence: `0.9028894697049799`

Feature-contract judgment:

- no feature-contract drift was observed between the current trainer output and [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
- no load breakage was observed
- no fallback/non-model source was required on the holdout rows or the smoke row

## Decision

Recommended decision:

- keep the current active Task 4L artifacts unchanged

Reason:

- Task 4S changed a measurable slice of canonical ML numeric inputs
- that shift was not large enough to make a fresh candidate beat the current active Task 4L bundle on the same current holdout
- current active artifacts remain loadable, provenance-backed, canonical, and predictor-compatible

Not recommended now:

- a separate artifact-promotion task

## Exact File List Touched

- [`docs/technical/TASK4S_POST_QUANTITY_ML_ARTIFACT_REFRESH_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_POST_QUANTITY_ML_ARTIFACT_REFRESH_AUDIT_REPORT.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)

## Exact Reason For Each Change

- [`docs/technical/TASK4S_POST_QUANTITY_ML_ARTIFACT_REFRESH_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_POST_QUANTITY_ML_ARTIFACT_REFRESH_AUDIT_REPORT.md)
  - records the live artifact state, post-Task4S data-shift evidence, temp-scoped candidate retraining audit, same-holdout candidate-vs-active comparison, predictor smoke, and final keep-vs-promote decision
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexes this ML audit close so future handoff reads can find the post-Task4S artifact decision directly
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - adds one factual live-ledger line stating that the active Task 4L bundle remains the correct live bundle after the post-Task4S ML artifact refresh audit

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/ml_trainer.py core/ml_predictor.py core/canonical_ml_reader.py modules/ml_module.py
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_ml_trainer tests.test_ml_predictor tests.test_canonical_ml_reader
```

Read-only / temp-scoped audit commands also run:

- read-only trainer-source grep on [`core/ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py)
- read-only active-vs-backup SQL comparisons on the current trainer hard-block and filtered bases
- temp-copy candidate retraining/evaluation against the same current holdout

Results:

- compile checks: passed
- focused ML regression suite: `Ran 20 tests ... OK`
- candidate predictor smoke: passed
- active-vs-candidate same-holdout comparison: completed

## Remaining Limitations

- the candidate audit used a temp DB copy because the current trainer still inserts `ml_models` metadata when training runs
- the filtered-base eligibility comparison in this audit used the trainer’s current numeric filters directly in SQL and relied on the current code path’s already-proven task-family mapping / fallback rules rather than replaying every adapter flag in SQL
- this task did not re-score every visible ML page month end to end; the decisive comparison here was the formal holdout bundle-vs-bundle evaluation on the current accepted regime
- legacy helper lookups still remain outside the formal canonical trainer path, as already documented in the downstream impact audit
