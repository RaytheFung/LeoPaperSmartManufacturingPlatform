# Rebuild Roadmap and Editable To-Do List

> Status convention
>
> - `[ ]` not started
> - `[~]` in progress
> - `[x]` done
> - `[!]` blocked / needs clarification

---

## Phase 0 — Repo truth audit and freeze

### Goal
Make sure the live repo structure, import paths, and current execution paths are understood before changes begin.

### Tasks
- [ ] Confirm actual repo tree in the live codebase.
- [ ] Confirm whether the live repo uses `core/`, `core/etl/`, or mixed top-level imports.
- [ ] Record current app entry path and runtime path.
- [ ] Create a safety branch for rebuild work.
- [ ] Mark current user-facing unified-view behavior as `legacy_demo`.
- [ ] Identify all places where synthetic or placeholder data may be returned.

### Deliverables
- repo tree snapshot
- live import-path notes
- list of high-risk modules

### Notes
- The uploaded review snapshot and the live repo are not guaranteed to match exactly.
- Do not start broad rewrites before this phase is completed.

---

## Phase 1 — Machine alias registry

### Goal
Create one explicit, maintainable source of truth for cross-system machine identity.

### Tasks
- [x] Produce `v1_machine_alias_registry.csv`.
- [x] Produce `v1_alias_exceptions.csv`.
- [ ] Create loader for `machine_alias_registry`.
- [ ] Create `resolve_canonical_machine_id()` utility.
- [ ] Create `normalize_machine_family()` utility.
- [ ] Apply explicit exception logic for `035-017` and `035-018`.
- [ ] Mark rows by `join_status` such as `production_joinable`, `energy_only`, `maintenance_only`.

### Deliverables
- working alias-registry loader
- canonical machine ID resolver
- exception handling rules

### Acceptance criteria
- One physical machine resolves to one canonical ID.
- All joins across CSI / MES / Energy / Maintenance use registry logic.
- Alias exceptions are explicit and traceable.

---

## Phase 2 — Bronze ingestion adapters

### Goal
Preserve raw source truth in stable raw tables or equivalent persisted structures.

### Tasks
- [ ] Implement `load_energy_raw()`.
- [ ] Implement `load_csi_raw()`.
- [ ] Implement `load_mes_raw()`.
- [ ] Implement `load_maintenance_raw()`.
- [ ] Preserve `source_file` and ingestion timestamp in every raw layer.
- [ ] Add minimal schema validation and logging.

### Deliverables
- four raw loaders
- ingestion logs
- schema-check notes

### Acceptance criteria
- Apr / May / Jun sample files load without silent column loss.
- Maintenance files load as transaction logs.
- Parsing failures are explicit, not silent.

---

## Phase 3 — Silver normalizers

### Goal
Convert raw source data into canonical source-specific tables without doing full unified attribution yet.

### Tasks
- [ ] Implement `normalize_energy_to_silver()`.
- [ ] Implement `normalize_csi_to_silver()`.
- [ ] Implement `normalize_mes_to_silver()`.
- [ ] Implement `normalize_maintenance_to_silver()`.
- [ ] Parse Energy meter component types such as `main`, `uv`, `ir`, `motor`, `aggregate`.
- [ ] Normalize CSI production / stop / team fields.
- [ ] Normalize MES report / prep / production / manpower fields.
- [ ] Normalize Maintenance asset / work-order / transaction fields.
- [ ] Store parse confidence where needed.

### Deliverables
- `energy_meter_hour`
- `csi_job_event`
- `mes_report_event`
- `maintenance_txn_event`

### Acceptance criteria
- Each Silver table is independently queryable.
- Machine IDs in Silver always resolve through the registry.
- No formal analysis still depends on raw field name ambiguity.

---

## Phase 4 — Gold `fact_machine_hour`

### Goal
Rebuild unified operational truth as one canonical machine-hour fact table.

### Tasks
- [ ] Design hour-bucket generation strategy.
- [ ] Implement state attribution hierarchy:
  - [ ] `maintenance`
  - [ ] `setup_changeover`
  - [ ] `production`
  - [ ] `planned_stop`
  - [ ] `unplanned_stop`
  - [ ] `idle`
