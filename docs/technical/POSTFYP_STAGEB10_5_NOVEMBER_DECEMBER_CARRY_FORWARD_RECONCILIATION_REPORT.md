# Post-FYP Stage B10.5 November-December Carry-Forward Reconciliation Report

## Purpose

Stage B10.5 runs one temp-only November 2025 package to December 2025 canonical-month CSI carry-forward reconciliation rehearsal.

The goal is to execute the B10.4 approved `135` include / `7` skip / `0` block plan against a copied temp DB only, prove duplicate prevention, compare against a December-only baseline, and stop before runtime adoption or live/shared DB promotion.

## Scope

This stage adds:

- `scripts/run_november_december_csi_carry_forward_reconciliation.py`
- `tests/test_november_december_carry_forward_reconciliation_safety.py`

It also creates this report and updates `docs/technical/REBUILD_DOCS_INDEX.md`.

This stage writes only to `/tmp/leopaper_stage_b10_5_nov_dec_reconciliation/nov_dec_reconciliation.db`.
It does not write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, modify model artifacts, retrain ML models, change source-discovery default policy, change runtime canonical predicates, change Streamlit upload/manual ETL behavior, add write-capable Streamlit controls, modify `app.py`, run March 2026, or run a broad multi-month rehearsal.

## Evidence basis from B10.1-B10.4

| Stage | Evidence |
| --- | --- |
| B10.1 | November 2025 package to December 2025 canonical scope selected as the lowest-complexity accepted target boundary: `142` candidates, `44` candidate machines, `85` candidate orders, `489580.0` good quantity, no duplicate stable identities. |
| B10.2 | Read-only preflight reproduced the `142` candidates and found `7` workbook-level December overlaps requiring Bronze/hash proof. |
| B10.3 | Bronze/hash overlap proof classified the `7` workbook overlaps as not present in December target-package Bronze under the exact B10.3 key, but left `15` source-row-hash gaps. |
| B10.4 | Source-hash gap decision resolved the `15` gaps as `8` hash-resolved rows and `7` target duplicates to skip, with `0` unresolved blockers and no stable-identity fallback rows. |

## Temp DB boundary

The original runtime DB was copied only.

| Evidence point | Value |
| --- | --- |
| original DB | `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db` |
| original DB size before/after | `7226900480` / `7226900480` bytes |
| original DB mtime before/after | `1776434362` / `1776434362` |
| temp DB | `/tmp/leopaper_stage_b10_5_nov_dec_reconciliation/nov_dec_reconciliation.db` |
| temp DB size before/after | `7226900480` / `7226900480` bytes |
| temp DB SHA before mutation | `acf2faffb9ffa3e366b4440a50e62783c9bb22142d0d3ded75c9ea019fc40d26` |
| temp DB SHA after reconciliation | `1fa93c215582a572be28b47f513e3f0d5c4084f28878e1281a9adc3564c300aa` |
| temp DB inside GitHub-safe tree | `false` |
| temp DB inside original runtime repo | `false` |

## Approved include/skip/block plan

Command:

```text
python3.11 scripts/run_november_december_csi_carry_forward_reconciliation.py --target-db-path /tmp/leopaper_stage_b10_5_nov_dec_reconciliation/nov_dec_reconciliation.db
```

Approved plan reproduced before mutation:

| Plan item | Count |
| --- | ---: |
| total candidates | `142` |
| include | `135` |
| skip existing duplicate | `7` |
| block unresolved | `0` |
| B10.3 hash-proven include | `127` |
| B10.4 hash-resolved include | `8` |
| stable-identity fallback include | `0` |

The `8` B10.4 hash-resolved rows used null-equivalent matching for maintenance/null-quantity rows and recovered existing November-source `source_row_hash` values.
The `7` skipped rows were existing target duplicates and were not inserted.

## Reconciliation method

The script:

1. Reproduced the B10.4 approved plan from the copied temp DB.
2. Captured the `135` approved November-source raw rows before any baseline pruning.
3. Conservatively pruned December partitions in the temp DB only.
4. Ran one December 2025 historical canonical backfill against the temp DB to rebuild the December-only baseline.
5. Inserted only the `135` approved November-source carry-forward raw rows.
6. Refreshed December Silver and Gold materialization in the temp DB.
7. Rechecked raw/silver traceability and duplicate prevention.

The December baseline backfill used manifest-backed source discovery with readiness `ready`.

## Insert/skip/block evidence

