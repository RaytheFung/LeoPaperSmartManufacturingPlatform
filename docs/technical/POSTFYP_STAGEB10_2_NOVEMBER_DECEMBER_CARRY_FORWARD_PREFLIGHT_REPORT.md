# Post-FYP Stage B10.2 November-December Carry-Forward Preflight Report

## Purpose

Stage B10.2 builds a focused read-only carry-forward preflight for:

```text
November 2025 source package -> December 2025 canonical month
```

The goal is to prove candidate identities, source-row-hash availability where possible, current December overlap, duplicate risk, and the reconciliation plan before any temp-only reconciliation execution.

## Scope

This stage adds:

- `core/november_december_carry_forward_preflight.py`
- `scripts/preflight_november_december_csi_carry_forward.py`
- `tests/test_november_december_carry_forward_preflight.py`

It also creates this report and updates `docs/technical/REBUILD_DOCS_INDEX.md`.

This stage does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active runtime, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence basis from B10.1/B9

Stage B10.1 inventoried accepted extension CSI source packages and found:

| Evidence point | Result |
| --- | ---: |
| packages inspected | `8` |
| total CSI rows read | `168791` |
| total boundary candidates | `1279` |
| forward spill candidates | `1279` |
| backward spill candidates | `0` |
| other/out-of-range candidates | `0` |

Stage B10.1 recommended November-to-December because it was the lowest-count accepted-target forward spill with complete stable identity fields and zero duplicate stable identity groups.

Stage B9.2 proved the July-to-August carry-forward path in a temp DB only.
Stage B9.3 then required future carry-forward adoption to preserve provenance, prevent duplicates, separate source package month from canonical event month, prove source-row-hash behavior, and keep runtime wiring behind a later review gate.

## Candidate identity evidence

Command:

```text
python3.11 scripts/preflight_november_december_csi_carry_forward.py --json
```

Source package and target package:

| Point | Value |
| --- | --- |
| source package | November 2025 |
| target canonical month | December 2025 |
| source CSI file | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年11月.xls` |
| target CSI file | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年12月.xls` |
| source discovery | manifest-backed |
| ETL/backfill/materialization run | `false` |
| DB writes | `false` |

Candidate evidence:

| Metric | Result |
| --- | ---: |
| candidate count | `142` |
| expected B10.1 candidate count | `142` |
| candidate count matches B10.1 | `true` |
| distinct machines | `44` |
| distinct orders | `85` |
| good quantity sum | `489580.0` |
| min event timestamp | `2025-11-30 00:00:00` |
| max event timestamp | `2025-12-01 20:00:00` |
| canonical month distribution | `{"2025-12": 142}` |
| direction distribution | `{"forward_spill_to_next_month": 142}` |
| duplicate stable identity groups | `0` |
| duplicate stable identity rows | `0` |

Stable identity fields:

```text
machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty
```

All stable identity fields were present in the workbook-derived evidence.

The `.xls` reader emitted OLE/file-size warnings for the November and December workbooks, but both files were readable and the candidate count was reproduced.

## Source-row-hash / Bronze evidence

Source-row hashes are not direct columns in the November workbook.

| Evidence point | Result |
| --- | --- |
| source-row hash directly in workbook | `false` |
| workbook source-row-hash columns | none |
| November source DB path supplied | none |
| November Bronze/raw hash evidence checked | `false` |
| source-row-hash available from this preflight | `false` |

No November/December temp DB was supplied for this read-only preflight, and a quick `/tmp` scan did not identify a relevant November/December LeoPaper temp DB.

This means B10.2 proves workbook-level identity candidates only.
It does not prove source-row-hash availability or raw-to-silver traceability for November-to-December.

## Current December overlap check

The helper compared the `142` November-package December-canonical candidates against December package workbook identities.

| Overlap evidence | Result |
| --- | ---: |
| evidence strength | workbook identity only, weaker than Bronze |
| December canonical workbook row count | `23047` |
| candidate overlap count | `7` |
| overlap row count | `7` |
| workbook overlap status | `overlap_found` |
| December Bronze/raw DB path supplied | none |
| Bronze/raw overlap checked | `false` |

This is a material B10.2 finding.
The current December package appears to contain `7` stable identities that match November-package carry-forward candidates at workbook level.

