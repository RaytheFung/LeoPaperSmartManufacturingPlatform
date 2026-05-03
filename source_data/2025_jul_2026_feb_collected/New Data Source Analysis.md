# Data Source Extension Report (July 2025 to February 2026)

## Purpose
This report consolidates the inspection results for the newly adopted **MES**, **CSI**, and **Energy** source files, with the goal of deciding whether the project dataset can be safely extended beyond the existing **January 2025 to June 2025** baseline.

**Current project boundary:**
- Extend the working database to **February 2026 only**
- **March 2026 is intentionally excluded** from the current ingestion scope

This report is written as a handoff document for the main project context window, so that the next session can continue with a correct understanding of:
- which source files are acceptable as the new baseline extension inputs
- what format and coverage issues were checked
- what data quality issues were found
- what ingestion rules should be applied

---

## Executive Summary

### Final acceptance verdict

#### 1. MES
**Acceptable as primary source**, with one important rule:
- use the new all-in-one MES export as the source for **July 2025 to February 2026**
- slice it internally by **`報工時間`** into monthly ETL windows
- do **not** infer March 2026 production from later system timestamps

#### 2. CSI
**Acceptable as primary source**, with minor ingestion handling:
- the new CSI files are structurally compatible with the older CSI report family
- however, the new files are in **`.xls`** format instead of `.xlsx`
- there is also **one extra column** compared with the older baseline files
- this is not a schema break, but the ingestion path must support `.xls`

#### 3. Energy
**Acceptable as primary source**, but with explicit data-quality rules:
- the July single-month export is normal
- the grouped exports for **Aug–Oct 2025**, **Nov–Dec 2025**, and **Jan–Mar 2026** largely preserve normal coverage
- for the current project scope, use these grouped files only through **February 2026**
- one August hard anomaly must be removed
- several later partial area/meter-month cases must be flagged, but they do **not** look like a fatal export failure

#### 4. Files outside the adopted ETL backbone
Some other energy files were inspected earlier during the investigation process, but they are **not part of the adopted handoff package** for the main project context window. This report therefore focuses only on the files that are actually intended to support the extension from **Jul 2025 to Feb 2026**.

---

## Included Source Scope for This Handoff

### MES
- `印刷機MES生產數據-2025年3月1日至2026年2月28日.xlsx`

### CSI
- `CSI印刷心電圖報表2025年7月.xls`
- `CSI印刷心電圖報表2025年8月.xls`
- `CSI印刷心電圖報表2025年9月.xls`
- `CSI印刷心電圖報表2025年10月.xls`
- `CSI印刷心電圖報表2025年11月.xls`
- `CSI印刷心電圖報表2025年12月.xls`
- `CSI印刷心電圖報表2026年1月.xls`
- `CSI印刷心電圖報表2026年2月.xls`

### Energy
- `能耗、費用報表_20260415155142.xlsx` (July 2025)
- `能耗、費用報表_2025.8-10.xlsx`
- `能耗、費用報表_2025.11-12.xlsx`
- `能耗、費用報表_2026.1-3.xlsx` (**use only through February 2026**)

---

## 1) MES inspection

### File inspected
- `印刷機MES生產數據-2025年3月1日至2026年2月28日.xlsx`

### Main conclusion
This new MES file is a valid and understandable **all-in-one Printer MES source**, and it can be used for the extension period.

### Key findings
- The file is a large detailed MES production log rather than a summary sheet.
- It contains the same general report family and field structure as the older Printer MES monthly files.
- The report is not limited to a single month; it spans multiple months in one workbook.

### Actual production time range
Using **`報工時間`** as the business time field:
- earliest: **2025-03-01**
- latest: **2026-02-28**

This means:
- the file **does not provide March 2026 production data**
- the real usable extension window from this source is **July 2025 to February 2026**

### Overlap with existing baseline
The project already has MES baseline coverage for **January 2025 to June 2025**.
The new all-in-one MES file overlaps with part of that old period:
- March 2025
- April 2025
- May 2025
- June 2025

Therefore:
- the new MES file should **not** simply be appended from March onward without logic
- the recommended policy is:
  - keep the existing Jan–Jun 2025 baseline as-is
  - use the new all-in-one MES file only for **Jul 2025 to Feb 2026**

### Important timestamp clarification
The MES file contains later system timestamps such as:
- `狀態變更時間`
- `記錄新增時間`

Some of those may reach into early March 2026, but the actual production event time (`報工時間`) still ends on **2026-02-28**.

**Decision:** for ETL and model alignment, treat **`報工時間`** as the authoritative production time field.
Do not count this file as March 2026 production coverage.

### MES ingestion recommendation
- accept this all-in-one MES file as the **source of truth for Jul 2025 to Feb 2026**
- slice by `報工時間` internally into monthly chunks
- do not use `狀態變更時間` or `記錄新增時間` to assign production month

---

## 2) CSI inspection

