# Task13 Jul 2025 to Feb 2026 Canonical Expansion Report

## 1. accepted baseline used

- Accepted runtime baseline:
  - `Task11`
  - `Task12A`
  - `Task12B`
- Accepted canonical DB baseline before this run:
  - `fact_machine_hour` months available on the shared DB: `January 2025` -> `June 2025`
- Active artifacts remained unchanged throughout this run:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 2. new source package and scope decision

- New source package used:
  - `/Users/rayfung/Documents/VCC/LeoPaper/DataSet Package(New Collected)`
- Task13 scope decision kept:
  - extend only through `February 2026`
  - explicitly exclude `March 2026`
- Direct-source resolution of the handoff inconsistency:
  - `July 2025` CSI is accepted
  - the earlier wording that implied CSI begins at `August 2025` was inconsistent with the actual files on disk

## 3. direct-source-verified constraints found in current repo

- `core/runtime_paths.py` still assumed a Jan-Jun-only default raw dataset root.
- `modules/etl_module.py` historical month discovery was hard-coded only for `January 2025` -> `June 2025`.
- `process_uploaded_files(...)` rewrote uploaded `.xls` files to `.xlsx` names, which would break engine detection on the active path.
- `core/etl/extractor.py` depended on `pd.read_excel(...)` directly, so `.xls` support depended entirely on the active interpreter already having `xlrd`.
- `core/canonical_materializer.py` still allowed MES month assignment to drift off `報工時間` by falling back to `記錄新增時間` / `狀態變更時間`.
- `core/silver_normalizer.py` had no localized energy-quality handling for the accepted August sentinel anomaly or the later partial meter-month cases.

## 4. exact month availability / completeness result

- Exact matrix: see `TASK13_SOURCE_AVAILABILITY_MATRIX.md`
- Month result summary:
  - `July 2025`: ready
  - `August 2025`: ready with flags
  - `September 2025`: ready
  - `October 2025`: ready with flags
  - `November 2025`: ready with flags
  - `December 2025`: ready
  - `January 2026`: ready with flags
  - `February 2026`: ready with flags
  - `March 2026`: blocked
- Alias/mapping outcome:
  - newly onboarded `024-075` and `024-080` were resolved safely across CSI / MES / Energy and added to the alias registry
  - `1262-00012` remained unresolved safely and stays quarantined

## 5. exact discovery / compatibility changes made

- `core/runtime_paths.py`
  - added `get_workspace_root()`
  - added `get_extended_raw_dataset_root()`
- `modules/etl_module.py`
  - added explicit Jul 2025 -> Mar 2026 extension-month source mappings
  - added month-level readiness / partial / blocked classification for the Task13 extension window
  - added a rendered ETL source-availability matrix on the ETL route
  - preserved Jan-Jun historical mapping behavior
- `core/etl/extractor.py`
  - added controlled `.xls` compatibility handling
  - prefers native `xlrd` when present
  - otherwise falls back to a controlled helper conversion path
  - narrowed CSI and MES workbook reads to the required canonical columns only
- `process_uploaded_files(...)`
  - now preserves uploaded file suffixes instead of blindly renaming `.xls` to `.xlsx`

## 6. exact ETL / materialization changes made

- Added month scoping before mapping/Bronze save for:
  - Energy by `datetime`
  - CSI by month-relevant event timestamps
  - MES by `報工時間`
- `run_historical_canonical_backfill(...)` now scopes extracted data to the target month before mapping/save.
- `save_etl_results(...)` now month-scopes source DataFrames again before Bronze and ETL table writes as a safety guard.
- `core/canonical_materializer.py`
  - raw MES month partitioning now uses `報工時間` only
  - normalized MES month partitioning now uses `report_ts` only
  - March 2026 no longer leaks in through MES status/create timestamps

## 7. exact anomaly / partial handling rules implemented

- Energy sentinel anomaly:
  - `1024-10032/024-147印刷機UV`
  - `2025-08-17 08:00:00` -> `2025-08-17 17:00:00`
  - `用電量 = 99999999.9999`
  - `電費 = 99999999.9999`
  - active rule: exclude from canonical Silver normalization
- Localized partial meter-month flags:
  - added targeted partial flags for the accepted October 2025, November 2025, January 2026, and February 2026 meter-month cases
  - active rule: flag, do not globally block the month
- CSI handling:
  - blank-vs-zero time fields remain preserved
  - extra column `心電圖轉版次數` is tolerated and ignored by canonical logic
- Alias handling:
  - `024-075` / `024-080` resolved and joinable
  - `1262-00012` remains quarantined

## 8. whether Jul 2025 -> Feb 2026 months were actually materialized

- Full shared-DB extension was **not** completed in this run.
- Full Jul 2025 -> Feb 2026 real-data materialization was **not** completed in this run.
- What was completed on real data:
  - direct source audit across the supplied extension package
  - controlled July 2025 Bronze landing on a temp DB path
  - observed Bronze row counts on `/tmp/task13_minismoke_fast.db`:
    - `raw_energy_hourly = 99,695`
    - `raw_csi_event = 24,952`
    - `raw_mes_report = 23,151`
- What did not complete within a practical runtime window:
  - the real-data July 2025 Silver/Gold materialization pass on the temp DB
  - the remaining Aug 2025 -> Feb 2026 real-data month sequence

## 9. shared DB impact and promotion decision

- Shared DB path:
  - `manufacturing_data.db`
- Shared DB decision:
  - left untouched
- Shared DB fingerprint:
  - before run: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - after run: unchanged in this Task13 attempt
- Promotion decision:
  - not safe to promote because the real-data month materialization pass did not finish cleanly end to end

## 10. validation / smoke summary

- Compile passed for all touched Python files.
- Focused tests passed:
  - `tests.test_machine_alias_registry`
  - `tests.test_silver_normalizer`
  - `tests.test_canonical_materializer`
  - `tests.test_task13_source_discovery`
  - `tests.test_etl_extractor`
  - total: `49` tests passed
- Direct-source audit completed on the actual Task13 package:
  - MES report-time range verified
  - CSI July acceptance verified
  - CSI `.xls` family and added column verified
  - August sentinel anomaly verified
  - later partial energy meter-month cases verified
- Runtime compatibility:
  - `requirements.txt` now includes `xlrd==2.0.1`
  - the active `.conda311` validation environment was also provisioned locally with `xlrd 2.0.1` from the existing repo-adjacent Python package cache so the native `.xls` path could be exercised without network access
- Real-data smoke outcome:
  - Bronze landing completed for July 2025 on a temp DB
  - Silver/Gold materialization did not finish within a practical runtime window in this run

## 11. remaining limitations

- Task13 is **not passed** in this run.
- The repo logic is prepared for the Jul 2025 -> Feb 2026 source family, but a full validated real-data month sequence is still pending.
- `1262-00012` remains unresolved and quarantined.
- Shared DB promotion was intentionally skipped.
- Active artifacts remain Task 4L only; no retraining or promotion occurred.

## 12. recommended next step after Task13

- Use the new source matrix and the now-hardened code path to rerun the real-data materialization on a dedicated temp DB in an extended validation window.
- Start with:
  - `July 2025`
  - then sweep `August 2025` -> `February 2026`
- Promote to the shared DB only after:
  - real-data Silver/Gold month completion is proven
  - month counts / latest canonical coverage are verified
  - `1262-00012` is still either safely quarantined or separately mapped with evidence