Because this is workbook identity evidence only, it is not strong enough to decide insertion or skipping.
B10.3 must prove whether those `7` overlaps are true Bronze/source-row-hash duplicates, normalized identity collisions, or workbook-level artifacts before any temp-only reconciliation.

## Reconciliation strategy

A future reconciliation stage should:

1. Treat November-package rows whose canonical event month is December 2025 as previous-package carry-forward candidates.
2. Preserve `source_package_month=November 2025` separately from `canonical_event_month=2025-12`.
3. Use `source_row_hash` from Bronze/raw evidence when available.
4. Use the stable identity only as a reviewed fallback if source-row-hash evidence is unavailable.
5. Reject or explicitly resolve any candidate overlapping current December package evidence.
6. Run only against a temp DB outside Git and outside the original runtime repo.
7. Keep runtime source discovery, canonical predicates, materialization, DQ wiring, Streamlit behavior, and ML artifacts unchanged.

## Duplicate-prevention plan

Before any future write, require:

- zero duplicate stable identity groups in the candidate set;
- explicit resolution of the `7` workbook-level December overlaps;
- source-row-hash proof from Bronze/raw evidence if available;
- duplicate `source_row_hash` groups blocked in `raw_csi_event` for December canonical scope;
- duplicate `source_row_hash` groups blocked in `csi_job_event` after Silver materialization;
- stable-identity duplicate blocking if source-row-hash evidence is unavailable;
- post-run raw and silver traceability proof for all included candidates;
- documented skips for every candidate not included.

Stage B10.2 result:

| Duplicate-prevention metric | Result |
| --- | ---: |
| candidate duplicate stable identity groups | `0` |
| candidate duplicate stable identity rows | `0` |
| workbook-level December overlap candidates | `7` |
| source-row hash proof | not available |
| automatic temp reconciliation readiness | blocked pending Bronze overlap/hash proof |

## Abort criteria

Abort any future reconciliation if:

- November source package is unreadable or missing required CSI columns;
- December target package is unreadable or missing required CSI columns;
- candidate count cannot be reproduced;
- duplicate stable identity groups are nonzero;
- current December package overlap is nonzero or ambiguous without an approved tie-breaker;
- stable identity fields are missing;
- source-row hash is unavailable and no safe fallback is approved;
- any DB path is inside the GitHub-safe tree, inside the original runtime repo, missing, or not opened read-only;
- any future step would run ETL, backfill, materialization, write a DB, promote a temp DB, or change runtime behavior without separate approval.

## What remains unproven

Stage B10.2 does not prove:

- November Bronze/raw source-row-hash availability;
- November raw-to-silver traceability;
- December Bronze/raw overlap counts;
- whether the `7` workbook-level overlaps are true duplicates or normalized workbook artifacts;
- any temp-only insertion/reconciliation behavior;
- Gold aggregate deltas;
- runtime adoption readiness;
- live/shared DB promotion readiness.

## Runtime behavior impact

No runtime behavior changed.

The B10.2 helper is read-only preflight code.
It does not change source discovery defaults, ETL extraction, canonical predicates, DQ wiring, carry-forward runtime behavior, Streamlit UI behavior, model artifacts, or `app.py`.

## Tests run

Validation commands run for this stage:

```text
python3.11 -m unittest tests.test_november_december_carry_forward_preflight
python3.11 scripts/preflight_november_december_csi_carry_forward.py --json
```

The full requested validation matrix was run after this report and docs index update; see the final terminal reply for exact pass/fail status.

## Unsafe file scan

Unsafe file checks were run before commit; see the final terminal reply for exact results.

B10.2 intentionally stages only code, tests, and documentation.
It does not stage DB, SQLite, raw Excel, generated `etl_outputs`, local environment folders, model artifacts, or `app.py`.

## Recommended B10.3

Recommended B10.3 should be a read-only Bronze/hash and overlap proof for November-to-December before any temp-only reconciliation:

1. Prepare or locate a temp DB outside Git that contains November and December Bronze/raw CSI evidence, or create a temp-only read path under an explicit no-promotion boundary.
2. Match the `142` November-package candidates to raw `source_row_hash` values.
3. Check the `7` workbook-level December overlaps against raw and silver `source_row_hash` plus stable identity.
4. Classify each overlap as true duplicate, safe skip, or ambiguous.
5. Produce a candidate inclusion/skip plan for a later temp-only reconciliation.
6. Do not run reconciliation until overlap and source-row-hash evidence is accepted.
