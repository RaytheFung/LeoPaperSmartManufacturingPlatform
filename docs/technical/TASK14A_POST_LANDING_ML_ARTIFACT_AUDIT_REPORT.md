# Task14A Post-Landing ML Artifact Audit Report

## 1. accepted baseline used

- Accepted runtime baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
  - `Task13I`
- Shared DB baseline audited read-only:
  - `manufacturing_data.db`
  - SHA1 during Task14A = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - canonical `fact_machine_hour` coverage = `January 2025` -> `February 2026`
- Active artifacts stayed unchanged throughout Task14A:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
- Task14A hard boundary stayed read-only:
  - no retraining
  - no artifact promotion
  - no DB write
  - no canonical semantic change

## 2. live canonical coverage vs active artifact coverage

- Live canonical coverage now spans `14` months on the shared DB:
  - `January 2025` -> `February 2026`
  - `fact_machine_hour` rows on the live DB = `879,978`
- Active artifact provenance still reflects the earlier Jan-Jun-only bundle:
  - artifact `month_coverage` = `January 2025` -> `June 2025`
  - `train_months` = `January 2025` -> `April 2025`
  - `eval_months` = `May 2025` -> `June 2025`
  - provenance `rows_loaded = 378,352`
  - provenance `rows_after_filtering = 132,549`
- The live canonical expansion therefore created an explicit provenance gap:
  - post-provenance live months = `July 2025` -> `February 2026`
  - post-provenance live canonical rows = `501,626`
- Routed inference is still live on that expanded base because the canonical ML contract did not break:
  - predictor bundle present = `true`
  - model artifact present = `true`
  - canonical inference enabled = `true`

## 3. month-by-month ML readiness results

- The routed ML surface remained non-empty on every landed month from `January 2025` through `February 2026`.
- A compact per-month readiness table is recorded in `TASK14A_MONTHLY_ML_READINESS_MATRIX.md`.
- The core month-by-month audit result is:

| Month | Canonical rows loaded | Inferable rows | Inferable machines | Latest-machine model candidates | Dominant blocked reason |
| --- | ---: | ---: | ---: | ---: | --- |
| January 2025 | `64,725` | `3,945` | `24` | `24` | `missing_positive_good_qty` |
| February 2025 | `58,461` | `12,577` | `52` | `52` | `missing_positive_good_qty` |
| March 2025 | `64,725` | `24,727` | `63` | `63` | `missing_positive_good_qty` |
| April 2025 | `62,637` | `27,914` | `71` | `71` | `missing_positive_good_qty` |
| May 2025 | `65,165` | `32,607` | `77` | `77` | `missing_positive_good_qty` |
| June 2025 | `62,639` | `33,798` | `76` | `76` | `missing_positive_good_qty` |
| July 2025 | `64,727` | `35,701` | `80` | `80` | `missing_positive_good_qty` |
| August 2025 | `64,727` | `31,582` | `81` | `81` | `missing_positive_good_qty` |
| September 2025 | `62,640` | `28,123` | `83` | `83` | `missing_positive_good_qty` |
| October 2025 | `64,247` | `25,407` | `81` | `81` | `missing_positive_good_qty` |
| November 2025 | `61,199` | `31,572` | `76` | `76` | `missing_positive_good_qty` |
| December 2025 | `63,240` | `34,261` | `77` | `77` | `missing_positive_good_qty` |
| January 2026 | `63,054` | `32,757` | `77` | `77` | `missing_positive_good_qty` |
| February 2026 | `57,792` | `18,762` | `76` | `76` | `missing_positive_good_qty` |

- Post-June routed ML readiness stayed materially usable rather than collapsing:
  - post-June canonical rows loaded = `501,626`
  - post-June inferable rows = `238,165`
  - post-June inferable machines across the full window = `84`
  - post-June latest-machine model candidates = `631`
- All `631` post-June latest-machine candidates returned `source == model`.

## 4. blocked-reason and support-path analysis

- Across the post-June window `July 2025` -> `February 2026`, blocked reasons remained narrow and stable:
  - `missing_positive_good_qty = 258,735`
  - `missing_hours_since_last_maintenance = 4,725`
  - `unmapped_task_name = 1`
- There was no broad post-June task-name mapping regression:
  - the only observed unmapped-task block in the full post-June audit was `1` row in `July 2025`
- Support-path composition on the same post-June window was overwhelmingly direct:
  - direct canonical rows = `236,062`
  - adapted rows = `2,006`
  - defaulted rows = `97`
  - blocked rows = `263,461`
- On inferable post-June rows only, the support-path mix was:
  - direct = about `99.1%`
  - adapted = about `0.8%`
  - defaulted = about `0.04%`
- The active saved bundle therefore still scores post-June candidates honestly, but most of the expanded row set remains outside the inference contract because of data-shape blockers, not predictor failure.

