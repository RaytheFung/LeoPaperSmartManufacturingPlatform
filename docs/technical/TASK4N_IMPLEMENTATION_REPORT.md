# TASK4N Implementation Report

## Outcome

Task 4N passed.

Task 4N closed in three narrow phases without widening scope into a new numbered task, without rewriting Gold/materialization broadly, and without retraining or promoting new ML artifacts.

- Phase A fixed the remaining Gold-side crew-truth inconsistency.
- Phase B audited the live DB blast radius and confirmed no active DB write was warranted.
- Phase C quantified the residual crew fallback from the real canonical trainer path and retained the preprocessor-default `team_size` path as a narrow, explicitly documented exception.

## Phase A

### Gold-side inconsistency fixed

The live Python Gold builder still had one rerun bug after Task 4M:

- CSI overlay could derive a valid `team_size` from `team_leader + team_members_raw`
- MES overlay could temporarily override that with positive `manpower`
- but a later MES rerun with no surviving valid match cleared `team_size` back to `NULL`

This was inconsistent with the intended Task 4N semantics and with the SQL repair path.

### What changed

- `core/gold_fact_builder.py`
  - MES reruns now restore CSI-derived `team_size` from the linked `csi_source_row_hash` before clearing MES fields
  - positive-manpower MES rows still override CSI `team_size` when a valid MES match exists
- `tests/test_gold_fact_builder.py`
  - added a regression proving that when a prior MES match disappears, the row falls back to the original CSI roster size instead of losing crew truth

### Phase A validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py core/fact_machine_hour_repair.py tests/test_gold_fact_builder.py tests/test_fact_machine_hour_repair.py
python3 -m unittest tests.test_gold_fact_builder tests.test_fact_machine_hour_repair
```

Result:

- `66` tests passed

## Phase B

### Active DB audit only

The active runtime DB path remained:

- `manufacturing_data.db`

No DB write was warranted in Phase B, so no backup copy was needed.

### Required live SQL audit

Residual Jan-Jun rows still requiring the preprocessor-default `team_size` fallback on the active DB:

```text
2025-01|3945|8|1
2025-02|12577|7|2
2025-03|24328|3|2
2025-04|27449|4|3
2025-05|32117|14|3
2025-06|32883|36|8
```

This was already far smaller than the earlier Task 4M baseline.

### Why no DB write happened

The decision query for the residual set showed:

- every affected row already had `csi_source_row_hash`
- every affected row joined to a CSI event
- none of those CSI rows had positive crew roster evidence
  - `team_leader` null
  - `team_members_raw = []`

Therefore the residual set was not a missed Gold landing from Phase A, and rerunning canonical repair/materialization would not honestly create additional crew truth.

## Phase C

### Real canonical trainer-path dependence

Phase C used the actual canonical trainer path on the active runtime DB through `MLDataPreparer.load_data()` and `get_canonical_retraining_status(...)`, not a hand-written SQL estimate.

Active trainer-path output:

```text
rows after filtering: 132,549
distinct machines after filtering: 76
month coverage: January 2025, February 2025, March 2025, April 2025, May 2025, June 2025
rows using team_size_from_preprocessor_default: 72
distinct machines using team_size_from_preprocessor_default: 16
monthly default breakdown:
  2025-01: 8
  2025-02: 7
  2025-03: 3
  2025-04: 4
  2025-05: 14
  2025-06: 36
rows using team_size_from_manpower: 0
```

This means the residual default-team path now covers about `0.054%` of the filtered canonical trainer rows.

### Policy decision

Task 4N keeps the remaining preprocessor-default `team_size` path as a narrow approved exception.

Reason:

- the real canonical trainer path depends on it for only `72` filtered Jan-Jun rows
- Phase B already proved there is no additional honest upstream crew truth left to land for those rows
- removing the fallback now would change training/inference eligibility semantics for a small but real residual set and would force unnecessary artifact reevaluation work

Task 4N therefore closes with:

- no blind fallback removal
- no fabricated crew data
- no artifact reevaluation
- explicit instrumentation and contract wording so the residual exception is visible

### What changed in Phase C

- `core/ml_trainer.py`
  - added explicit trainer-path `team_size` fallback diagnostics derived from filtered canonical training rows
  - exposed those diagnostics through retraining status and retraining result payloads
- `modules/ml_module.py`
  - surfaced the residual fallback counts in the canonical retraining status section
  - clarified the ML contract wording so the remaining preprocessor-default path is described as a visible exceptional path
- `tests/test_ml_trainer.py`
  - added assertions covering the fallback summary for default-team and manpower-derived rows
- `tests/test_ml_module.py`
  - added status assertions covering the new fallback summary payload

### Phase C validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/ml_trainer.py modules/ml_module.py tests/test_ml_trainer.py tests/test_ml_module.py
python3 -m unittest tests.test_ml_trainer tests.test_ml_module
```

Result:

- `14` tests passed

## Active DB / Artifact State

Task 4N did not mutate the active runtime DB.

Task 4N did not retrain models, did not create `models/task4n_artifacts/`, and did not promote any artifact.

Verified active artifact manifests after closeout:

- active model manifest task tag: `Task 4L`
- active model artifact version: `20260401_000808`
- active preprocessor manifest task tag: `Task 4L`
- active preprocessor artifact version: `20260401_000808`

## Official Closeout

Task 4N passes because:

- the Gold-side rerun inconsistency was fixed and tested
- the active DB residual set was audited directly and proven not to have missed upstream crew truth
- the real canonical trainer path now quantifies the remaining fallback dependence explicitly
- the remaining default-team path is retained narrowly and honestly without forcing unnecessary artifact churn
