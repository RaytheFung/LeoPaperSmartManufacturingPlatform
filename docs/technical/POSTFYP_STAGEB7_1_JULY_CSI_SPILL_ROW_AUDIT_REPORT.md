# Post-FYP Stage B7.1 July CSI Spill-Row Audit Report

## Purpose

Stage B7.1 audits the July 2025 CSI row-count gap observed in Stage B6.4.
Stage B6.4 recorded `24,952` extracted July CSI rows in `etl_csi_data`, but only `24,717` canonical July rows in both `raw_csi_event` and `csi_job_event`.
This report determines whether the `235` excluded rows are legitimate spill rows outside canonical July scope or evidence of a predicate, extraction, duplicate, or row-hash issue.

## Scope

This is a read-only audit.
It adds a read-only audit helper, a focused safety test module, this report, and a docs-index entry.
It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write a DB in the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery defaults, change canonical predicates, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence source

The audit used the preferred Stage B6.4 temp-only DB:

- DB path: `/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db`
- Resolved read-only path: `/private/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db`
- Script: `python3.11 scripts/audit_july_csi_spill_rows.py --db-path /tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db --pretty`

The helper opens SQLite with `mode=ro`, refuses DB paths inside the GitHub-safe repo, refuses DB paths inside the original runtime repo, and fails clearly for a missing DB path.

## Canonical July CSI predicate

Current code uses these canonical month expressions:

Bronze `raw_csi_event`:

```sql
COALESCE(
  substr(raw_start_time, 1, 7),
  substr(raw_end_time, 1, 7),
  substr(raw_prep_end_time, 1, 7),
  substr(json_extract(raw_payload_json, '$.班次內日期'), 1, 7)
) = '2025-07'
```

Silver `csi_job_event`:

```sql
COALESCE(
  substr(prod_start_ts, 1, 7),
  substr(prod_end_ts, 1, 7),
  substr(prep_end_ts, 1, 7),
  substr(shift_date, 1, 7)
) = '2025-07'
```

For `etl_csi_data`, the equivalent available expression is:

```sql
COALESCE(
  substr(start_time, 1, 7),
  substr(end_time, 1, 7),
  substr(setup_end, 1, 7)
) = '2025-07'
```

`etl_csi_data` does not store CSI shift date, so the audit reports shift-date month as unavailable for ETL-stage spill rows.

## Row-count reconciliation

| Surface | July rows | Good qty sum | Min start | Max end |
| --- | ---: | ---: | --- | --- |
| `etl_csi_data` where `month_year = 'July 2025'` | `24,952` | `131,049,760.0` | `2025-07-01 08:00:00` | `2025-08-11 15:40:37` |
| `etl_csi_data` using canonical-like July expression | `24,717` | `130,309,991.0` | `2025-07-01 08:00:00` | `2025-08-01 08:00:00` |
| `raw_csi_event` under canonical July predicate | `24,717` | `130,309,991.0` | `2025-07-01 08:00:00` | `2025-08-01 08:00:00` |
| `csi_job_event` under canonical July predicate | `24,717` | `130,309,991.0` | `2025-07-01 08:04:53` | `2025-08-01T08:00:00` |
| `etl_csi_data` outside canonical-like July expression | `235` | `739,769.0` | `2025-08-01 00:02:01` | `2025-08-11 15:40:37` |

Reconciliation:

- `24,952 - 24,717 = 235`
- `etl_csi_data` canonical-like July rows match `raw_csi_event` canonical July rows.
- `raw_csi_event` canonical July rows match `csi_job_event` canonical July rows.
- The excluded `235` rows account exactly for the Stage B6.4 difference.

## Spill-row classification

| Start month | End month | Setup/prep month | Shift date month | Canonical month | Rows | Good qty sum | Min start | Max end |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| `2025-08` | `2025-08` | `2025-08` | unavailable in `etl_csi_data` | `2025-08` | `213` | `739,769.0` | `2025-08-01 00:02:01` | `2025-08-01 08:00:04` |
| `2025-08` | `2025-08` | null | unavailable in `etl_csi_data` | `2025-08` | `22` | null | `2025-08-01 01:04:59` | `2025-08-11 15:40:37` |

All `235` excluded ETL rows resolve to canonical month `2025-08`, not `2025-07`, under the first-available timestamp rule.
They are legitimate extracted spill rows outside canonical July scope.

## Machine/order/good-qty summary

The `235` spill rows cover `70` distinct CSI machine IDs and `138` distinct order IDs.
The total positive/non-null good quantity sum is `739,769.0`.

Top machine contributors by good quantity:

| Machine ID | Rows | Distinct orders | Good qty sum | Min start | Max end |
| --- | ---: | ---: | ---: | --- | --- |
| `D-024-147` | `1` | `1` | `46,594.0` | `2025-08-01 02:18:36` | `2025-08-01 08:00:00` |
| `D-024-143` | `5` | `2` | `42,340.0` | `2025-08-01 01:09:08` | `2025-08-01 08:00:00` |
| `D-024-144` | `4` | `1` | `40,888.0` | `2025-08-01 00:48:47` | `2025-08-01 08:00:00` |
| `D-024-131` | `2` | `2` | `30,750.0` | `2025-08-01 03:51:30` | `2025-08-01 07:54:10` |
| `D-024-082` | `4` | `1` | `24,449.0` | `2025-08-01 00:34:02` | `2025-08-01 08:00:00` |
| `D-035-018` | `4` | `4` | `23,426.0` | `2025-08-01 00:31:03` | `2025-08-01 08:00:00` |
| `D-024-138` | `2` | `1` | `23,040.0` | `2025-08-01 00:25:29` | `2025-08-01 08:00:00` |
| `D-024-099` | `3` | `3` | `22,539.0` | `2025-08-01 01:15:29` | `2025-08-01 07:54:14` |
| `D-024-133` | `3` | `3` | `21,735.0` | `2025-08-01 02:18:00` | `2025-08-01 07:45:49` |
| `D-024-141` | `6` | `2` | `21,712.0` | `2025-08-01 00:11:53` | `2025-08-01 08:00:04` |

