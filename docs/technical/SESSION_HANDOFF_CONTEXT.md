# Session Handoff Context

Use this file to continue the project in a new conversation or to brief Codex / collaborators.

---

## 1. Current project state

This FYP is a smart manufacturing platform built around:
- monthly Excel ingestion;
- ETL over `Energy + CSI + MES + Maintenance`;
- SQLite-backed unified analytics;
- Streamlit decision-support pages;
- ML-assisted efficiency prediction / ranking.

The high-level direction is still valid. The current work is a **controlled rebuild of the data backbone**, not a full product restart.

---

## 2. Why the rebuild is happening

The rebuild was triggered because the current codebase likely contains these trust issues:
- machine IDs are inconsistent across source systems;
- some unified-view paths are not trustworthy enough for formal analysis;
- setup inference is under-specified because raw CSI lacks `準備開始時間`;
- ML credibility depends on better canonical joins first;
- the live repo structure may differ from the uploaded review snapshot.

---

## 3. Frozen decisions

These decisions are already agreed and should be treated as current truth:

1. Keep the product direction.
2. Rebuild the **data backbone first**.
3. Use **Bronze → Silver → Gold** architecture.
4. Use a mandatory **`machine_alias_registry`** for all cross-system joins.
5. Treat the maintenance export as **maintenance transaction / parts log first**, not as a full predictive-maintenance label table.
6. Rebuild the unified layer as **`fact_machine_hour`**.
7. Disable formal reliance on synthetic fallback records.
8. Keep the AI claim modest and real: **ML-assisted decision support**, not full autonomy.

---

## 4. Canonical artifacts already produced

These files exist and should be passed into future work:

- `v1_machine_alias_registry.csv`
- `v1_alias_exceptions.csv`
- `v1_canonical_schema.md`
- `v1_rebuild_blueprint.md`
- `maintenance_initial_findings.md`
- `REBUILD_INTENT_AND_SYSTEM_SPEC.md`
- `REBUILD_ROADMAP_AND_TODO.md`
- `CODEX_TASK_PROMPT_PACK.md`
- `SESSION_HANDOFF_CONTEXT.md`

---

## 5. Most important technical conclusions so far

### Machine identity
- cross-system machine mapping is the first mandatory layer;
- maintenance files provide strong new-code ↔ legacy-code crosswalk evidence;
- known alias exceptions include `035-017` and `035-018`.

### Data architecture
- Bronze preserves raw source truth;
- Silver canonicalizes source-specific events;
- Gold unifies everything into `fact_machine_hour`.

### Unified state model
Priority must be:
1. `maintenance`
2. `setup_changeover`
3. `production`
4. `planned_stop`
5. `unplanned_stop`
6. `idle`

### Setup inference
Raw CSI does not contain `準備開始時間`, so setup start must be inferred from:
- `prep_end_ts - actual_changeover_minutes`
then fallback to other CSI or MES prep fields.

### Maintenance usage
Maintenance exports should first support:
- alias registry enrichment;
- maintenance summary by machine;
- last-maintenance-date proxy;
- maintenance-age features;
- parts hotspot analysis.

### FYP-safe AI scope
Keep these:
- contextual efficiency prediction;
- opportunity ranking;
- ML-assisted recommendations.

Do not overclaim these yet:
- full predictive maintenance;
- production scheduling optimizer;
- enterprise ROI engine.

---

## 6. Recommended next execution order

1. Repo audit and path normalization.
2. `machine_alias_registry` loader and resolver.
3. Bronze raw loaders.
4. Silver normalizers.
5. Gold `fact_machine_hour` builder.
6. Maintenance summary integration.
7. App retargeting to canonical data.
8. ML stabilization.

---

## 7. What to tell Codex

Tell Codex:
- do not do a broad rewrite;
- preserve the product shell;
- prioritize data backbone over UI polish;
- never fabricate formal analysis rows;
- all joins must go through the alias registry;
- all inference must be explicit about method and confidence.

Use `CODEX_TASK_PROMPT_PACK.md` as the instruction source.

---

## 8. If a new chat window is opened

To resume cleanly in a new window:

1. Upload these files:
   - `SESSION_HANDOFF_CONTEXT.md`
   - `REBUILD_INTENT_AND_SYSTEM_SPEC.md`
   - `REBUILD_ROADMAP_AND_TODO.md`
   - `CODEX_TASK_PROMPT_PACK.md`
   - `v1_machine_alias_registry.csv`
   - `v1_alias_exceptions.csv`
   - optionally sample Excel files

2. Start with this message:

```text
This conversation is continuing a controlled rebuild of my smart manufacturing FYP repository.
Please use `SESSION_HANDOFF_CONTEXT.md` as the source of truth for what has already been decided.
Then use `REBUILD_INTENT_AND_SYSTEM_SPEC.md`, `REBUILD_ROADMAP_AND_TODO.md`, and `CODEX_TASK_PROMPT_PACK.md` to continue the rebuild planning and implementation review.
Do not restart the analysis from scratch unless these documents conflict.
```

3. Then continue with the specific next task you want help with.

---

## 9. Current best next step

The best next step is to start Codex on:
1. repo audit;
2. alias registry loader;
3. Bronze/Silver data adapters.

Do not start with UI polish or ambitious ML redesign.