### Files inspected for the extension window
- `CSI印刷心電圖報表2025年8月.xls`
- `CSI印刷心電圖報表2025年9月.xls`
- `CSI印刷心電圖報表2025年10月.xls`
- `CSI印刷心電圖報表2025年11月.xls`
- `CSI印刷心電圖報表2025年12月.xls`
- `CSI印刷心電圖報表2026年1月.xls`
- `CSI印刷心電圖報表2026年2月.xls`

Earlier new CSI files from 2025 were also compared against the old April/May/June baseline family where useful.

### Main conclusion
The new CSI files are **compatible with the older CSI format family** and can be used as the primary CSI source for the extension period.

### Structural findings
Compared with the older baseline CSI files:
- same report family
- same overall sheet layout
- same header positioning logic
- same key fields remain present

Examples of preserved business fields include:
- `機台編號`
- `作业`
- `任務`
- `工程開始時間`
- `準備結束時間`
- `工程結束時間`
- `正品數量`
- `物料`
- `實際速度_本_時`

### Differences found
#### A. File container difference
- old baseline CSI files were `.xlsx`
- new CSI files are `.xls`

This is **not a business schema problem**, but it may affect Python ingestion depending on engine support.

#### B. One additional column
The new CSI files contain **one extra column** compared with the older baseline family:
- `心電圖轉版次數`

This is a compatible extension, not a breaking difference.

### CSI blank vs 0 observations
A targeted inspection was done for the CSI fields corresponding to:
- actual production minutes
- planned stop minutes
- unplanned stop minutes
- good quantity
- scrap quantity

#### Scrap quantity
Business clarification received:
- the company currently does **not record scrap quantity** and has no immediate plan to do so

Therefore, `廢品數量` should not be treated as a mature production-quality metric in this stage.

#### Stop time and production time
Observed pattern from the CSI reports:

**`實際計劃停機時間` / `實際無計劃停機時間`**
- `0` appears in normal production jobs with no stop
- blank appears frequently in maintenance-like or non-standard records
- therefore blank should **not automatically be treated as equivalent to 0**

**`實際生產時間`**
- blank and `0` both appear
- some blank rows still coexist with actual production context
- therefore blank should also **not be blindly imputed as 0**

### CSI ingestion recommendation
- accept the new CSI monthly files as the **source of truth for Aug 2025 to Feb 2026**
- ensure the pipeline supports `.xls` input, or convert these files to `.xlsx` before final ingestion
- keep the extra column if convenient, but do not depend on it for critical ETL logic yet
- do **not** auto-convert CSI blank time fields into 0 unless business meaning is explicitly confirmed

---

## 3) Energy inspection

### 3.1 July 2025 single-month hourly export

#### File inspected
- `能耗、費用報表_20260415155142.xlsx`

### Main conclusion
This file works and behaves like a **normal full monthly hourly energy report**.

### Why it was accepted
- correct hourly structure
- time range matches July 2025 only
- coverage level matches normal monthly report expectations
- no systemic coverage collapse was observed

**Decision:** accept as the primary energy source for **July 2025**.

---

### 3.2 Grouped hourly exports for Aug 2025 to Mar 2026

#### Files inspected
- `能耗、費用報表_2025.8-10.xlsx`
- `能耗、費用報表_2025.11-12.xlsx`
- `能耗、費用報表_2026.1-3.xlsx`

### Main conclusion
These grouped exports are **usable and internally consistent enough to support the extension period**.
For the current project scope, they should be used through **February 2026 only**.

### Coverage behavior
These grouped files preserve the normal coverage scale expected from valid hourly monthly reports.
They do **not** show the sort of global collapse that would make them unusable as the extension backbone.

### Important limitation for current project scope
The `2026.1-3` file includes March 2026 rows, but the current project decision is to extend only to **February 2026**.

**Decision:** use this file only through **2026-02-28** for the present stage.

---

## Energy data quality issues found in the accepted grouped exports

### A. August 2025 hard anomaly
A clear sentinel-style anomaly was found in the August grouped export.

#### Affected area
- `1024-10032/024-147印刷機UV`

#### Affected timestamps
- `2025-08-17 08:00:00` to `2025-08-17 17:00:00`

#### Anomalous values
- `用電量 = 99999999.9999`
- `電費 = 99999999.9999`

### Interpretation
This does **not** look like a real operating value.
It behaves like a placeholder / sentinel / broken reading.

### Recommended treatment
- hard-flag these rows as invalid
- exclude them from normal aggregation and model features
- do not treat them as real consumption

This issue appears localized and does **not** invalidate the rest of the August file.

---

### B. Partial area/meter months in later grouped files

Several later months contain **partial area/meter-month behavior**.
These are important to flag, but they do **not** look like a system-wide export failure.

### Why they are not treated as a fatal issue
The accepted grouped exports still preserve normal overall coverage scale.
The partial behavior is localized to specific machine areas or sub-meters, rather than removing a massive portion of the entire factory scope.