## 5. routed ML / optimization / experimental-surface audit on post-June months

- Routed ML page behavior on the post-June months stayed honest:
  - each landed post-June month produced non-zero inferable rows
  - each landed post-June month produced non-zero latest-machine model candidates
  - no post-June latest-machine candidate fell back to simulation
- Routed Optimization behavior also stayed live across every post-June month:
  - machine-summary rows per month = `85` -> `87`
  - schedule payload rows per month = `24`
  - team payload rows per month = `231` -> `286`
  - no post-June schedule payload or team payload blocked
- Representative Optimization top-machine results were stable and explicit rather than empty/fallback:
  - `July 2025`: top machine `024-092`, score `0.6047`, top driver `High non-productive share`
  - `August 2025`: top machine `166-002`, score `0.5885`, top driver `High kWh per good unit`
  - `February 2026`: top machine `024-003`, score `0.6275`, top driver `High non-productive share`
- Representative experimental-route anchors also closed read-only on the expanded base:
  - `July 2025`: anchor machine pool `87`, seeded queue `5`, optimized schedule rows `5`, maintenance risk rows `87`
  - `December 2025`: anchor machine pool `85`, seeded queue `5`, optimized schedule rows `5`, maintenance risk rows `85`
  - `February 2026`: anchor machine pool `86`, seeded queue `5`, optimized schedule rows `5`, maintenance risk rows `86`
- The experimental route stayed explicit about provenance rather than hiding support limits:
  - scheduling remained `Real-seeded synthetic queue`
  - predictive maintenance stayed `Weak-label model`
  - stored maintenance-event horizon still ended at `2025-08-14`, even when the current-state anchor month moved to `December 2025` or `February 2026`

## 6. drift / refresh-readiness assessment

- The real Task14A governance gap is artifact freshness, not route breakage.
- The active Task 4L bundle still works on the expanded canonical base, but its provenance and evaluation window now lag the live DB materially.
- A separate future artifact-refresh task would now have enough live canonical support to run honestly if explicitly approved:
  - direct trainer-parity SQL audit found `fact_machine_hour` rows read = `879,978`
  - hard-blocked rows = `512,241`
  - rows after hard block = `367,737`
  - rows after trainer-style filtering = `364,399`
  - distinct machines after filtering = `84`
  - filtered month coverage = `January 2025` -> `February 2026`
- Under the current Task 4L time-aware split contract, that later reevaluation window would resolve to:
  - train months = `January 2025` -> `December 2025`
  - eval months = `January 2026` -> `February 2026`
  - train rows = `313,724`
  - eval rows = `50,675`
- That potential reevaluation base is much broader than the current active provenance:
  - active provenance `rows_after_filtering = 132,549`
  - read-only expanded-base reevaluation base = `364,399`
- Task14A does **not** approve retraining or promotion.
- Task14A closes only the audit question:
  - the routed surfaces still work
  - the active artifacts are now stale relative to the live canonical base
  - a separate explicit reevaluation task would be technically justified

## 7. shared DB / artifact safety

- Shared DB remained unchanged during Task14A:
  - `manufacturing_data.db` SHA1 before audit = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - `manufacturing_data.db` SHA1 after audit = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
- No artifact file under `models/` was changed.
- No retraining or promotion was run against the live repo artifact paths.
- Task14A-only generated outputs were read-only diagnostics and `/tmp` helper files only.

## 8. remaining limitations

- Active artifact provenance still stops at `June 2025` even though the shared canonical base now reaches `February 2026`.
- Post-June routed ML readiness is partial, not full:
  - `263,461` post-June rows still remain outside the inference contract
  - the dominant blocker remains `missing_positive_good_qty`
- The experimental predictive-maintenance route remains bonus-only and its stored maintenance-event support still ends at `2025-08-14`, so late-anchor views must continue to disclose that evidence horizon honestly.
- `March 2026` remains intentionally out of scope.
- `February 2026` still carries the accepted Task13I flag/quarantine posture:
  - localized partial-energy flags remain active
  - `1262-00012` remains quarantined
- Local AppTest route validation under `/usr/bin/python3` (`Python 3.9`) is still blocked by the existing PEP 604 union annotation in `modules/etl_module.py`; Task14A validation therefore relied on the passed non-AppTest Task14A suites plus direct live-data route/helper audits.

## 9. recommended next step after Task14A

- No further Task14A work is required.
- If a follow-up is desired, keep it separate from Task14A and make it explicit:
  - run one non-promoted expanded-base reevaluation on temp copies only
  - keep the current Task 4L predictor contract
  - compare the candidate against the active bundle on the same time-aware holdout
  - promote only if the candidate wins and post-train predictor smoke still returns `source == model`
- Do not combine that later follow-up with:
  - DB landing
  - canonical semantic changes
  - solver promotion
  - predictive-maintenance production claims
