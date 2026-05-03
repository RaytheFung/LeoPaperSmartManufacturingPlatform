# Codex Task Prompt Pack

This file contains the exact task prompts to drive Codex through the rebuild in a controlled, low-risk way.

---

## 0. What to give Codex before any task

Give Codex these files and context first:

### Must provide
- the live repo itself;
- `REBUILD_INTENT_AND_SYSTEM_SPEC.md`;
- `REBUILD_ROADMAP_AND_TODO.md`;
- `v1_machine_alias_registry.csv`;
- `v1_alias_exceptions.csv`;
- `v1_canonical_schema.md`;
- `v1_rebuild_blueprint.md`;
- `maintenance_initial_findings.md`.

### Strongly recommended
- sample raw files for Apr / May / Jun:
  - Energy Excel files;
  - CSI Excel files;
  - MES Excel files;
  - Maintenance Excel files.

### Important note to tell Codex
The uploaded review snapshot may not match the live repo exactly. The live repo appears to contain `core/` and `core/etl/`, so Codex must inspect the actual tree first before editing imports or module paths.

---

## Global operating rules for Codex

Paste this before task prompts if needed:

```text
You are editing a smart manufacturing FYP repository. Do not do a broad rewrite. Use a controlled rebuild approach. Preserve the product shell and prioritize the data backbone.

Hard rules:
1. Audit the actual live repo structure first; do not assume the uploaded review snapshot is identical.
2. Do not invent new business facts or silently fabricate fallback data for formal analytics.
3. If a value must be inferred, store a method and confidence field whenever reasonable.
4. Do not touch UI styling or broad Streamlit layout unless the task explicitly asks for it.
5. Do not redesign scheduling or predictive maintenance into ambitious versions right now.
6. Prefer small, reviewable commits and explicit diffs.
7. Summarize exactly which files were changed, why they were changed, and what still remains risky.
8. If you find conflicting implementations, isolate legacy/demo paths instead of deleting everything blindly.
9. Keep all changes aligned to Bronze → Silver → Gold architecture and machine_alias_registry governance.
10. If data truth is uncertain, fail clearly or mark low confidence; do not return fake success.
```

---

## Task 1 — Repo audit and structure truth

### Prompt
```text
Audit the actual live repo structure before making changes.

Context:
- The design direction is a controlled rebuild of the data backbone for a smart manufacturing FYP.
- The review snapshot showed top-level modules like `app.py`, `etl_module.py`, `unified_view_module.py`, `ml_trainer.py`, `ml_predictor.py`, etc.
- A later screenshot of the live repo shows a `core/` directory and a `core/etl/` folder, so the live repo structure may differ from the review snapshot.

Your job:
1. Inspect the real repo tree.
2. Identify the actual runtime entry points.
3. Identify where ETL, unified view, ML, maintenance, and app orchestration really live.
4. Identify conflicting import paths or duplicate module implementations.
5. Produce a concise audit note:
   - actual repo structure;
   - high-risk modules;
   - duplicate or stale code paths;
   - recommended minimal path normalization plan.

Constraints:
- Do not start rewriting business logic yet.
- Do not change UI.
- Make only minimal edits if absolutely required to fix broken imports discovered during the audit.

Deliverable:
- a markdown audit summary in the repo;
- optional tiny import fixes only if clearly necessary.
```

---

## Task 2 — Machine alias registry loader and resolver

### Prompt
```text
Implement the canonical machine identity layer first.

Inputs available:
- `v1_machine_alias_registry.csv`
- `v1_alias_exceptions.csv`
- `REBUILD_INTENT_AND_SYSTEM_SPEC.md`
- `REBUILD_ROADMAP_AND_TODO.md`

Your job:
1. Create a durable loader for `machine_alias_registry`.
2. Implement a reusable resolver function such as `resolve_canonical_machine_id()`.
3. Implement explicit exception handling from `v1_alias_exceptions.csv`.
4. Make the resolver usable by Energy, CSI, MES, and Maintenance normalization code.
5. Preserve evidence, confidence, and join status from the registry.

Constraints:
- Do not hardcode one-off regex rules throughout the codebase; centralize identity logic.
- Do not yet rewrite front-end modules.
- Keep the API of the resolver simple and testable.

Acceptance criteria:
- Given any CSI machine ID, MES resource ID, maintenance asset ID / legacy ID, or Energy meter label, the resolver can return a canonical machine ID or `None` with a clear reason.
- Known exceptions like `035-017` and `035-018` are handled explicitly.

Deliverables:
- registry loader module or utility;
- canonical resolver utility;
- basic tests or validation examples if the repo supports tests.
```

---

## Task 3 — Bronze raw ingestion adapters

### Prompt
```text
Build raw ingestion adapters for the four source families.

Goal:
Preserve source truth before business reinterpretation.

Sources:
- Energy Excel
- CSI Excel
- MES Excel
- Maintenance Excel

Your job:
1. Implement `load_energy_raw()`.
2. Implement `load_csi_raw()`.
3. Implement `load_mes_raw()`.
4. Implement `load_maintenance_raw()`.
5. Preserve `source_file` and ingestion timestamp.
6. Add basic schema validation and parsing logs.

Constraints:
- Do not do full unified attribution in this task.
- Do not silently drop columns.
- If headers require offset handling, make it explicit in code.
- Keep raw-layer functions pure or nearly pure where practical.

Acceptance criteria:
- Raw Apr / May / Jun files can be loaded consistently.
- Raw maintenance files are treated as transaction logs, not one-row-one-event assumptions.
- Loader failures are explicit and logged.

Deliverables:
- loader functions;
- a short note about raw schema assumptions;
- minimal tests or reproducible examples if possible.
```

