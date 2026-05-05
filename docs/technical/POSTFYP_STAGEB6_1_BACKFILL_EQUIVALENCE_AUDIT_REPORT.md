# Post-FYP Stage B6.1 Backfill Equivalence Audit Report

## Purpose

Stage B6.1 audits the historical backfill call chain after the Stage B5 source-discovery default switch.
Stage B5 proved source-path payload behavior for accepted extension historical months; it did not prove ETL output equivalence, canonical Silver/Gold materialization equivalence, database safety under execution, or runtime performance.

This report defines the evidence required before any future temp-only historical backfill rehearsal.

## Scope

This is an audit and documentation stage only.
It does not run ETL, run historical backfill, run canonical materialization, write `manufacturing_data.db`, train or promote ML artifacts, change Streamlit upload/manual ETL behavior, expose new write controls, or wire `config/data_quality_rules.v1.json` into runtime normalization.

The audit covers the historical backfill path beginning at `ETLPipelineModule.run_historical_canonical_backfill()` and ending at the Silver/Gold month-partition writes invoked by `CanonicalMaterializer.materialize_backfill_month()`.

## Evidence basis

Evidence was reviewed from:

- `docs/technical/POSTFYP_STAGEB5_SOURCE_DISCOVERY_DEFAULT_SWITCH_CLOSEOUT_REPORT.md`
- `docs/technical/POSTFYP_STAGEB5_1_EXTENSION_MANIFEST_DEFAULT_SWITCH_REPORT.md`
- `docs/technical/POSTFYP_STAGEB5_2_POST_SWITCH_AUDIT_AND_DIAGNOSTICS_REPORT.md`
- `docs/technical/POSTFYP_STAGEB4_4_MANIFEST_DEFAULT_SWITCH_DECISION_PACK.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `modules/etl_module.py`
- `core/enhanced_etl_solution_CURRENT.py`
- `core/etl/extractor.py`
- `core/etl/mapper.py`
- `core/etl/reporter.py`
- `core/bronze_raw_store.py`
- `core/canonical_materializer.py`
- `core/silver_normalizer.py`
- `core/gold_fact_builder.py`
- `tests/test_source_discovery_default_switch.py`
- `tests/test_source_discovery_stage_b5_closeout.py`
- `tests/test_task13_source_discovery.py`
- `scripts/compare_source_discovery_modes.py`
- `docs/technical/TASK13_SOURCE_AVAILABILITY_MATRIX.md`
- `docs/technical/TASK13I_AUG2025_TO_FEB2026_SWEEP_AND_PROMOTION_REPORT.md`

No ETL execution, historical backfill execution, canonical materialization, or DB write was performed for this report.

## Historical backfill call-chain map

1. `ETLPipelineModule.run_historical_canonical_backfill(month_years, data_root=None)` validates the requested month list, creates `CanonicalMaterializer(self.db_path)`, and loops through each requested month.
2. For each month, `resolve_historical_month_sources(month_year, data_root=data_root)` resolves the raw source payload. After Stage B5, default `auto` mode uses manifest-backed discovery for accepted extension months July 2025 through February 2026, falls back to legacy for January through June 2025, and preserves blocked behavior for March 2026.
3. `EnhancedSmartManufacturingETL.extract_all_sources(energy_files, csi_file, mes_file)` delegates to `DataExtractor.extract_all()`, which loads Energy, CSI, and MES workbooks, applies machine-resolution metadata, and returns DataFrames.
4. `_scope_etl_state_to_month(etl, month_year)` filters the extracted Energy, CSI, and MES state to the requested month and clears cached aggregation, mapping, partial-match, and integrated-metric state.
5. `EnhancedSmartManufacturingETL.create_comprehensive_mapping()` builds machine mapping via `MachineMapper.create_mapping()`, including Energy aggregation, Energy-CSI, Energy-MES, CSI-MES, three-way-match counts, mapping stats, and partial-match groups.
6. `ETLPipelineModule.save_etl_results(mapping_results, month_year, etl)` creates or alters ETL staging tables, writes scoped Energy/CSI/MES rows through `BronzeRawStore`, deletes and reinserts target-month rows in `etl_energy_data`, `etl_csi_data`, and `etl_mes_data`, and records run metadata.
7. `CanonicalMaterializer.materialize_backfill_month(month_year)` parses month bounds, calls `_materialize_month_silver()`, then calls `_materialize_gold_month()`.
8. `_materialize_month_silver()` reads target-month Bronze partitions, normalizes them with `SilverNormalizer._normalize_energy_rows()`, `_normalize_csi_rows()`, `_normalize_mes_rows()`, and `_normalize_maintenance_rows()`, then replaces matching Silver month partitions.
9. `_materialize_gold_month()` reads target-month Silver rows, builds base `fact_machine_hour` rows from Energy, overlays CSI, applies CSI quantity, overlays MES, overlays maintenance context, applies idle and maintenance-state review, serializes source flags, then replaces the target-month `fact_machine_hour` partition.

## Step classification table

| Step | Primary classification | Write/output behavior | Rollback sensitivity |
| --- | --- | --- | --- |
| `run_historical_canonical_backfill()` request handling | orchestration | no direct write before child calls | high, because it coordinates all downstream writes on `self.db_path` |
| `resolve_historical_month_sources()` | source-discovery only | no DB write; reads filesystem path availability | low for DB, high for accepted/blocked source policy |
| `EnhancedSmartManufacturingETL.extract_all_sources()` | raw extraction | reads Excel sources; `.xls` conversion helper may create cache under `etl_outputs/xls_cache` | medium, because generated cache must not be staged |
| `_scope_etl_state_to_month()` | month-scoping guard | in-memory filtering only | medium, because incorrect scoping can contaminate month evidence |
| `create_comprehensive_mapping()` | mapping/business logic | in-memory Energy aggregation, mapping stats, and partial-match groups | medium, because mapping changes alter staging and Bronze canonical IDs |
| `save_etl_results()` table creation and schema alignment | database write | creates/alters ETL staging tables on `self.db_path` | high |
| `BronzeRawStore.write_energy_rows()`, `write_csi_rows()`, `write_mes_rows()` | database write | upserts Bronze raw source rows by `source_row_hash` | high |
| `save_etl_results()` monthly staging replacement | database write | deletes and reinserts target-month `etl_energy_data`, `etl_csi_data`, `etl_mes_data` | high |
| `save_etl_results()` run metadata | database write | records ETL run summary and mapping counts | high |
| `CanonicalMaterializer.materialize_backfill_month()` | canonical Silver/Gold materialization | invokes Silver and Gold replacement helpers | high |
| `_materialize_month_silver()` | canonical Silver materialization | replaces target-month Silver partitions | high |
| `_materialize_gold_month()` | canonical Gold materialization | replaces target-month `fact_machine_hour` partition | high |
| CSI quantity overlay support read | canonical Gold materialization | reads other-month Gold rows by CSI source hash to allocate quantity basis | medium, because other-month reads affect target-month allocation evidence |
| `ETLReporter.generate_report()` | generated-output/reporting risk | not called by `run_historical_canonical_backfill()`; would write an Excel report if invoked separately | low for this call chain, high if added to future rehearsal |

## Output-equivalence definition

A future temp-only rehearsal should define ETL output equivalence as all of the following matching the approved baseline or the explicit expected policy for the target month:

- Source payload equivalence: resolved `energy_files`, `csi_file`, `mes_file`, `family_status`, `backfill_readiness`, source-discovery mode, and blocked-month behavior match expected Stage B5 policy.
- Extracted row counts by family: Energy, CSI, and MES loaded counts match the accepted month source package after month scoping.
- Machine mapping counts: Energy unique-machine count, CSI machine count, MES machine count, three-way-match count, and mapping coverage match expected baseline.
- Partial match counts: `energy_csi_only`, `energy_mes_only`, `csi_mes_only`, `energy_only`, `csi_only`, and `mes_only` counts match expected baseline or documented month-specific flags.
- ETL staging table row counts: `etl_energy_data`, `etl_csi_data`, and `etl_mes_data` target-month rows match expected baseline.
- Bronze row counts: `raw_energy_hourly`, `raw_csi_event`, `raw_mes_report`, and `raw_maintenance_txn` target-month rows match expected baseline.
- Silver row counts: `energy_meter_hour`, `csi_job_event`, `mes_report_event`, and `maintenance_txn_event` target-month rows match expected baseline.
- Gold row counts: `fact_machine_hour` target-month rows match expected baseline.
- Canonical `fact_machine_hour` month row count: the month partition count matches the expected materialized count and does not silently include March 2026 or any other blocked/out-of-scope month.
- Aggregate quantity and energy checks: target-month total kWh, positive good quantity, scrap quantity, quantity-basis minutes, and major source-overlay counts match expected baseline within an explicitly approved tolerance.
- Source flags and DQ flags consistency: `source_flags`, partial-energy flags, CSI quantity flags, maintenance flags, and known quarantine handling match expected policy.
- Blocked-month behavior: March 2026 remains blocked in default, manifest, and compare paths and cannot become accepted through rehearsal setup.
- Temp-only DB boundary: all writes occur only on a temp DB copy; the repo-local runtime DB and any shared DB path remain unchanged.
- Git safety: no DB, raw Excel, generated `etl_outputs`, model artifact, or local environment folder is created in the staged set.

## Evidence available without ETL execution

The following evidence can be collected without running ETL or writing a DB:

- Static call-chain mapping from source code.
- Resolver default-policy verification through source-discovery-only tests and compare diagnostics.
- Source payload equivalence for accepted extension months using `scripts/compare_source_discovery_modes.py`.
- January through June legacy default boundary from Stage B5 reports and resolver tests.
- March 2026 blocked behavior from manifest metadata, compare diagnostics, and Stage B5 tests.
- DB write-point identification in `save_etl_results()`, `BronzeRawStore`, and `CanonicalMaterializer`.
- Generated-output risk identification from `DataExtractor._convert_xls_with_helper()` and `ETLReporter.generate_report()`.
- Required future SQL metric list and abort criteria.
- Git unsafe-file scans for DB files, local env folders, generated outputs, and staging scope.

This evidence is enough to plan B6.2 safely, but it is not enough to claim ETL output or canonical materialization equivalence.

## Evidence requiring temp-only execution

The following evidence requires a controlled temp-only execution against a copied DB path:

- Extracted Energy/CSI/MES row counts after workbook loading and month scoping.
- Machine mapping stats and partial-match group counts generated by `MachineMapper`.
- ETL staging table row counts after `save_etl_results()`.
- Bronze target-month row counts after raw-source upserts.
- Silver target-month row counts after `_materialize_month_silver()`.
- Gold `fact_machine_hour` row counts after `_materialize_gold_month()`.
- Aggregate target-month kWh, good quantity, scrap quantity, and quantity-basis checks.
- Source flag and quarantine consistency checks after Silver/Gold normalization.
- Actual runtime duration and stage-level performance evidence.
- Proof that no writes occurred outside the temp DB path.
- Regression-test evidence after temp-only execution.

Any future temp-only run must log the temp DB path, source root, command, start/end timestamps, row-count queries, aggregate queries, and post-run Git safety scans.

## Candidate month recommendation

The safest candidate month for a future B6.2 temp-only rehearsal is `July 2025`.

July 2025 is preferable because it is the first accepted extension month, has complete Energy/CSI/MES source-family status, and does not carry the same known partial-energy or quarantine complexity documented for later accepted months.
The Task13 source availability matrix records July as ready, while August 2025 has a sentinel anomaly policy and February 2026 has both partial-family flags and the unresolved `1262-00012` quarantine.

July is still not risk-free: its source files may include next-month spill rows, so month scoping must be verified explicitly.
That risk is narrower and easier to audit than starting with August or February, where expected flags and quarantines would make first-pass equivalence failures harder to interpret.

## Abort criteria for future rehearsal

A future B6.2 rehearsal must abort if any of the following occur:

- The DB path is not a temp-only copy.
- Any write would target repo-local `manufacturing_data.db` or another shared/live DB path.
- Any raw DB, `*.db`, `*.sqlite`, or `*.sqlite3` file appears in the working tree or staged set.
- Any raw Excel source file is staged.
- Any generated `etl_outputs` file is staged.
- Any model artifact is staged or modified.
- Source payload comparison mismatches for the selected month.
- March 2026 becomes accepted, resolvable as canonical, or silently included in target-month outputs.
- Extracted, mapping, ETL staging, Bronze, Silver, or Gold row counts materially diverge from expected baseline without a documented accepted reason.
- Canonical materialization writes outside the temp DB.
- Runtime exceeds the predeclared safe threshold.
- Downstream regression tests fail.
- Manual upload/runtime ETL behavior changes.
- Streamlit write-capable controls are added.
- `data_quality_rules.v1.json` is wired into `core/silver_normalizer.py` or other runtime materialization code as part of the rehearsal.

## Rollback and DB boundary

Stage B6.1 makes no runtime code change and performs no DB write, so no DB rollback is required.

For any future B6.2 rehearsal, rollback must be defined before execution:

- Use a temp DB copy only.
- Keep the temp DB path outside the Git working tree.
- Record the pre-run and post-run fingerprints of any DB file touched.
- Delete or archive temp DB artifacts outside Git after evidence is extracted.
- Re-run unsafe-file scans before staging.
- Treat source-discovery default rollback as separate from DB rollback; source discovery can be restored to explicit `legacy`, but that does not undo any DB writes from ETL/materialization.

## Out of scope

- Running ETL.
- Running historical backfill.
- Running canonical materialization.
- Writing `manufacturing_data.db`.
- Creating, copying, staging, committing, or pushing DB files.
- ML retraining or artifact promotion.
- Runtime Streamlit behavior changes.
- Manual upload behavior changes.
- New write-capable controls.
- Legacy/dormant code removal.
- Jan-Jun manifest migration.
- March 2026 acceptance.
- Data-quality rule runtime enforcement.
- Raw Excel, generated `etl_outputs`, model artifact, or local environment staging.

## Validation

Stage B6.1 validation is limited to documentation, static code review, regression tests, compile checks, compare diagnostics, and unsafe-file scans.
No ETL, backfill, canonical materialization, or DB write is part of validation.

Required validation commands for this stage are:

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface tests.test_source_discovery_default_switch`
- `python3.11 -m unittest tests.test_source_discovery_post_switch_audit tests.test_source_discovery_stage_b5_closeout`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

