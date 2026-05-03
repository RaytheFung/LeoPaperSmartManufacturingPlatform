# Task15A Runtime DB Path Stabilization Report

## 1. accepted baseline used

- Accepted baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
  - `Task13I`
  - `Task14A`
  - `Task14B`
  - `Task14C`
  - `Task14F`
- Repo-local shared DB expected at task start:
  - path = `manufacturing_data.db`
  - SHA1 = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - `fact_machine_hour` rows = `879978`
  - month range = `2025-01` -> `2026-02`
- Live artifacts remained the accepted Task14F bundle throughout Task15A:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`

## 2. exact repo-local DB path probes run

- Raw repo-local SQLite probe:
  - `sqlite3 manufacturing_data.db "select count(*) as rows, min(substr(hour_ts,1,7)) as min_month, max(substr(hour_ts,1,7)) as max_month from fact_machine_hour;"`
- Repo-local canonical Gold probe:
  - `./.conda311/bin/python -c "... CanonicalGoldReader(db_path=Path('manufacturing_data.db').resolve()).get_available_months(); ... read_month_page_dataframe('February 2026') ..."`
- Repo-local direct predictor + canonical ML + canonical Optimization probe:
  - `./.conda311/bin/python -c "... CanonicalMLReader(db_path=db_path) ... MLPredictor() ... CanonicalOptimizationReader(db_path=db_path) ..."`
- Default no-override runtime-path probe:
  - `./.conda311/bin/python -c "... CanonicalGoldReader(); CanonicalMLReader(); CanonicalOptimizationReader(); MLPredictor() ..."`
- DB / artifact safety fingerprints:
  - `stat -f 'mtime=%m size=%z inode=%i' manufacturing_data.db`
  - `./.conda311/bin/python -c "... hashlib.sha1(manufacturing_data.db) ..."`
  - `./.conda311/bin/python -c "... hashlib.sha256(models/production_*) ..."`

## 3. repo-local path result

- Result: **healthy**
- SQLite opened the repo-local DB cleanly.
- Repo-local DB direct facts matched the accepted Task14F state exactly:
  - `fact_machine_hour` rows = `879978`
  - month range = `2025-01` -> `2026-02`
  - SHA1 = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
- `CanonicalGoldReader` read the repo-local DB directly and exposed all `14` supported months from `January 2025` through `February 2026`.
- `CanonicalGoldReader.read_month_page_dataframe('February 2026')` returned `57792` page rows on the repo-local DB.
- `CanonicalMLReader` built the supported post-June month `February 2026` directly from the repo-local DB:
  - input rows = `57792`
  - latest-machine candidate rows = `76`
  - prediction rows = `76`
  - blocked prediction rows after predictor gate = `0`
- `CanonicalOptimizationReader` read the supported post-June month `February 2026` directly from the repo-local DB:
  - machine summary rows = `86`
  - top ranked machine = `024-003`
- Default no-override reader usage also resolved the same repo-local DB successfully:
  - latest month = `February 2026`
  - month count = `14`
  - default-path ML input rows = `57792`
  - default-path ML prediction rows = `76`
  - default-path Optimization machine rows = `86`
- Conclusion:
  - the repo-local DB path is readable and stable for normal runtime use
  - the Task14F mirror is no longer required for honest normal-runtime reads

## 4. runtime hardening added (if any)

- No runtime code-path change was required.
- No DB-path override helper, env var, or mirror fallback was added.
- Added one short explicit note:
  - `docs/technical/TASK15A_RUNTIME_PATH_NOTES.md`
- That note makes the accepted default runtime DB path explicit:
  - normal runtime reads the repo-local `manufacturing_data.db`
  - the Task14F mirror remains historical validation/troubleshooting support only

## 5. default runtime smoke result

- Direct predictor smoke on the repo-local DB passed:
  - sample machine = `024-058`
  - sample hour = `2026-02-01T00:00:00`
  - sample month = `February 2026`
  - `source = model`
  - predicted efficiency = `0.016713657957883175`
  - confidence = `0.7081282609418037`
- ML route-adjacent smoke on the repo-local DB passed:
  - canonical rows loaded = `57792`
  - latest-machine candidates = `76`
  - prediction rows = `76`
  - blocked prediction rows after predictor gate = `0`
- Optimization route-adjacent smoke on the repo-local DB passed:
  - machine summary rows = `86`
  - preview-capable month slice remained readable
  - top machine = `024-003`
- Default runtime proof boundary used the real routed helper chain with no DB override:
  - `CanonicalGoldReader()`
  - `CanonicalMLReader()`
  - `CanonicalOptimizationReader()`
  - `MLPredictor()`
- Result:
  - default runtime DB-path behavior is explicit and reliable without a mirror path

## 6. live DB / live artifact safety

- Repo-local DB contents remained untouched:
  - pre-task accepted SHA1 = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - post-probe SHA1 = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - pre/post file stat remained `mtime=1776434362 size=7226900480 inode=12554300`
- No write-capable SQL path was executed.
- No ETL/materialization path was executed.
- No canonical semantics changed.
- No blocked-row rules changed.
- Live Task14F artifacts remained unchanged:
  - model SHA-256 = `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - preprocessor SHA-256 = `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - model provenance SHA-256 = `d23648bb1fb24b9e830ba6586df5ed4faf02645522b085293e968f3a76774ff5`
  - preprocessor provenance SHA-256 = `66cbdb505ef3c577a0523efabf8881d6f6b104470fc17ff203f44f520d3a7611`
- Mirror-path conclusion after Task15A:
  - mirror path is not needed for normal runtime anymore
  - mirror copies may remain only as historical validation or optional troubleshooting support

## 7. remaining limitations

- Task15A was intentionally read-only; it did not run ETL/materialization or retraining.
- The pass boundary here is repo-local read stability, not a fresh artifact reevaluation.
- Heavy full-shell Streamlit harnesses remain slower/noisier than the narrow read-only probes used here; startup logs currently emit non-blocking warnings from obsolete client config keys in `.streamlit/config.toml`.
- March 2026 remains out of scope.
- Post-June ML readiness limits still remain a separate topic from runtime DB-path health.

## 8. recommended next step after Task15A

- No further runtime DB-path stabilization work is required.
- If a later micro-cleanup is desired, keep it separate from Task15A:
  - optionally remove the obsolete non-blocking Streamlit client-config warnings
  - or continue a separate ML-readiness/artifact-governance follow-up
- Do not reopen DB content changes, ETL/materialization, retraining, or artifact promotion in that later cleanup.
