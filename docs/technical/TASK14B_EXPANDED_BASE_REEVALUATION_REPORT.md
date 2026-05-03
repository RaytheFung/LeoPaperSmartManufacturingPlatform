# Task14B Expanded-Base Reevaluation Report

## 1. accepted baseline used

- Accepted baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
  - `Task13I`
  - `Task14A`
- Shared canonical base used for reevaluation:
  - `January 2025` -> `February 2026`
  - canonical source table: `fact_machine_hour`
- Active live artifacts at task start remained unchanged:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
- Task14B boundary remained reevaluation-only:
  - no shared-DB write
  - no live-artifact overwrite
  - no predictor-contract broadening
  - no promotion in this task

## 2. active artifact provenance frozen at task start

- Frozen active model provenance:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
  - `train_months = January 2025 -> April 2025`
  - `eval_months = May 2025 -> June 2025`
  - `month_coverage = January 2025 -> June 2025`
  - `rows_loaded = 378,352`
  - `rows_after_filtering = 132,549`
  - `distinct_machines_after_filtering = 76`
- This provenance was treated as the defended active baseline for every comparison below.
- Expanded canonical month coverage was not treated as automatic approval for promotion.

## 3. reevaluation protocol chosen and why

- One explicit protocol was frozen before any candidate training:
  - train one temp-only candidate bundle
  - keep the existing canonical ML feature contract
  - use the same trainer hard-block and filter logic as the current canonical ML path
  - use a time-aware holdout on the expanded canonical base
  - compare the temp candidate against the unchanged active Task 4L bundle on the exact same holdout slice
- Chosen split:
  - train months = `January 2025` -> `December 2025`
  - eval months = `January 2026` -> `February 2026`
  - train rows after filtering = `313,724`
  - eval rows after filtering = `50,675`
- Why this protocol was accepted:
  - it preserves the Task 4L time-aware design rather than drifting into a random split
  - it uses the expanded base honestly without leaking the evaluation months into training
  - it allows a direct saved-bundle comparison on the same rows and months
  - it keeps all candidate outputs on temp paths only

## 4. expanded-base candidate dataset summary

- Expanded-base trainer input summary:
  - rows loaded = `879,978`
  - rows hard-blocked = `512,241`
  - rows after hard block = `367,737`
  - rows after filtering = `364,399`
  - distinct machines retained = `84`
  - retained month coverage = `January 2025` -> `February 2026`
- Retained filtered month distribution:

| Month | Rows After Filtering | Distinct Machines |
| --- | ---: | ---: |
| January 2025 | `3,945` | `24` |
| February 2025 | `12,542` | `52` |
| March 2025 | `24,042` | `62` |
| April 2025 | `27,071` | `70` |
| May 2025 | `32,097` | `76` |
| June 2025 | `32,854` | `75` |
| July 2025 | `34,956` | `79` |
| August 2025 | `31,087` | `80` |
| September 2025 | `27,657` | `82` |
| October 2025 | `24,379` | `78` |
| November 2025 | `30,148` | `73` |
| December 2025 | `32,946` | `76` |
| January 2026 | `32,197` | `76` |
| February 2026 | `18,478` | `75` |

- Team-size default carryover remained narrow but non-zero:
  - `169` filtered rows
  - `30` machines
- Block dominance stayed explicit on the reevaluation slice:
  - Jan-Feb 2026 rows loaded for inference = `120,846`
  - Jan-Feb 2026 rows blocked for missing features = `69,327`
  - dominant blocked reason = `missing_positive_good_qty`
  - Jan-Feb 2026 `missing_positive_good_qty` blocks = `68,596`
  - Jan-Feb 2026 `missing_hours_since_last_maintenance` blocks = `731`

## 5. active-bundle comparison result on the chosen slice

- The same Jan-Feb 2026 reevaluation slice produced:
  - rows loaded for inference = `120,846`
  - rows eligible for inference = `51,519`
  - rows blocked for missing features = `69,327`
  - latest-machine candidates = `153`
  - latest-machine rows blocked after predictor gate = `0`
- Reevaluation-slice support-path mix:
  - direct canonical rows = `51,140`
  - adapted rows = `352`
  - defaulted rows = `27`
  - blocked rows = `69,327`
- Active Task 4L holdout result on that exact Jan-Feb 2026 slice:
  - rows considered = `50,675`
  - rows evaluated = `50,675`
  - non-model-source rows = `0`
  - distinct machines retained = `77`
  - `R² = 0.7605741131053376`
  - `MAE = 0.01499678606743838`
  - `RMSE = 0.1523568146386601`