## Remaining risks

- ETL output equivalence remains unproven until a temp-only execution captures row counts and aggregates.
- Canonical Silver/Gold materialization equivalence remains unproven until a temp-only execution captures Bronze, Silver, and Gold row counts plus aggregate checks.
- Runtime duration remains unproven for the current post-Stage-B5 call chain.
- Month-scoping correctness for source workbooks with spill rows needs execution evidence.
- Later accepted months carry flags and quarantines that can mask true regressions if they are used before July is proven.
- The `.xls` conversion helper can create generated cache under `etl_outputs/xls_cache` if variant workbook handling is triggered in a future run.

## Recommended B6.2

Recommended B6.2 should be a temp-only July 2025 rehearsal plan and, only after explicit approval, execution.
It should copy the DB to a temp path outside the repo, run one selected July 2025 backfill path against that temp DB, capture source payloads, extracted row counts, mapping stats, partial-match counts, ETL staging counts, Bronze/Silver/Gold counts, `fact_machine_hour` row count, aggregate energy and quantity checks, source-flag consistency, runtime duration, and post-run unsafe-file scans.

B6.2 should not expand to August 2025, February 2026, March 2026, Jan-Jun manifest migration, data-quality rule enforcement, Streamlit runtime changes, or model artifact promotion until the July temp-only evidence is reviewed.
