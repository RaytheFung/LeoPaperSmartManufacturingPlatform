# Post-FYP Stage B9.2 CSI Carry-Forward Reconciliation Report

## Purpose

Stage B9.2 performs a temp-only CSI carry-forward reconciliation rehearsal for August 2025.
It starts from a copied temp DB outside Git, runs the August clean-baseline flow, carries forward the `235` July-package CSI rows that canonicalize to August, refreshes August canonical materialization, and compares the result against the B8.2 August-only baseline.

## Scope

This stage adds `scripts/run_august_2025_csi_carry_forward_reconciliation.py`, adds safety tests, creates this technical report, and updates the rebuild docs index.

It writes only `/tmp/leopaper_stage_b9_2_carry_forward/august_carry_forward.db`.
It does not write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, modify model/preprocessor artifacts, retrain ML models, stage raw Excel files, stage generated `etl_outputs`, change source-discovery defaults, change runtime canonical predicates, change Streamlit upload/manual ETL behavior, add write-capable Streamlit controls, modify `app.py`, run March 2026, or run a broad multi-month rehearsal.

## Evidence basis from B8/B9.1

| Stage | Evidence used |
| --- | --- |
| B8.2 | August-only temp rehearsal succeeded operationally but left July-package spill traceability at `0/235` raw and `0/235` silver. |
| B8.3 | Policy direction selected controlled carry-forward / adjacent-package reconciliation without runtime predicate changes. |
| B9.1 | Read-only preflight identified `235` July-package candidates, zero August-only overlap, and `235/235` raw/silver traceability in the B6.4 temp DB. |

## Temp DB boundary

Original runtime DB copied from:

```text
/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db
```

Temp execution DB:

```text
/tmp/leopaper_stage_b9_2_carry_forward/august_carry_forward.db
```

Original runtime DB evidence:

| Point | Size bytes | mtime UTC | mtime ns |
| --- | ---: | --- | ---: |
| before | `7226900480` | `2026-04-17T13:59:22.177873+00:00` | `1776434362177873373` |
| after | `7226900480` | `2026-04-17T13:59:22.177873+00:00` | `1776434362177873373` |

Temp DB evidence:

| Point | Size bytes | SHA-256 |
| --- | ---: | --- |
| before mutation | `7226900480` | `acf2faffb9ffa3e366b4440a50e62783c9bb22142d0d3ded75c9ea019fc40d26` |
| after reconciliation | `7226900480` | `0c3e513b4070d01ec541a025a18fd9c8367d74657c261963dffb5a5a52e6ca52` |

The temp DB path resolved under `/private/tmp/...`, outside both the GitHub-safe tree and the original runtime repo.

## Candidate source

Candidate source DB:

```text
/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db
```

Candidate evidence:

| Metric | Result |
| --- | ---: |
| candidate count | `235` |
| distinct machines | `70` |
| distinct orders | `138` |
| good quantity sum | `739769.0` |
| min start time | `2025-08-01 00:02:01` |
| max end time | `2025-08-11 15:40:37` |
| raw hash matched candidates | `235` |
| silver matched candidates | `235` |
| source row hash available | `true` |

The identity key remains:

```text
machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty
```

## Reconciliation method

The B9.2 runner:

1. Validates the target month is exactly August 2025.
2. Refuses target DB paths inside the GitHub-safe tree or original runtime repo.
3. Copies the original runtime DB to the temp target path.
4. Reuses the B8.2 conservative August isolation and August backfill flow on the temp DB.
5. Selects one repo-relative previous-package raw CSI row per candidate identity from B6.4 evidence.
6. Rejects candidates already present by `source_row_hash` or composite identity.
7. Inserts only non-overlapping carry-forward raw CSI rows into temp `raw_csi_event`.
8. Runs August canonical materialization on the temp DB so `csi_job_event` and `fact_machine_hour` are refreshed from augmented Bronze.

No runtime predicate or source-discovery policy was changed.
No schema column was added; provenance is retained through the previous-package July `source_file` path.

## Candidate evidence

The runner selected the repo-relative July source file for all inserted carry-forward rows:

```text
source_data/2025_jul_2026_feb_collected/CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年7月.xls
```

This avoids copying both B6.4 provenance variants and keeps one raw row per candidate identity.

## Insert/reconcile evidence

| Metric | Result |
| --- | ---: |
| candidates planned | `235` |
| raw rows inserted | `235` |
| skipped existing source hash | `0` |
| skipped existing identity | `0` |
| duplicate candidate identity groups | `0` |

Before carry-forward, the temp DB matched the B8.2 August-only limitation:

| Metric | Result |
| --- | ---: |
| raw overlap candidate count | `0` |
| silver overlap candidate count | `0` |
| raw August rows before reconcile | `22399` |
| silver August rows before reconcile | `22399` |

After carry-forward and materialization:

| Metric | Result |
| --- | ---: |
| raw matched spill identities | `235` |
| raw unmatched spill identities | `0` |
| silver matched spill identities | `235` |
| silver unmatched spill identities | `0` |
| raw matched distinct source hashes | `235` |
| silver hash matched distinct source hashes | `235` |

Traceability verdict:

```text
august_raw_and_silver_traceability_proven_in_current_temp_db
```

## Duplicate-prevention evidence

Duplicate source-row-hash groups after reconciliation:

| Surface | Duplicate hash groups |
| --- | ---: |
| `raw_csi_event` | `0` |
| `csi_job_event` | `0` |
| `energy_meter_hour` | `0` |
| `mes_report_event` | `0` |

The helper also tested duplicate prevention with a tiny fixture where a candidate identity already exists; the duplicate identity was skipped and not inserted.

## B8.2 baseline comparison

| Surface / metric | B8.2 August-only baseline | B9.2 carry-forward target | Delta |
| --- | ---: | ---: | ---: |
| `raw_csi_event` August rows | `22399` | `22634` | `235` |
| `csi_job_event` August rows | `22399` | `22634` | `235` |
| `csi_job_event` good qty | `107563972.0` | `108303741.0` | `739769.0` |
| `fact_machine_hour` August rows | `64727` | `64727` | `0` |
| `fact_machine_hour` good qty | `98382657.0` | `99069808.0` | `687151.0` |

The raw/silver row delta equals the `235` carry-forward identities.
Gold row count did not change because the existing August hourly grain already covered the month; the Gold good-quantity aggregate increased after refreshed CSI overlay and quantity allocation.

## Gold / aggregate delta evidence

Gold materialization result:

| Metric | Result |
| --- | ---: |
| Bronze `raw_energy_hourly` used | `99695` |
| Bronze `raw_csi_event` used | `22634` |
| Bronze `raw_mes_report` used | `20884` |
| Silver `energy_meter_hour` rows | `99685` |
| Silver `csi_job_event` rows | `22634` |
| Silver `mes_report_event` rows | `20884` |
| Gold `fact_machine_hour` rows | `64727` |

Aggregate evidence after reconciliation:

| Metric | Result |
| --- | ---: |
| raw CSI good qty | `108303741.0` |
| silver CSI good qty | `108303741.0` |
| fact good qty | `99069808.0` |
| fact energy total kWh | `1120241.8068` |
| fact scrap qty | `0.0` |
| affected candidate machine count | `70` |
| affected candidate order count | `138` |

## Safety evidence

- Original runtime DB size and mtime were unchanged.
- Target DB was outside Git and outside the original runtime repo.
- B6.4 and B8.2 evidence DBs were inspected read-only.
- Only the B9.2 temp DB was written.
- No temp DB was promoted.
- No runtime canonical predicate changed.
- No source-discovery default policy changed.
- No DQ runtime wiring changed.
- No model artifact changed.
- `app.py` was not modified.
- March 2026 was not run.

## Result verdict

Stage B9.2 succeeded as a temp-only rehearsal.

The rehearsal proves that the `235` July-package / August-canonical CSI identities can be reconciled into August raw and silver scope without duplicate source-row-hash groups, and that refreshed August Gold output reflects an aggregate good-quantity increase.

## What passed

- Candidate count remained `235`.
- Raw carry-forward insert count was `235`.
- Duplicate candidate identity groups were `0`.
- Raw/silver duplicate source-row-hash groups were `0`.
- Spill traceability improved from `0/235` raw and silver in the August-only baseline to `235/235` raw and silver in the carry-forward temp DB.
- Original runtime DB remained unchanged.
- Validation tests passed.

## What failed or was deferred

An initial local run failed safely before final evidence capture because the first insert implementation copied the source raw `id` column and hit a temp-only `raw_csi_event.id` uniqueness constraint.
The script was fixed to omit `id` during insert and a regression test was added.
The final run succeeded from a fresh copied temp DB.

No live/shared DB promotion was attempted.
No runtime wiring was implemented.
No broad multi-month rehearsal was run.

## What remains unproven

- This is not yet a runtime implementation.
- Cross-month generalization beyond July to August 2025 is not proven.
- Reviewer approval is still needed before any runtime source-selection or carry-forward adoption.
- The permanent provenance representation for carry-forward rows remains a design decision; B9.2 used existing `source_file` provenance only.

## Rollback / cleanup note

Rollback is simply to discard:

```text
/tmp/leopaper_stage_b9_2_carry_forward/august_carry_forward.db
```

No rollback is required for the original runtime DB because it was copied only and stayed unchanged.

## Recommended B9.3

Recommended Stage B9.3: carry-forward adoption design and review gate.

B9.3 should decide how to represent carry-forward provenance permanently, define whether adjacent-package source selection should be helper-only or runtime-wired, specify duplicate protection as a formal contract, and prepare a narrow implementation plan before any live/shared DB promotion.
