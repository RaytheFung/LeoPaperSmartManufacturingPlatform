# Task16F Integrated Internal Landing Rehearsal Report

## 1. accepted baseline used

- Accepted live baseline remained:
  - `Task14F passed`
  - `Task15A passed`
  - `Task15C passed`
  - `Task15E passed`
  - `Task15F passed`
  - `Task15G passed`
  - `Task15H passed`
  - `Task15I closed Task15 and allowed Task16 entry`
  - `Task16A passed`
  - `Task16B passed`
  - `Task16C passed`
  - `Task16D passed`
  - `Task16E passed`
- Accepted live DB/runtime baseline remained:
  - repo-local runtime DB path = `manufacturing_data.db`
  - canonical coverage = `January 2025` -> `February 2026`
  - `fact_machine_hour` rows = `879,978`
- Accepted live artifact baseline remained:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
- Although the repo worktree was already dirty when Task16F started, the on-disk live fingerprints matched the accepted Task15A/Task16E anchor values exactly at task start:
  - DB SHA1 = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - model SHA-256 = `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - preprocessor SHA-256 = `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - model provenance SHA-256 = `d23648bb1fb24b9e830ba6586df5ed4faf02645522b085293e968f3a76774ff5`
  - preprocessor provenance SHA-256 = `66cbdb505ef3c577a0523efabf8881d6f6b104470fc17ff203f44f520d3a7611`

## 2. task boundary kept

- Task16F stayed narrow and read-only:
  - no DB writes
  - no ETL/materialization rerun
  - no retraining
  - no artifact promotion
  - no predictor-contract broadening
  - no good_qty semantic change
  - no blocked-logic change
  - no Task15 shadow/remediation reopening
- The only code artifact added for this task was:
  - `scripts/run_task16f_integrated_internal_landing_rehearsal.py`
- The rehearsal used `pilot_review` as the main integrated runtime posture while still verifying route exposure contracts separately for:
  - `standard`
  - `demo_readonly`
  - `pilot_review`

## 3. exact commands and diagnostics run

- Exact `.conda311` commands used:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile scripts/run_task16f_integrated_internal_landing_rehearsal.py`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python scripts/run_task16f_integrated_internal_landing_rehearsal.py`
- Exact read-only SQLite probes used:
  - `sqlite3 -readonly manufacturing_data.db "SELECT COUNT(*) AS fact_rows, MIN(substr(hour_ts, 1, 7)) AS min_month, MAX(substr(hour_ts, 1, 7)) AS max_month FROM fact_machine_hour; SELECT COUNT(*) AS feb_2026_rows FROM fact_machine_hour WHERE hour_ts >= '2026-02-01T00:00:00' AND hour_ts < '2026-03-01T00:00:00';"`
  - inside the Task16F script:
    - `SELECT COUNT(*), MIN(substr(hour_ts, 1, 7)), MAX(substr(hour_ts, 1, 7)) FROM fact_machine_hour`
    - `SELECT COUNT(*) FROM fact_machine_hour WHERE hour_ts >= ? AND hour_ts < ?`
    - params = `('2026-02-01T00:00:00', '2026-03-01T00:00:00')`
- Exact month used for the real-data rehearsal:
  - `February 2026`
- Exact route/module checks run:
  - `app.py` import boundary with blocked legacy loader imports
  - `modules.etl_module` import
  - `modules.unified_view_module` import
  - `modules.energy_module` import plus `build_energy_route_snapshot(...)`
  - `modules.optimization_module` import plus `build_schedule_tab_payload(...)` and `build_team_insights_tab_payload(...)`
  - `modules.ml_module` import plus `CanonicalMLReader` + active `MLPredictor`
  - `modules.maintenance_module` import plus `MaintenanceEvidenceReader` coverage/evidence read
  - `modules.experimental_intelligence_lab_module` import plus `build_experimental_lab_route_snapshot(...)` in `pilot_review`

## 4. integrated landing rehearsal result

