# Task14B Model Comparison Matrix

## 1. frozen protocol

| Item | Value |
| --- | --- |
| Active baseline | `Task 4L` |
| Active artifact version | `20260401_000808` |
| Active train months | `January 2025` -> `April 2025` |
| Active eval months | `May 2025` -> `June 2025` |
| Task14B strategy | `time_aware_multi_month_holdout` |
| Task14B train months | `January 2025` -> `December 2025` |
| Task14B eval months | `January 2026` -> `February 2026` |
| Candidate bundle state | temp-only |
| Live artifact promotion | not performed |

## 2. expanded-base dataset matrix

| Metric | Value |
| --- | ---: |
| Rows loaded | `879,978` |
| Rows hard-blocked | `512,241` |
| Rows after hard block | `367,737` |
| Rows after filtering | `364,399` |
| Distinct machines retained | `84` |
| Train rows | `313,724` |
| Eval rows | `50,675` |

## 3. reevaluation-slice inference matrix

| Metric | Value |
| --- | ---: |
| Jan-Feb 2026 rows loaded for inference | `120,846` |
| Jan-Feb 2026 rows eligible for inference | `51,519` |
| Jan-Feb 2026 rows blocked for missing features | `69,327` |
| Latest-machine candidates | `153` |
| Latest-machine rows blocked after predictor gate | `0` |
| Direct canonical rows | `51,140` |
| Adapted rows | `352` |
| Defaulted rows | `27` |
| Dominant blocker | `missing_positive_good_qty (68,596)` |

## 4. holdout comparison matrix

| Metric | Active Task 4L | Temp Task14B Candidate |
| --- | ---: | ---: |
| Rows considered | `50,675` | `50,675` |
| Rows evaluated | `50,675` | `50,675` |
| Distinct machines retained | `77` | `77` |
| Non-model-source rows | `0` | `0` |
| R² | `0.7605741131053376` | `0.812714004142606` |
| MAE | `0.01499678606743838` | `0.012804444950338988` |
| RMSE | `0.1523568146386601` | `0.13475006522302904` |

## 5. candidate model family matrix

| Candidate Model | R² | MAE | RMSE |
| --- | ---: | ---: | ---: |
| Linear regression | `0.006707922657925303` | `0.046101496332793354` | `0.31032360909301165` |
| Random forest | `0.812714004142606` | `0.012804444950338988` | `0.13475006522302904` |
| XGBoost | `0.45202642295959194` | `0.018341191294290352` | `0.23049215083984392` |

## 6. governance outcome

- Recommendation: `candidate clearly beats active bundle and is promotion-worthy later`
- Temp smoke: `passed`, `source == model`
- Live DB change: none
- Live artifact change: none