- The active bundle therefore remained runnable and fair to compare on the expanded-base holdout; this was not an apples-to-oranges fallback path.

## 6. temp candidate training result

- One temp-only candidate bundle was trained and stored outside live `models/`:
  - candidate model path = `/tmp/task14b_candidate/production_efficiency_model.candidate.task14b.pkl`
  - candidate preprocessor path = `/tmp/task14b_candidate/production_preprocessor.candidate.task14b.pkl`
- Candidate model family comparison on the frozen Jan-Feb 2026 holdout:

| Model | R² | MAE | RMSE |
| --- | ---: | ---: | ---: |
| Linear regression | `0.006707922657925303` | `0.046101496332793354` | `0.31032360909301165` |
| Random forest | `0.812714004142606` | `0.012804444950338988` | `0.13475006522302904` |
| XGBoost | `0.45202642295959194` | `0.018341191294290352` | `0.23049215083984392` |

- Selected temp candidate:
  - `random_forest`
- Temp candidate training footprint:
  - train rows = `313,724`
  - eval rows = `50,675`
  - rows loaded = `879,978`
  - rows after hard block = `367,737`
  - rows after filtering = `364,399`
  - distinct machines retained = `84`

## 7. active vs candidate comparison

| Comparison Item | Active Task 4L Bundle | Temp Task14B Candidate |
| --- | --- | --- |
| Eval months | `January 2026` -> `February 2026` | `January 2026` -> `February 2026` |
| Rows considered | `50,675` | `50,675` |
| Rows evaluated | `50,675` | `50,675` |
| Non-model-source rows | `0` | `0` |
| Distinct machines retained | `77` | `77` |
| R² | `0.7605741131053376` | `0.812714004142606` |
| MAE | `0.01499678606743838` | `0.012804444950338988` |
| RMSE | `0.1523568146386601` | `0.13475006522302904` |

- Holdout conclusion:
  - the temp candidate beat the active bundle on all three comparison metrics
  - the comparison stayed fair because months, rows, blocked-rule contract, and saved-predictor evaluation path were identical
- Routed inference helper behavior stayed stable enough for this reevaluation boundary:
  - latest-machine predictor gate blocked `0` rows on the Jan-Feb 2026 reevaluation slice
  - no support-path widening was needed

## 8. temp inference smoke result

- Temp candidate smoke passed:
  - `source == model`
  - sample month = `January 2025`
  - sample machine = `024-135`
  - sample hour = `2025-01-12T16:00:00`
  - predicted efficiency = `0.008997239070611677`
  - confidence = `0.9028894697049799`
- Temp latest-machine gate outcome on the Jan-Feb 2026 reevaluation slice:
  - latest-machine candidates = `153`
  - blocked after predictor gate = `0`
- This proved that the temp candidate bundle could be loaded through the canonical predictor path without swapping the live bundle.

## 9. shared DB / live artifact safety

- Shared DB safety:
  - no shared `manufacturing_data.db` write was performed in Task14B
  - Task14B was executed as reevaluation only, not ETL/materialization/promotion
- Live artifact safety:
  - no file under live `models/production_*` was overwritten
  - active provenance remained Task 4L only
  - candidate artifacts were written only to `/tmp/task14b_candidate/`
- Task14B therefore closed as a temp-only comparison task, not a live replacement task.

## 10. remaining limitations

- Task14B does not promote artifacts.
- The reevaluation conclusion is about candidacy, not live activation.
- Inference coverage on the reevaluation slice is still partial:
  - blocked rows = `69,327` of `120,846`
  - `missing_positive_good_qty` remains the overwhelming blocker
- The temp candidate path is an ephemeral staging location under `/tmp`, not a defended live runtime attachment.
- This task proved a narrow canonical predictor smoke only; it did not run a full routed UI/AppTest sweep on the temp bundle.

## 11. promotion recommendation after Task14B

- Outcome: **candidate clearly beats active bundle and is promotion-worthy later**
- Reason:
  - the temp candidate improved `R²`
  - the temp candidate reduced `MAE`
  - the temp candidate reduced `RMSE`
  - both bundles were evaluated on the same Jan-Feb 2026 holdout with zero fallback rows
- Governance boundary after Task14B:
  - keep the live Task 4L bundle unchanged now
  - if promotion is desired, run one separate later promotion task only
  - that later task should revalidate the temp bundle, preserve rollback paths, and then decide whether to replace the live bundle