- Route visibility by runtime mode:
  - `standard` visible routes = defended core + `🧪 Experimental Intelligence Lab`
  - `demo_readonly` visible routes = defended core only
  - `pilot_review` visible routes = defended core + `🧪 Experimental Intelligence Lab`
  - `loader_dependent_visible_pages = []` in all three modes
- `🔄 ETL Pipeline`
  - module import passed
  - `pilot_review` route exposure passed
  - read-only source-availability contract passed for `February 2026`
  - family status = `energy partial / csi partial / mes partial`
  - backfill readiness = `ready_with_flags`
  - missing source files = `none`
  - honest limitation kept:
    - the ETL upload/process/backfill path was not exercised because it mutates the DB
- `📊 Canonical Operations Overview`
  - `CanonicalGoldReader` month enumeration passed
  - available canonical months = `14`
  - real `February 2026` slice load passed
  - `rows_loaded = 57,792`
  - `distinct_machines = 86`
  - weighted `kWh / good unit = 0.009043242235796408`
- `⚡ Energy Analysis`
  - module import passed
  - route-aligned snapshot build passed on real `February 2026` canonical data
  - `rows_loaded = 57,792`
  - `total_energy_kwh = 640,101.3193`
  - weighted `kWh / good unit = 0.009043242235796408`
  - fallback proof:
    - `fallback_used = false`
    - legacy EUVG / `unified_view` data fallback not used
- `🎯 Operational Decision Support`
  - module import passed
  - real `February 2026` machine summary passed
  - `machine_summary_rows = 86`
  - top machine = `024-003`
  - route-aligned scheduling payload passed:
    - `schedule_rows = 24`
    - `blocked = false`
  - route-aligned team payload passed:
    - `team_rows = 234`
    - `blocked = false`
- `🤖 Efficiency Prediction & Governance`
  - module import passed
  - active Task14F artifacts loaded successfully
  - real `February 2026` canonical ML input/readiness slice passed
  - `input_rows = 57,792`
  - `candidate_rows = 76`
  - `prediction_rows = 76`
  - `blocked_after_predictor_gate_rows = 0`
  - predictor status:
    - `loaded_model = true`
    - `loaded_preprocessor = true`
    - `canonical_inference_enabled = true`
- `🔧 Maintenance`
  - module import passed
  - read-only coverage snapshot passed:
    - `records_stored = 14,378`
    - `integrated_machine_count = 61`
    - `months_covered = 20`
    - latest stored maintenance month = `August 2025`
    - latest stored maintenance event = `2025-08-14 17:27`
  - one real selected-month evidence read passed through the read-only helper:
    - selected machine = `024-003`
    - `all_time_event_count = 14`
    - `recent_window_event_count = 10`
    - latest linked event = `2025-07-26 14:01`
  - honest limitation kept:
    - upload/integration controls were not exercised because they mutate maintenance tables
- `🧪 Experimental Intelligence Lab`
  - module import passed
  - route exposure in `pilot_review` passed
  - real selected-month route snapshot passed on `February 2026`
  - scheduling prototype passed:
    - `queue_rows = 3`
    - `assigned_rows = 3`
    - `naive_rows = 3`
    - provenance = `Real-seeded synthetic queue`
  - maintenance prototype passed:
    - `prototype_mode = Weak-label model`
    - `risk_rows = 86`
    - selected machine = `166-002`
    - maintenance-event horizon end = `2025-08-14`
  - explicit active live binding proof passed:
    - `Task 14F / 20260419_181842 / random_forest`
    - predictor instantiated from explicit repo-local live paths
    - model + preprocessor both loaded successfully

## 5. blocker map

- Hard blockers before internal use testing:
  - none
- Soft / non-blocking debt:
  - the ETL upload/process/backfill path was intentionally not rehearsed because Task16F had to remain read-only
  - the Maintenance upload/integration controls were intentionally not rehearsed because Task16F had to remain read-only
  - the integrated rehearsal proves route-aligned read paths and shell contracts, but it does not replace a human live Streamlit interaction pass