Top machine/order contributors by good quantity:

| Machine ID | Order ID | Rows | Good qty sum | Min start | Max end |
| --- | --- | ---: | ---: | --- | --- |
| `D-024-147` | `J250019578` | `1` | `46,594.0` | `2025-08-01 02:18:36` | `2025-08-01 08:00:00` |
| `D-024-143` | `J250026548` | `4` | `42,340.0` | `2025-08-01 01:09:08` | `2025-08-01 07:40:24` |
| `D-024-144` | `J250016979` | `4` | `40,888.0` | `2025-08-01 00:48:47` | `2025-08-01 08:00:00` |
| `D-024-131` | `J250027783` | `1` | `30,750.0` | `2025-08-01 03:51:30` | `2025-08-01 07:24:26` |
| `D-024-082` | `J250024423` | `4` | `24,449.0` | `2025-08-01 00:34:02` | `2025-08-01 08:00:00` |
| `D-024-138` | `J250027039` | `2` | `23,040.0` | `2025-08-01 00:25:29` | `2025-08-01 08:00:00` |
| `D-024-121` | `J250026052` | `3` | `21,440.0` | `2025-08-01 01:07:52` | `2025-08-01 08:00:00` |
| `D-024-132` | `J250027823` | `7` | `17,968.0` | `2025-08-01 00:09:33` | `2025-08-01 07:46:44` |
| `D-035-015` | `J250025871` | `2` | `17,637.0` | `2025-08-01 02:18:34` | `2025-08-01 08:00:00` |
| `D-024-133` | `J250027695` | `1` | `15,993.0` | `2025-08-01 02:18:00` | `2025-08-01 06:57:22` |

## Interpretation

The difference is legitimate spill rows outside canonical July scope.
The ETL extraction scope admits rows into the July ETL staging set when the source package/month-scoping process includes them.
The canonical Bronze/Silver July predicates then assign CSI rows by the first available timestamp month.
For the `235` excluded rows, that first available month is `2025-08`.

This is not a predicate mismatch: `raw_csi_event` and `csi_job_event` both return `24,717` canonical July rows and the same `130,309,991.0` good quantity sum.
It is not an extraction-scope issue requiring a runtime change in this stage: the extracted staging set is broader than canonical July, and the excluded rows are consistently outside canonical July under the current predicate.
It is not a duplicate or row-hash issue: duplicate source-row-hash group counts are zero for canonical raw and silver CSI, and duplicate ETL signature groups are zero for July staging.

## Whether policy is acceptable

The current policy is acceptable for Stage B6/B7 evidence if the canonical month rule remains the approved interpretation:

- ETL staging can contain source-package spill rows.
- Canonical July Bronze/Silver/Gold should use the first available CSI timestamp month.
- Rows whose first available CSI timestamp month is August should not be counted in canonical July, even if they were carried by the July source/extraction scope.

This policy should stay documented because extracted-row counts and canonical-row counts are not expected to match when a source package includes next-month spill rows.

## What remains uncertain

- `etl_csi_data` does not preserve `班次內日期`, so this audit cannot summarize shift-date month directly from ETL staging.
- The audit did not change or re-evaluate whether the first-available timestamp rule is the best long-term business policy.
- The audit did not run August 2025, so it does not prove where these `235` rows land in a clean August canonical run.

## Safety evidence

- The audit used `/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db`.
- The helper opens SQLite with `mode=ro`.
- The helper refuses DB paths inside `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_github_safe`.
- The helper refuses DB paths inside `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform`.
- The helper requires an explicit `--db-path`.
- No ETL, historical backfill, canonical materialization, ML retraining, or artifact promotion was run.
- No DB file was created in the GitHub-safe tree.
- `app.py` was not modified.

## Runtime behavior impact

No runtime behavior changed.
The audit helper is standalone and read-only.
No source-discovery default policy, ETL scoping, Bronze/Silver/Gold predicate, DQ rule, Streamlit route, or model behavior was changed.

## Tests run

- `python3.11 -m unittest tests.test_july_csi_spill_audit_safety`
- `python3.11 scripts/audit_july_csi_spill_rows.py --db-path /tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db --pretty`

The full required regression and safety-validation set for Stage B7.1 was run before commit and is recorded in the terminal handoff for this branch.

## Unsafe file scan

The required unsafe-file scans were run before commit.
The intended staged set is limited to:

- `scripts/audit_july_csi_spill_rows.py`
- `tests/test_july_csi_spill_audit_safety.py`
- `docs/technical/POSTFYP_STAGEB7_1_JULY_CSI_SPILL_ROW_AUDIT_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

No DB file, raw Excel file, generated `etl_outputs` file, local environment folder, model artifact, or `app.py` change is part of Stage B7.1.

## Recommended B7.2

Recommended Stage B7.2 should be a policy decision pack for CSI month assignment.
It should decide whether to keep the current first-available timestamp canonical predicate, add explicit report wording/UI diagnostics that distinguish extracted-source rows from canonical-month rows, or design a later predicate change.
It should not change runtime predicates until the business interpretation is approved.
