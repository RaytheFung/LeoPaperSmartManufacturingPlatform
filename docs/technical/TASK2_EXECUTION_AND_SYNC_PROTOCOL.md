# Task 2 Execution and Sync Protocol

## Task 1 verdict

Task 1 repo audit is accepted as a valid first-pass audit.
It stayed within scope, made only one minimal import fix, and confirmed the main architectural risks:
- split unified-view truth across `app.py`, `modules/euvg_module.py`, and `modules/unified_view_module.py`
- synthetic/demo fallback paths still exist in formal analysis flows
- path/import/layout drift exists between live repo structure and prior review snapshot
- maintenance behavior depends partly on hidden DB state
- stale dataset-folder assumptions still exist in scripts

Task 2 should proceed, but only in controlled sub-phases.

---

## Task 2 should be split into two sub-tasks

### Task 2A — path normalization foundation

Goal:
Create a minimal runtime-path and import foundation so later rebuild work does not depend on fragile working-directory assumptions.

In scope:
- one small runtime path helper
- canonical DB path resolver
- canonical dataset-root resolver supporting live names first and legacy names explicitly if needed
- package-qualified imports in touched files only
- no UI rewrite
- no business-logic rewrite
- no schema redesign yet

Out of scope:
- no unified-view rebuild yet
- no ML rewrite
- no maintenance redesign
- no app-page cleanup beyond import/path safety

Deliverables:
- new path helper module
- list of touched files and why
- minimal import/path diff only
- confirmation that app launch and ETL import paths still work

### Task 2B — machine alias registry foundation

Goal:
Introduce the first canonical machine-identity layer without yet rewriting the full ETL or unified-view business logic.

In scope:
- load `v1_machine_alias_registry.csv`
- load `v1_alias_exceptions.csv`
- add a resolver API such as:
  - `normalize_machine_id(raw_id: str) -> str | None`
  - `resolve_canonical_machine_id(raw_id: str, source_system: str) -> dict`
- make resolver evidence-aware where possible
- integrate maintenance-backed alias evidence as seed truth, not predictive logic
- add tests for representative mappings and exception cases

Out of scope:
- do not rewrite `core/etl/mapper.py` aggressively
- do not migrate the full ETL pipeline to the new registry yet
- do not rewrite unified-view attribution yet

Deliverables:
- alias loader/resolver module
- seed file integration path
- tests for normal + exception mappings
- short note on how later ETL/unified-view code should consume the resolver

---

## Codex prompt for Task 2A

```text
Please execute Task 2A only: path normalization foundation.

Source of truth:
- docs/technical/TASK1_REPO_AUDIT.md
- REBUILD_INTENT_AND_SYSTEM_SPEC.md
- REBUILD_ROADMAP_AND_TODO.md
- CODEX_TASK_PROMPT_PACK.md

Objective:
Create a minimal path and import foundation so the rebuild no longer depends on fragile working-directory behavior.

Required work:
1. Add one small runtime path helper for:
   - repo root
   - manufacturing_data.db
   - data/
   - raw dataset root
   - models/
   - etl_outputs/
2. Add a dataset root resolver that supports the live dataset folder names first, and legacy names explicitly if still needed.
3. Standardize imports to package-qualified form (`core.*`, `modules.*`) in touched files only.
4. Remove or reduce ad hoc path mutations only where required for this task.
5. Keep all business logic and UI behavior unchanged.

Constraints:
- Do not rewrite unified-view logic.
- Do not rewrite ML logic.
- Do not redesign schemas.
- Do not do broad cleanup outside what is required for path safety.
- Keep edits minimal and explain each touched file.

Deliverables:
- changed file list
- reason for each change
- brief runtime validation result
- any remaining path risks not fixed yet
```

---

## Codex prompt for Task 2B

```text
Please execute Task 2B only: machine alias registry foundation.

Source of truth:
- docs/technical/TASK1_REPO_AUDIT.md
- REBUILD_INTENT_AND_SYSTEM_SPEC.md
- REBUILD_ROADMAP_AND_TODO.md
- CODEX_TASK_PROMPT_PACK.md
- v1_machine_alias_registry.csv
- v1_alias_exceptions.csv
- maintenance_initial_findings.md

Objective:
Introduce the first canonical machine-identity layer without rewriting the full ETL or unified-view logic yet.

Required work:
1. Add a machine alias registry loader using `v1_machine_alias_registry.csv`.
2. Add exception handling using `v1_alias_exceptions.csv`.
3. Implement a resolver API, for example:
   - normalize_machine_id(raw_id: str) -> str | None
   - resolve_canonical_machine_id(raw_id: str, source_system: str) -> dict
4. Ensure the resolver can handle at least:
   - CSI-style IDs
   - MES resource IDs
   - Energy label extracted IDs
   - maintenance-backed alias cases
5. Add tests for representative normal cases and exception cases, especially the `035-017` and `035-018` family inconsistencies.
6. Do not aggressively rewrite existing mapper logic yet; wrap or isolate where needed.

Constraints:
- Do not yet migrate all ETL writes to the resolver.
- Do not rebuild unified-view attribution yet.
- Do not change UI behavior.
- Keep the change reviewable and modular.

Deliverables:
- changed file list
- new files added
- tests added
- clear note on how Task 3 should consume this alias layer
```

---

## Sync protocol between Codex and this review thread

Do **not** replace the whole project in this chat after every Codex run.
Use checkpoint-based review.

### After each Codex task, collect and upload only:
1. the task report markdown
2. the terminal summary / final reply
3. the changed file list
4. the changed files themselves
5. if possible, a unified diff patch (`git diff` or equivalent)

### Replace broader snapshots only when:
- a task restructures imports across many files
- a package is moved or renamed
- more than about 10 files changed in a tightly coupled way

### Recommended branch / checkpoint rule
- one Codex task = one review checkpoint
- do not start the next task until the current checkpoint is reviewed
- keep each task isolated and reversible

---

## What the next review needs from Codex

After Task 2A finishes, upload:
- the task report
- changed files
- the new path helper module
- any touched import-bearing files
- the diff summary

After Task 2B finishes, upload:
- the task report
- changed files
- the alias loader/resolver module
- tests added
- the diff summary