- Explicit non-defended prototype limits:
  - experimental scheduling remains a read-only prototype, not a live scheduling engine or solver
  - experimental scheduling default provenance remains `Real-seeded synthetic queue` unless a narrow real-input pilot queue is uploaded
  - experimental maintenance remains a weak-label-model-or-fallback evidence prototype, not a production predictive-maintenance recommendation engine
  - the experimental maintenance-event observation horizon remains bounded by stored maintenance records through `2025-08-14`

## 6. internal use-test handoff

- Recommended runtime mode:
  - `pilot_review`
- Exact launch command:
  - `SMART_MFG_RUNTIME_MODE=pilot_review ./.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true`
- Route order:
  - `🔄 ETL Pipeline`
  - `📊 Canonical Operations Overview`
  - `⚡ Energy Analysis`
  - `🎯 Operational Decision Support`
  - `🤖 Efficiency Prediction & Governance`
  - `🔧 Maintenance`
  - `🧪 Experimental Intelligence Lab`
- Selected month for consistency:
  - `February 2026`
- Concise manual verification checklist:
  - `🔄 ETL Pipeline`: confirm `pilot_review` hides upload/process controls, the Jul 2025 -> Mar 2026 source-availability table renders, and no visible action offers DB mutation
  - `📊 Canonical Operations Overview`: keep `February 2026` selected and confirm real canonical cards/table render from `fact_machine_hour`
  - `⚡ Energy Analysis`: keep `February 2026` selected and confirm canonical KPI, attribution coverage, and machine-attention views render without EUVG / `unified_view` fallback messaging
  - `🎯 Operational Decision Support`: keep `February 2026` selected and confirm worklist + schedule payload + team payload render as canonical read-only decision support
  - `🤖 Efficiency Prediction & Governance`: keep `February 2026` selected and confirm active saved-model status, prediction rows, blocked-reason surfaces, and Scenario Lab remain read-only
  - `🔧 Maintenance`: confirm coverage cards, machine evidence lookup, and supporting maintenance-age energy context render while upload/integration controls stay hidden
  - `🧪 Experimental Intelligence Lab`: keep `February 2026` selected and confirm route snapshot, scheduling provenance, maintenance prototype mode, and export/provenance messaging all remain explicit and non-defended
- Boundaries that must stay visible to reviewers:
  - runtime DB path remains repo-local `manufacturing_data.db`
  - active saved artifact bundle remains `Task 14F / 20260419_181842 / random_forest`
  - the experimental lane remains read-only and non-defended
  - experimental scheduling provenance must stay explicit
  - the late-anchor maintenance-event horizon note must stay explicit
- What must **not** be claimed during the internal test:
  - no live solver or production scheduling engine claim
  - no production predictive-maintenance claim
  - no claim that `pilot_review` rehearses ETL processing, DB writes, retraining, or artifact promotion
  - no claim that experimental outputs are defended production truth

## 7. live DB / live artifact safety

- Repo-local DB contents remained untouched.
- No write-capable SQL path was executed.
- No ETL/materialization path was executed.
- No retraining path was executed.
- No artifact promotion path was executed.
- Before/after fingerprints remained unchanged for:
  - `manufacturing_data.db`
  - `models/production_efficiency_model.pkl`
  - `models/production_preprocessor.pkl`
  - `models/production_efficiency_model.provenance.json`
  - `models/production_preprocessor.provenance.json`

## 8. closeout decision

- Result: **Task16F passed**
- Why it passed:
  - the full internal landing surface was rehearsed coherently on real `February 2026` data
  - the defended-core shell remained coherent across `standard`, `demo_readonly`, and `pilot_review`
  - the experimental flagship lane stayed included while remaining explicit and non-defended
  - no hard blockers were found before whole-platform internal use testing
  - DB and live artifacts stayed unchanged throughout the rehearsal
- Explicit next-step decision:
  - implementation should pause now and whole-platform internal use testing should begin in `pilot_review`
