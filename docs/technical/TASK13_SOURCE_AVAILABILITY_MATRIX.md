# Task13 Source Availability Matrix

## Scope

- Target extension window: `July 2025` -> `February 2026`
- Explicit blocked month shown for control: `March 2026`
- Source families:
  - MES
  - CSI
  - Energy

## Month Matrix

| Month | Energy | CSI | MES | Backfill Readiness | Notes |
| --- | --- | --- | --- | --- | --- |
| July 2025 | complete | complete | complete | ready | July CSI file is present, non-empty, structurally compatible, and accepted after direct file audit. |
| August 2025 | partial | complete | complete | ready with flags | Energy accepts the month after excluding the `2025-08-17 08:00:00` -> `17:00:00` sentinel anomaly rows for `1024-10032/024-147印刷機UV`. |
| September 2025 | complete | complete | complete | ready | No additional scoped blocker found during direct audit. |
| October 2025 | partial | complete | complete | ready with flags | Energy contains localized partial meter-month cases for `024-094`, `1024-10006`, and `024-082` sub-meter onboarding. |
| November 2025 | partial | complete | complete | ready with flags | Energy contains a localized partial meter-month case for `印刷機1024-10009（IR+UV）`. |
| December 2025 | complete | complete | complete | ready | No additional scoped blocker found during direct audit. |
| January 2026 | partial | complete | complete | ready with flags | Energy contains localized partial meter-month cases for `024-010`, `024-075`, and `024-080`. |
| February 2026 | partial | partial | partial | ready with flags | Energy partial flags remain active; CSI/MES rows for unresolved `1262-00012` stay quarantined; new `024-075` / `024-080` aliases were resolved safely. |
| March 2026 | blocked | blocked | blocked | blocked | Explicitly outside Task13 scope. Energy grouped file contains March rows, but they must not be landed in this task. |

## Direct-Source Notes

### MES

- File: `印刷機MES生產數據-2025年3月1日至2026年2月28日.xlsx`
- Authoritative month field: `報工時間`
- Direct audit confirmed:
  - `報工時間` max = `2026-02-28 23:39:45.643000`
  - `狀態變更時間` and `記錄新增時間` extend into early March 2026
- Task13 policy: month assignment must use `報工時間` only

### CSI

- Files: `CSI印刷心電圖報表2025年7月.xls` -> `CSI印刷心電圖報表2026年2月.xls`
- Direct audit confirmed:
  - July 2025 file contains `24,952` July rows plus next-month spill rows that require month slicing, not rejection
  - new files are `.xls`
  - new family carries one added column versus old June baseline: `心電圖轉版次數`
- Task13 policy:
  - July 2025 CSI is accepted
  - blank-vs-zero semantics remain preserved
  - unresolved `1262-00012` rows in February 2026 remain quarantined

### Energy

- Files:
  - `能耗、費用報表__2025.7.xlsx`
  - `能耗、費用報表_2025.8-10.xlsx`
  - `能耗、費用報表_2025.11-12.xlsx`
  - `能耗、費用報表_2026.1-3.xlsx`
- Direct audit confirmed:
  - August 2025 contains exactly `10` sentinel anomaly rows for `1024-10032/024-147印刷機UV`
  - October 2025, November 2025, January 2026, and February 2026 contain localized partial meter-month cases that should be flagged, not treated as global failure
  - March 2026 exists in the grouped Jan-Mar file and must remain excluded from Task13 landing