### Likely interpretation
Most of these cases are more consistent with one of the following:
- machine retirement / fade-out
- new machine onboarding
- sub-meter onboarding later than the main machine
- meter lifecycle change

Rather than:
- catastrophic missing extraction
- full-month scope collapse
- broken export logic across the entire file

### Partial cases worth flagging

#### 2025-10
- `印刷机024-094` ends around `2025-10-27 09:00`
- `印刷機1024-10006（UV）` ends around `2025-10-16 12:00`
- `印刷機1024-10006（主機）` ends around `2025-10-16 12:00`
- `印刷機1024-10006（馬達）` ends around `2025-10-16 12:00`
- `印刷機024-082風泵用電(測量)` starts around `2025-10-29 11:00`

#### 2025-11
- `印刷機1024-10009（IR+UV）` ends around `2025-11-08 09:00`

#### 2026-01
- `印刷機024-010` ends around `2026-01-20 17:00`
- `印刷機024-075 UV` starts around `2026-01-28 18:00`
- `印刷機024-075主機` starts around `2026-01-28 18:00`
- `印刷機024-080主機` starts around `2026-01-31 17:00`

#### 2026-02
- `印刷機024-080 UV` starts around `2026-02-02 09:00`

### Impact assessment of partials
These partials matter most for:
- machine-level comparisons
- sub-meter trend interpretation
- attribution logic for the directly affected machines/meters

They matter much less for:
- monthly total energy trend
- broader system-level monitoring
- overall database extension feasibility

**Practical conclusion:** these partials are manageable and should be flagged, not treated as a blocker.

---

## Cross-checking energy partials against CSI / MES

To understand whether the accepted grouped energy partials looked like missing extraction or real machine/meter lifecycle behavior, cross-checking was done against the newer CSI and MES sources.

### 1. `024-094`
Observed pattern:
- active in CSI during August and September 2025
- absent from October CSI
- energy still present into late October

### Likely interpretation
This looks more like:
- production side already stopped or disappeared earlier
- energy meter persisted a bit longer

So this is more consistent with **machine fade-out / tail-end meter presence** than with missing bulk records.

---

### 2. `024-010`
Observed pattern:
- still present in CSI through late 2025
- activity reduces heavily by January 2026
- energy ends mid-late January 2026

### Likely interpretation
This looks like a gradual decline or end-of-life behavior, not a major extraction failure.

---

### 3. `024-075` and `024-080`
Observed pattern:
- these appear as late-arriving cases in energy
- CSI support appears only around the late stage as well

### Likely interpretation
These are more consistent with **new machine / new meter onboarding**.

---

### 4. `024-082風泵用電(測量)`
Observed pattern:
- the machine itself has earlier CSI activity
- but the specific wind-pump sub-meter only appears later in energy

### Likely interpretation
This suggests **sub-meter onboarding later than machine existence**, not missing machine production history.

---

## Overall conclusion on partials
The partial cases in the accepted grouped hourly exports do **not** resemble a global source failure.
They are much more plausibly explained as:
- localized machine lifecycle change
- localized meter lifecycle change
- localized sub-meter onboarding

Therefore, they should be handled as **data-quality flags**, not as evidence that the grouped exports are unusable.

---

## Final ingestion policy for extending the project database to February 2026

### Target extension window
- **July 2025 to February 2026**
- **March 2026 excluded**

### Recommended source-of-truth policy

#### MES
Use:
- `印刷機MES生產數據-2025年3月1日至2026年2月28日.xlsx`

Rules:
- slice by `報工時間`
- ingest only **Jul 2025 to Feb 2026** for extension
- keep existing Jan–Jun 2025 baseline as historical base

#### CSI
Use:
- monthly CSI files from **Aug 2025 to Feb 2026**

Rules:
- support `.xls` ingestion or convert to `.xlsx`
- keep blank-vs-zero semantics cautious
- do not auto-impute blank stop/production time fields as 0

#### Energy
Use as primary energy inputs:
- `能耗、費用報表_20260415155142.xlsx` (July 2025)
- `能耗、費用報表_2025.8-10.xlsx`
- `能耗、費用報表_2025.11-12.xlsx`
- `能耗、費用報表_2026.1-3.xlsx` **but truncate to February 2026 only**

Rules:
- filter out the August 2025 sentinel anomaly rows
- maintain a partial-meter flag list for localized area-month exceptions
- do not treat partial areas as fatal to the full monthly dataset

---

## Practical impact on the project

### What is now safe to say
The project now has a credible path to extend from the original Jan–Jun 2025 baseline to:
- **Jul 2025 to Feb 2026**

using a combination of:
- valid grouped hourly energy files
- valid compatible CSI files
- a valid all-in-one MES file

### What should not be overstated
- energy sub-meter behavior is not perfectly static across the whole period
- some meter lifecycle changes exist
- CSI blank fields should not be oversimplified
- the August 2025 sentinel anomaly must be explicitly handled

### But overall feasibility conclusion
The extension to **February 2026** is feasible and technically well-supported, provided the ingestion rules above are respected.

---