| Evidence point | Result |
| --- | ---: |
| raw rows planned | `135` |
| raw rows inserted | `135` |
| skipped existing duplicates | `7` |
| unresolved candidates | `0` |
| source package month | `November 2025` |
| canonical event month | `2025-12` |
| carry-forward reason | `previous_package_timestamp_spill_to_target_month` |

Traceability after reconciliation:

| Surface | Matched | Unmatched |
| --- | ---: | ---: |
| raw `raw_csi_event` | `135` | `0` |
| silver `csi_job_event` | `135` | `0` |

## Duplicate-prevention evidence

| Surface | duplicate `source_row_hash` groups | duplicate stable-identity groups |
| --- | ---: | ---: |
| baseline raw `raw_csi_event` | `0` | `0` |
| baseline silver `csi_job_event` | `0` | `0` |
| after raw `raw_csi_event` | `0` | `0` |
| after silver `csi_job_event` | `0` | `0` |

The script also blocked insertion if any approved include row overlapped the rebuilt December baseline by `source_row_hash` or stable identity. No approved include overlap was found.

## Baseline comparison

The December-only baseline was rebuilt after pruning and before carry-forward insertion.

| Metric | Baseline | After reconciliation | Delta |
| --- | ---: | ---: | ---: |
| `raw_csi_event` December rows | `23047` | `23182` | `+135` |
| `csi_job_event` December rows | `23047` | `23182` | `+135` |
| `csi_job_event` good qty | `110458977.0` | `110948557.0` | `+489580.0` |
| affected machines from included rows | none | `39` | n/a |
| affected orders from included rows | none | `84` | n/a |

The pre-isolation copied DB had `23182` December raw and silver CSI rows because it already contained the November-source carry-forward rows. The controlled baseline reset intentionally pruned December partitions and rebuilt December from the December package before applying the approved carry-forward set.

## Gold / aggregate delta evidence

| Metric | Baseline | After reconciliation | Delta |
| --- | ---: | ---: | ---: |
| `fact_machine_hour` December rows | `63240` | `63240` | `0` |
| `fact_machine_hour.good_qty` | `100634237.0` | `101107494.0` | `+473257.0` |
| `fact_machine_hour.energy_total_kwh` | `1125948.3095` | `1125948.3095` | `0.0` |

The row count is unchanged because the December hour backbone already existed. The CSI quantity overlay changed after the `135` carry-forward rows were materialized into Silver and Gold.

## Safety evidence

- Original runtime DB size and mtime were unchanged.
- The target DB was `/private/tmp/leopaper_stage_b10_5_nov_dec_reconciliation/nov_dec_reconciliation.db`.
- No DB was written inside the GitHub-safe tree.
- No temp DB was promoted.
- March 2026 was not run.
- Runtime predicates were not changed.
- Source-discovery defaults were not changed.
- Model artifacts were not modified.
- `app.py` was not modified.

## Result verdict

Stage B10.5 passed as a temp-only reconciliation rehearsal.

The approved B10.4 plan was executed with:

```text
include 135 / skip 7 / block 0
```

All included candidates were traceable in raw and silver after reconciliation, and duplicate-prevention checks stayed at zero.

## What passed

- The approved plan reproduced before mutation.
- December-only baseline isolation and backfill succeeded.
- `135` approved raw carry-forward rows were inserted.
- December Silver and Gold were refreshed in the temp DB.
- Raw and silver traceability matched `135/135`.
- Duplicate source-hash and stable-identity groups remained `0`.
- The original runtime DB stayed unchanged by size and mtime.

## What failed or was deferred

No execution failure occurred.

Deferred by scope:

- live/shared DB promotion;
- runtime carry-forward wiring;
- schema-level permanent provenance fields;
- rollback execution beyond temp DB discardability;
- broad multi-month rehearsal.

## What remains unproven

Stage B10.5 does not prove:

- production runtime adoption readiness;
- live/shared DB write safety;
- operator rollback on a promoted DB;
- behavior for other month boundaries;
- March 2026 carry-forward handling;
- long-term provenance schema migration.

## Rollback / cleanup note

Rollback is to discard the temp DB:

```text
/tmp/leopaper_stage_b10_5_nov_dec_reconciliation/nov_dec_reconciliation.db
```

No live DB rollback is needed because the original runtime DB was not written and no temp DB was promoted.

## Recommended B10.6 or Stage B10 closeout

Recommended B10.6 should be a documentation and adoption-gate closeout, not runtime wiring.

It should consolidate B10.1-B10.5 evidence, define the minimum review criteria for any future disabled-by-default runtime hook, and explicitly preserve the live/shared DB promotion gate as a separate approval task.
