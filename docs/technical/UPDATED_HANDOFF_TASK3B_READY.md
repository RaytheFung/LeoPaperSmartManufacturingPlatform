# Controlled Rebuild Handoff — Status after Task 3B1a reconcile

## Project identity
This is a controlled rebuild of a smart manufacturing FYP repository.
Primary goal: preserve real-data backbone (CSI + MES + hourly Energy + Maintenance) and build a defendable Smart Manufacturing DSS with ML-assisted analysis.
Secondary goal: later add a clearly-labeled Scenario Mode for demo/what-if capability.

## Current approved status
- Task 1 repo audit: passed
- Task 2A path normalization foundation: passed
- Task 2B machine alias registry foundation: passed
- Task 3A consume alias registry at raw-to-silver boundary: passed
- Task 3B1 Bronze canonical raw tables foundation: passed with follow-up
- Task 3B1a Bronze reconcile/stability patch: passed
- Task 3B2: NOT started yet

## Key technical decisions already frozen
1. Real Data Mode is the main line; Scenario Mode is secondary and comes later.
2. Hourly energy is the canonical backbone for smart analysis and ML.
3. Daily energy reports are supplementary only (trend/reconciliation/executive view), not a replacement for hourly.
4. Tariff bucket aggregate energy files are a separate source family and must not be merged into `raw_energy_hourly` or `energy_meter_hour`.
5. Maintenance stays as transaction/event records for now, not predictive labels.
6. We are doing controlled rebuild, not broad rewrite.

## Why hourly energy remains required
- The rebuild is centered on machine-hour analysis (`raw_energy_hourly` -> `energy_meter_hour` -> later `fact_machine_hour`).
- CSI and MES are event/report oriented; hourly energy is what lets us align energy with setup/production/idle/maintenance windows.
- Daily energy can support coarse trend dashboards and reconciliation, but it weakens event-level attribution and ML usefulness.
- Since new hourly data can be retrieved, do NOT downgrade the backbone to daily.

## Newly observed source families
### Already supported/expected
- Hourly energy report family (old existing files)
- CSI monthly family
- MES monthly family
- Maintenance transaction family

### Newly observed / pending handling
- Daily energy report family (`能耗、費用報表-...`) — useful, but supplementary only
- Energy tariff aggregate family (`用電原始數據抽取表格_...`) — separate source family, not for hourly backbone
- CSI 2026 `.xls` files with slight schema drift (new field: `心電圖轉版次數`) — needs explicit `.xls` support and schema registration
- Long-range MES file for 2025-03 to 2026-02 — same MES family, useful for later ingestion

## Important outcome from Task 3B1a
Bronze hash stability issue was fixed:
- `source_row_hash` now depends only on raw-source truth
- derived mapping fields are excluded from the hash input
- regression tests were added for stable hash, upsert behavior, and MES raw-field preference/fallback behavior

## Current recommendation
### Do now
- Commit Task 3B1a
- Wait for the correct new hourly energy file sample tomorrow
- Before Task 3B2, do a quick source-family/schema sanity check with one recent hourly energy file plus matching CSI/MES sample if possible

### Do not do yet
- Do not start Task 3B2 before checking the new hourly energy sample
- Do not merge daily energy or tariff aggregate energy into hourly Silver tables
- Do not start Task 3C yet

## Next intended step
### Preferred next step
Perform a quick drift/source-family check on:
- one recent hourly energy file (newly retrieved)
- one matching recent CSI file
- one matching recent MES file

If that check passes, then run Task 3B2:
- build Silver normalized tables from Bronze
- keep energy Silver limited to supported hourly family only
- explicitly register supported vs pending source families

## Files that are especially important for continuity
Attach these to the next chat window if you want seamless takeover:
1. `UPDATED_HANDOFF_TASK3B_READY.md`
2. `SESSION_HANDOFF_CONTEXT.md`
3. `REBUILD_INTENT_AND_SYSTEM_SPEC.md`
4. `REBUILD_ROADMAP_AND_TODO.md`
5. `TASK1_REPO_AUDIT.md`
6. `TASK2A_IMPLEMENTATION_REPORT.md`
7. `TASK2_EXECUTION_AND_SYNC_PROTOCOL.md`
8. `REAL_DATA_PLUS_SCENARIO_MODE_STRATEGY.md`
9. `TASK3B1_BRONZE_IMPLEMENTATION_REPORT.md`
10. `TASK3B1A_RECONCILE_REPORT.md`
11. `v1_canonical_schema.md`
12. `core/machine_alias_registry.py` (or exported copy)
13. `tests/test_machine_alias_registry.py` (or exported copy)
14. latest exported `bronze_raw_store.py`
15. latest exported `test_bronze_raw_store.py`
16. one recent correct hourly energy sample
17. optional: one recent CSI sample + one recent MES sample

## Suggested opening message for a new chat window
This conversation is continuing a controlled rebuild of my smart manufacturing FYP repository.
Please use `UPDATED_HANDOFF_TASK3B_READY.md` as the current source of truth.
Also use the attached rebuild documents under docs/technical / exported markdown files.
Current approved status:
- Task 2A passed
- Task 2B passed
- Task 3A passed
- Task 3B1 passed
- Task 3B1a reconcile passed
- Task 3B2 has NOT started yet
Important decision: hourly energy remains the canonical backbone; daily energy is supplementary only.
Please do not restart analysis from scratch unless the attached documents conflict.

## Suggested opening message for a new Codex thread
Read these first before changing anything:
- UPDATED_HANDOFF_TASK3B_READY.md
- REBUILD_INTENT_AND_SYSTEM_SPEC.md
- REBUILD_ROADMAP_AND_TODO.md
- TASK1_REPO_AUDIT.md
- TASK2A_IMPLEMENTATION_REPORT.md
- TASK2_EXECUTION_AND_SYNC_PROTOCOL.md
- REAL_DATA_PLUS_SCENARIO_MODE_STRATEGY.md
- TASK3B1_BRONZE_IMPLEMENTATION_REPORT.md
- TASK3B1A_RECONCILE_REPORT.md
- v1_canonical_schema.md
- current machine_alias_registry module
- current Bronze raw store module/tests

Current approved status:
- Task 2A passed
- Task 2B passed
- Task 3A passed
- Task 3B1 passed
- Task 3B1a reconcile passed
- Task 3B2 has NOT started yet

Do not broaden scope.
Do not change UI unless the task explicitly requires it.
Do not rewrite ML logic unless the task explicitly requires it.
Do not merge daily energy or tariff aggregate energy into the hourly backbone.
At the end provide:
1. changed file list
2. reason for each change
3. tests run
4. unresolved issues
5. patch/diff summary