---

## Task 4 — Silver normalizers

### Prompt
```text
Normalize raw source data into canonical Silver tables.

Goal:
Create source-specific canonical tables before rebuilding the Gold unified fact table.

Use these target contracts:
- `energy_meter_hour`
- `csi_job_event`
- `mes_report_event`
- `maintenance_txn_event`

Refer to:
- `v1_canonical_schema.md`
- `REBUILD_INTENT_AND_SYSTEM_SPEC.md`

Your job:
1. Implement `normalize_energy_to_silver()`.
2. Implement `normalize_csi_to_silver()`.
3. Implement `normalize_mes_to_silver()`.
4. Implement `normalize_maintenance_to_silver()`.
5. Resolve machine identity through the alias registry only.
6. Parse Energy meter labels into components like `main`, `uv`, `ir`, `motor`, `aggregate`.
7. Preserve source-file traceability.

Constraints:
- Do not yet build `fact_machine_hour` in this task.
- Do not silently coerce ambiguous fields without notes.
- Where parsing is heuristic, add a confidence signal.

Acceptance criteria:
- Each Silver table is queryable independently.
- Machine IDs are canonicalized consistently.
- Energy data does not naively double-count total + component meters.

Deliverables:
- Silver normalizer code;
- a short field-mapping note.
```

---

## Task 5 — Gold `fact_machine_hour` rebuild

### Prompt
```text
Rebuild the unified operational fact table as `fact_machine_hour`.

Goal:
Replace fragile unified-view logic with a formal canonical machine-hour fact table.

Formal state priority:
1. maintenance
2. setup_changeover
3. production
4. planned_stop
5. unplanned_stop
6. idle

Critical rule:
Raw CSI does not contain `準備開始時間`, so setup start must be inferred.
Preferred logic:
- `setup_start_ts = prep_end_ts - actual_changeover_minutes`
Fallbacks:
- CSI refined/planned changeover duration
- MES `prep_hours`
Every inferred setup window must store method + confidence.

Your job:
1. Build hour buckets per canonical machine.
2. Attribute Energy, CSI, MES, and Maintenance signals into one Gold table.
3. Store `machine_state`, `state_confidence`, `source_flags`, `attribution_method`.
4. Reconcile attributed hourly energy totals to total hourly energy.
5. Explicitly disable synthetic fallback in formal paths.

Constraints:
- Do not fabricate rows to make the app look complete.
- If data is missing, keep the record honest and low-confidence.
- Keep the implementation modular enough that app modules can consume it later.

Acceptance criteria:
- `fact_machine_hour` exists and is queryable.
- Energy attribution reconciles.
- All inferred setup windows are traceable.
- No synthetic formal analytics path remains.

Deliverables:
- Gold builder code;
- reconciliation / audit summary;
- notes on unresolved uncertainty.
```

---

## Task 6 — App retargeting to canonical data

### Prompt
```text
Retarget the application to canonical data layers with minimal UI churn.

Goal:
Make the app consume canonical data instead of fragile or legacy paths.

Target behavior:
- ETL page -> ingestion status + normalization status + registry status
- Unified View page -> `fact_machine_hour`
- Maintenance page -> maintenance summary derived from canonical layers
- Optimization / ML pages -> consume `fact_machine_hour` only

Your job:
1. Identify which existing app paths should be treated as legacy/demo.
2. Wire the app to canonical Bronze/Silver/Gold outputs.
3. Add warnings or guardrails when confidence is low.
4. Keep visible behavior stable where possible.

Constraints:
- Do not redesign the entire Streamlit UI.
- Do not spend time polishing visuals in this task.
- Prefer isolating legacy paths over deleting large blocks blindly.

Acceptance criteria:
- The main pages work from canonical data.
- The app no longer silently relies on synthetic unified data.
- Users can see ingestion / confidence / status signals.

Deliverables:
- app wiring changes;
- note describing which legacy paths remain and why.
```

---

## Task 7 — FYP-safe ML stabilization

### Prompt
```text
Stabilize the ML layer after canonical data is in place.

Goal:
Keep the AI element real, modest, and defensible for an FYP.

Desired ML positioning:
- contextual efficiency regression;
- machine opportunity ranking;
- excess-energy style flagging;
- ML-assisted recommendation.

Your job:
1. Make training consume canonical Gold-layer data.
2. Review whether the current target should remain `kwh_per_unit` or be reframed as contextual/excess energy.
3. Implement time-aware validation if feasible in the existing repo architecture.
4. Separate true model outputs from rule-based fallback outputs.
5. Make confidence logic explicit and honest.

Constraints:
- Do not overclaim predictive maintenance.
- Do not turn this into a scheduling optimizer project.
- Keep the scope FYP-safe and demonstrable.

Acceptance criteria:
- ML uses canonical data.
- Evaluation is more defensible than random-split-only logic.
- The final app story remains ML-assisted decision support.

Deliverables:
- ML pipeline updates;
- evaluation notes;
- short note on what is still heuristic.
```

