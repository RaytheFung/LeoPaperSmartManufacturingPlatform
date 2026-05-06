# Post-FYP Stage B10.3 November-December Bronze/Hash Overlap Proof Report

## Purpose

Stage B10.3 builds a read-only Bronze/hash overlap proof for the November 2025 source package to December 2025 canonical month carry-forward candidate set.

The goal is to classify the `7` workbook-level December overlaps found in B10.2 and produce an include/skip/unresolved plan for all `142` candidates before any temp-only reconciliation execution.

## Scope

This stage adds:

- `core/november_december_overlap_proof.py`
- `scripts/prove_november_december_csi_overlap.py`
- `tests/test_november_december_overlap_proof.py`

It also creates this report and updates `docs/technical/REBUILD_DOCS_INDEX.md`.

This stage does not run ETL, run historical backfill, run canonical materialization, execute carry-forward reconciliation, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active runtime, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence basis from B10.2

Stage B10.2 reproduced:

| B10.2 point | Result |
| --- | ---: |
| candidate count | `142` |
| distinct machines | `44` |
| distinct orders | `85` |
| good quantity sum | `489580.0` |
| duplicate stable identity groups | `0` |
| workbook-level December overlaps | `7` |
| source-row-hash availability | unproven |

B10.2 blocked automatic reconciliation because workbook-level overlap was weaker than Bronze evidence and source-row-hash availability was unproven.

## DB evidence source

No existing November/December LeoPaper temp DB was found under `/tmp`.

Following the B10.3 fallback path, the original runtime DB was copied to:

```text
/tmp/leopaper_stage_b10_3_nov_dec_overlap/nov_dec_overlap.db
```

Safety evidence:

| Point | Result |
| --- | --- |
| original DB source | `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db` |
| temp DB evidence path | `/private/tmp/leopaper_stage_b10_3_nov_dec_overlap/nov_dec_overlap.db` |
| original DB size | `7226900480` bytes |
| temp DB size | `7226900480` bytes |
| original DB mtime | `Apr 17 21:59:22 2026` |
| temp DB mtime | `Apr 17 21:59:22 2026` |
| DB opened by proof script | SQLite read-only URI |
| DB written by proof script | `false` |

The proof script refuses DB paths inside the GitHub-safe repo and inside the original runtime repo.

## Candidate identity reproduction

Command:

```text
python3.11 scripts/prove_november_december_csi_overlap.py --db-path /tmp/leopaper_stage_b10_3_nov_dec_overlap/nov_dec_overlap.db --json
```

Candidate reproduction:

| Metric | Result |
| --- | ---: |
| candidate count | `142` |
| expected B10.2 candidate count | `142` |
| candidate count matches B10.2 | `true` |
| distinct machines | `44` |
| distinct orders | `85` |
| good quantity sum | `489580.0` |
| duplicate stable identity groups | `0` |

The `.xls` reader emitted OLE/file-size warnings for the November and December CSI workbooks, but both files were readable.

## Workbook-level overlap reproduction

The B10.2 workbook overlap was reproduced:

| Metric | Result |
| --- | ---: |
| workbook-level overlap count | `7` |
| expected B10.2 overlap count | `7` |
| overlap count matches B10.2 | `true` |

## Bronze/raw/silver overlap proof

The copied temp DB contained the required tables:

| Table | Available |
| --- | --- |
| `raw_csi_event` | `true` |
| `csi_job_event` | `true` |

December canonical scope evidence:

| Metric | Result |
| --- | ---: |
| raw December canonical rows | `23182` |
| silver December canonical rows | `23182` |
| raw November-source candidate-scope rows | `135` |
| raw December-current target-scope rows | `23047` |
| silver November-source candidate-scope rows | `135` |
| silver December-current target-scope rows | `23047` |
| candidates with raw source-hash match | `127` |
| candidates with target raw/silver identity match | `0` |

The `135 + 23047 = 23182` split shows that the copied DB already contains December-canonical rows from both November-source and December-source provenance surfaces.

## Classification of the 7 overlaps

All `7` workbook-level overlaps were classified as:

```text
workbook_artifact_not_present_in_bronze
```

Classification summary:

| Classification | Count |
| --- | ---: |
| workbook artifact / not present in Bronze | `7` |
| true duplicate already present | `0` |
| same identity but different provenance/hash | `0` |
| unresolved | `0` |

For each of the `7`, the stable identity was not present in current December Bronze/Silver target-package scope.
That means the workbook-level overlap does not represent a December Bronze/Silver duplicate in the copied DB.

## Include/skip/unresolved plan for 142 candidates

Plan summary:

| Decision | Count |
| --- | ---: |
| include | `142` |
| skip true duplicate | `0` |
| unresolved/block | `0` |
| total candidates | `142` |

Classification count for all candidates:

| Classification | Count |
| --- | ---: |
| workbook artifact / not present in Bronze | `142` |

The include plan means no candidate is already present in December current-package Bronze/Silver target scope by stable identity.
It does not yet mean execution is safe, because source-row-hash proof is incomplete.

## Source-row-hash evidence

Source-row-hash evidence:

| Metric | Result |
| --- | ---: |
| candidate source-hash matched count | `127` |
| candidate source-hash unmatched count | `15` |
| target hash matched candidate count | `0` |
| source-row hash available for all candidates | `false` |

This is the key remaining blocker.
The copied DB proves source-row-hash evidence for `127/142` candidates but leaves `15` candidate identities without source-row-hash proof.

## Whether B10.4 execution is safe

B10.4 temp-only reconciliation execution is not yet safe.

Safety decision:

```text
safe_for_b10_4_temp_reconciliation = false
```

Reason:

```text
15 candidate identities do not yet have source-row-hash evidence; a reviewed fallback or source-hash proof is required before execution.
```

The `7` workbook overlaps are resolved as not present in Bronze/Silver target scope, but the `15` source-hash gaps prevent an execution-ready include plan.

## Abort criteria

Abort any future reconciliation if:

- DB path is inside the GitHub-safe repo or original runtime repo;
- DB path is missing or cannot be opened read-only;
- November/December source workbooks cannot be read;
- candidate count cannot be reproduced as `142`;
- workbook overlap cannot be reproduced as `7`;
- duplicate stable identity groups become nonzero;
- any target-package Bronze/Silver overlap remains true duplicate, different-hash, or unresolved without approved include/skip handling;
- any source-row-hash gap lacks an approved fallback;
- any future task would run ETL, backfill, materialization, DB writes, temp DB promotion, or runtime changes without separate approval.

## What remains unproven

Stage B10.3 does not prove:

- carry-forward insertion;
- canonical materialization after insertion;
- post-run raw/silver traceability;
- duplicate source-hash groups after insertion;
- Gold aggregate deltas;
- how to safely handle the `15` source-row-hash gaps;
- runtime adoption readiness;
- live/shared DB promotion readiness.

## Runtime behavior impact

No runtime behavior changed.

The helper and script are read-only proof tooling.
They do not change source discovery defaults, ETL extraction, canonical predicates, DQ wiring, carry-forward runtime behavior, Streamlit behavior, model artifacts, or `app.py`.

## Tests run

Validation commands run for this stage:

```text
python3.11 -m unittest tests.test_november_december_overlap_proof
python3.11 scripts/prove_november_december_csi_overlap.py --db-path /tmp/leopaper_stage_b10_3_nov_dec_overlap/nov_dec_overlap.db --json
```

The full requested validation matrix was run after this report and docs index update; see the final terminal reply for exact pass/fail status.

## Unsafe file scan

Unsafe file checks were run before commit; see the final terminal reply for exact results.

B10.3 intentionally stages only code, tests, and documentation.
It does not stage DB, SQLite, raw Excel, generated `etl_outputs`, local environment folders, model artifacts, or `app.py`.

## Recommended B10.4

Recommended B10.4 should not execute reconciliation yet.

The next stage should be a narrow source-hash gap resolution / fallback decision for the `15` candidates without source-row-hash evidence:

1. List the `15` source-hash-gap identities explicitly.
2. Determine whether they are non-production maintenance rows, source normalization artifacts, or missing Bronze evidence.
3. Decide whether stable-identity fallback is acceptable for those `15`.
4. Only after that decision, prepare a temp-only reconciliation execution plan with `127` hash-proven candidates plus the approved handling for the `15` gaps.
