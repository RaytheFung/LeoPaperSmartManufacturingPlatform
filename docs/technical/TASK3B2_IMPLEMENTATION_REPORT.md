# Task 3B2 Implementation Report

## What Was Changed
- Patched [core/bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/bronze_raw_store.py) so `raw_payload_json` serialization safely handles `datetime.datetime`, `datetime.date`, `datetime.time`, and `pd.Timestamp`.
- Added [core/source_family_registry.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/source_family_registry.py) as a lightweight source-family contract registry.
- Added [core/silver_normalizer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/silver_normalizer.py) to create and normalize the Silver tables:
  - `energy_meter_hour`
  - `csi_job_event`
  - `mes_report_event`
  - `maintenance_txn_event`
- Added and extended tests in:
  - [tests/test_bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_bronze_raw_store.py)
  - [tests/test_silver_normalizer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_silver_normalizer.py)

## Supported Source Families
- `energy_hourly_report_v1` -> `supported`
- `energy_daily_report_v1` -> `supplementary_only`
- `energy_tariff_aggregate_v1` -> `separate_family`
- `csi_monthly_xlsx_v1` -> `supported`
- `csi_monthly_xls_variant_v1` -> `registered_variant`
- `mes_monthly_report_v1` -> `supported`
- `maintenance_transaction_v1` -> `supported`

## Implementation Notes
- Energy Silver normalization only consumes Bronze `raw_energy_hourly` and excludes `合計用量` summary rows from `energy_meter_hour`.
- Energy hour timestamps are parsed strictly. Rows are excluded from `energy_meter_hour` if `raw_timestamp` cannot be parsed into a valid hour-aligned timestamp.
- Energy component parsing preserves meter composition explicitly and currently normalizes into:
  - `aggregate_total`
  - `main`
  - `uv`
  - `ir`
  - `motor`
  - `combo`
  - `unknown`
- CSI, MES, and maintenance normalization use `raw_payload_json` as the primary truth source when available, with Bronze convenience columns used only as fallback.
- All canonical machine joins go through [core/machine_alias_registry.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/machine_alias_registry.py). Bronze canonical IDs are reused when already populated, otherwise the resolver is called again from the raw identifier.
- Silver keeps CSI leader naming explicit as `team_leader`; no `engineer_leader` column is created in Silver.
- Silver-to-Bronze audit rejoin remains deterministic through `source_row_hash`. The mapping is documented in [core/silver_normalizer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/silver_normalizer.py) via `get_silver_bronze_traceability_contract()`.
- Merge-readiness guidance for the next stage is documented directly in [core/silver_normalizer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/silver_normalizer.py) via comments and `get_gold_merge_readiness_contract()`. The Gold backbone is not `energy_meter_hour` itself; it must be an aggregated machine-hour projection derived from meter-level `energy_meter_hour`.

## Real-Sample Validation
- Unit coverage was added for the required edge cases and June-like schema shapes.
- A light smoke validation path was run against the live sample files:
  - `data/能耗、費用報表June(1-30).xlsx`
  - `data/CSI印刷心電圖報表June.xlsx`
  - `data/MES生產數據JunePrinter.xlsx`
  - `2025 DataSet(JAN to JUN)/(12:3:2026) Maintenance/印刷機維修記錄清單（2025年全年）.xlsx`
- What was actually smoke-tested:
  - Energy: first 20 rows from the real June hourly workbook, written to Bronze then normalized to Silver
  - CSI: first 20 rows from the real June CSI workbook, written to Bronze then normalized to Silver
  - MES: first 20 rows from the real June MES workbook, written to Bronze then normalized to Silver
  - Maintenance: first 20 valid rows from the live full-year maintenance export after `skiprows=2`, written to Bronze then normalized to Silver
- Result in a temporary database:
  - `energy_meter_hour`: 20 rows, with summary-row filtering and hour timestamp parsing exercised on live June labels
  - `csi_job_event`: 20 rows, using the real June CSI column set including team fields and stop-reason fields
  - `mes_report_event`: 20 rows, using the real June MES raw schema rather than legacy convenience-field names only
  - `maintenance_txn_event`: 20 rows, using the live maintenance export schema with asset and legacy-asset fields
- What remains unvalidated:
  - No full-file end-to-end normalization run was executed for the entire June workbooks in this task
  - No `.xls` CSI variant sample was available to validate the registered variant path
  - No downstream Gold aggregation or page retargeting was exercised, by design

## Deliberately Out Of Scope
- Retargeting Streamlit pages or changing UI behavior
- Rewriting legacy `unified_view` logic
- Building Gold `fact_machine_hour`
- Daily energy and tariff aggregate integration into the canonical hourly backbone
- ML logic changes
- Repo-wide cleanup or refactors outside the Bronze hardening and Silver foundation

## Schema Drift Or Naming Drift Noticed
- `UPDATED_HANDOFF_TASK3B_READY.md` and `SESSION_HANDOFF_CONTEXT.md` were referenced by the Task 3B2 prompt but are not present in the live repo under those names.
- [docs/technical/v1_canonical_schema.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/v1_canonical_schema.md) names the CSI lead field `engineer_leader`, while the Task 3B2 prompt and the real June CSI contract align better with `team_leader` from `機長姓名1`. This reconcile patch resolves that drift explicitly in favor of `team_leader`.
- The maintenance export uses `工單描述` in the real workbook, while older code paths also reference `工單說明`. Silver supports both, preferring `工單描述`.
- The maintenance workbook requires `skiprows=2` to reach the actual header row because the first two rows are filter/banner output.

## XLS Reader / Dependency Limitation
- The `csi_monthly_xls_variant_v1` family is registered but not normalized through a dedicated reader path in this task.
- No `.xls` CSI sample file is present in the repo, and no new dependency was added only to support that variant.
- The variant is marked as reader-dependent on `xlrd`, and that dependency should be treated as optional until a real `.xls` sample is approved for testing.

## Unresolved Ambiguity Before Gold
- Some canonical machine IDs in CSI are already 4-digit resource-style identifiers. Gold-stage merge rules must decide when those are already canonical versus when they need stricter family-level normalization.
- `energy_meter_hour.parse_confidence` currently communicates parser certainty only; Gold still needs an explicit policy for whether low-confidence unresolved energy rows are excluded or routed to review.
- Gold still needs the exact aggregation contract that projects meter-level `energy_meter_hour` rows into one machine-hour record when multiple meter rows exist for the same `canonical_machine_id x hour_ts`.
- CSI maintenance-like context is preserved by not filtering those rows, but the exact Gold-stage interpretation of mixed production-plus-maintenance stop reasons still needs a decision.
- The maintenance sample available for smoke validation is the full-year export rather than a June-only slice, so Gold-stage temporal assumptions should not rely on that file being month-scoped.