- [ ] Implement setup inference from CSI `prep_end_ts - actual_changeover_minutes`.
- [ ] Add fallback from CSI refined/planned duration.
- [ ] Add final fallback from MES `prep_hours`.
- [ ] Store `setup_inference_method` and `setup_confidence`.
- [ ] Reconcile hourly energy attribution totals.
- [ ] Add `source_flags` and `attribution_method`.
- [ ] Disable synthetic fallback in formal paths.

### Deliverables
- `fact_machine_hour`
- attribution audit output
- reconciliation checks

### Acceptance criteria
- No synthetic rows in formal user-facing analysis.
- Reconciled energy attribution per machine-hour.
- Every inferred value has method + confidence.

---

## Phase 5 — Maintenance feature integration

### Goal
Use maintenance data in an FYP-safe way without overclaiming predictive maintenance.

### Tasks
- [ ] Build latest-maintenance-date proxy by machine.
- [ ] Build counts by maintenance type (`PM`, `CM`, `AM`, `EM`, etc.).
- [ ] Build parts-consumption hotspot summaries.
- [ ] Add `hours_since_last_maintenance` and `days_since_last_maintenance` to Gold layer.
- [ ] Add machine maintenance summary table for app consumption.

### Deliverables
- maintenance summary table
- maintenance-age features
- optional component hotspot summary

### Acceptance criteria
- Maintenance enriches analytics and ML context.
- Project does not overclaim downtime-labelled predictive maintenance.

---

## Phase 6 — App stabilization

### Goal
Retarget the app to canonical data layers while minimizing risky UI churn.

### Tasks
- [ ] ETL page reads ingestion + normalization status.
- [ ] Unified View page reads `fact_machine_hour` only.
- [ ] Maintenance page reads maintenance summary + canonical maintenance tables.
- [ ] Optimization page reads canonical Gold data only.
- [ ] ML page reads canonical Gold data only.
- [ ] Remove or clearly isolate legacy demo paths.
- [ ] Add user-facing warnings when data confidence is low.

### Deliverables
- stable app pages reading canonical tables
- legacy/demo isolation notes

### Acceptance criteria
- User-facing outputs are based on canonical data.
- No silent fallback to synthetic data.

---

## Phase 7 — ML stabilization (FYP-safe)

### Goal
Keep the AI element real and defendable without overselling.

### Tasks
- [ ] Retarget training data source to `fact_machine_hour`.
- [ ] Review target definition (`kwh_per_unit` vs contextual/excess-energy framing).
- [ ] Implement time-aware validation.
- [ ] Separate model output from rule-based fallback output.
- [ ] Make confidence logic explicit.
- [ ] Retain machine opportunity ranking.

### Deliverables
- updated ML spec
- revised training pipeline
- evaluation notes

### Acceptance criteria
- ML is grounded in canonical data.
- AI claim is defendable as ML-assisted decision support.

---

## Phase 8 — FYP finish line

### Goal
Ensure the project is runnable, demonstrable, and academically defensible.

### Tasks
- [ ] Verify end-to-end run on sample monthly data.
- [ ] Prepare a clear architecture diagram.
- [ ] Prepare one slide for `why rebuild was necessary`.
- [ ] Prepare one slide for `machine alias governance`.
- [ ] Prepare one slide for `fact_machine_hour` logic.
- [ ] Prepare one slide for `AI element and its real scope`.
- [ ] Prepare a limitations slide.

### Deliverables
- runnable demo flow
- presentation-ready architecture story
- limitations / future work list

### Acceptance criteria
- The project runs.
- The data story is credible.
- The AI story is modest but real.

---

## Current decisions already frozen

- [x] Use Bronze → Silver → Gold architecture.
- [x] Use `machine_alias_registry` as mandatory cross-system join layer.
- [x] Treat current maintenance export as maintenance transaction log first.
- [x] Disable formal reliance on synthetic unified data.
- [x] Keep FYP positioning as ML-assisted decision support, not full factory autonomy.

---

## Open questions to track

- [ ] Confirm final live repo structure under `core/` and `core/etl/`.
- [ ] Confirm whether any existing registry or mapping table already exists in the live repo.
- [ ] Confirm which app pages are currently most demo-critical for final presentation.
- [ ] Confirm whether more months of data will be used for validation.
- [ ] Confirm whether maintenance exports contain hidden useful fields not yet exploited.

