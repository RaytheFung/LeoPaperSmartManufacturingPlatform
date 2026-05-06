# Post-FYP Stage B10.4 November-December Source-Hash Gap Decision Report

## Purpose

Stage B10.4 resolves the `15` November 2025 package to December 2025 canonical-month carry-forward candidates that lacked `source_row_hash` evidence in Stage B10.3.

This is a read-only proof and policy decision stage before any B10.5 temp-only reconciliation execution.

## Scope

This stage adds:

- `core/november_december_hash_gap_decision.py`
- `scripts/resolve_november_december_source_hash_gaps.py`
- `tests/test_november_december_hash_gap_decision.py`

It also creates this report and updates `docs/technical/REBUILD_DOCS_INDEX.md`.

This stage does not run ETL, run historical backfill, run canonical materialization, run reconciliation execution, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active runtime, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence basis from B10.3

Stage B10.3 proved:

| Evidence point | Result |
| --- | ---: |
| candidate count | `142` |
| workbook-level overlaps reproduced | `7/7` |
| workbook overlap classification under exact B10.3 key | `7` workbook artifacts not present in Bronze |
| include/skip/unresolved plan under exact B10.3 key | include `142` / skip `0` / unresolved `0` |
| source-row-hash matched | `127/142` |
| source-row-hash unmatched | `15/142` |

B10.3 therefore blocked execution until the `15` source-hash gaps were resolved or a reviewed fallback was approved.

## The 15 source-hash gap candidates

Command:

```text
python3.11 scripts/resolve_november_december_source_hash_gaps.py --db-path /tmp/leopaper_stage_b10_4_hash_gap/nov_dec_hash_gap.db
```

The helper opened `/private/tmp/leopaper_stage_b10_4_hash_gap/nov_dec_hash_gap.db` with a SQLite read-only URI. The DB is outside the GitHub-safe tree and outside the original runtime repo. The November and December `.xls` readers emitted OLE/file-size warnings, but the workbooks were readable and the candidate counts reproduced.

| # | Machine | Start | End | Order | B10.4 class | Evidence hash |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `D-024-090` | `2025-12-01 06:29:57` | `2025-12-01 07:21:25` | `日保養` | `hash_resolved` | source `6c000404e6b1684f150074e83c69edf3136ec1bf7c04afc913eb7f172163dbc3` |
| 2 | `D-024-124` | `2025-12-01 06:58:50` | `2025-12-01 07:42:53` | `計劃保養` | `hash_resolved` | source `bbd7242ee54bea6a48e7f0c2fbe8269f3eb2d769f2fbc3b96888e501cdc72d29` |
| 3 | `D-024-074` | `2025-12-01 05:59:34` | `2025-12-01 08:00:00` | `日保養` | `hash_resolved` | source `a589b04890b79991d8aa62a080e0e3b6643c6589ecb44e115f7803cbad602d97` |
| 4 | `D-024-085` | `2025-12-01 10:42:17` | `2025-12-01 20:00:00` | `月保養` | `skip_due_existing_duplicate` | target `a2546a459e4dc6cef92fa6313790a10c360d5dc08d8c91e3bd67680cb5e0b3f5` |
| 5 | `D-024-145` | `2025-12-01 01:59:53` | `2025-12-01 05:43:07` | `日保養` | `hash_resolved` | source `bc893d318b809de94995127ef585994e25f373affeb793d4269d83f0368f8df6` |
| 6 | `D-024-072` | `2025-12-01 08:17:54` | `2025-12-01 08:49:36` | `日保養` | `skip_due_existing_duplicate` | target `9423bc4c1fbb6b7bf0aac0b31db35d27317bcfd5a544d141ae37eab56db4d3b9` |
| 7 | `D-024-069` | `2025-12-01 01:34:43` | `2025-12-01 06:20:23` | `日保養` | `hash_resolved` | source `5ae0f1a608e9f3228a466b515f0f33ba0e3ae71eb7823f7f02ab7e9bf66cbb25` |
| 8 | `D-024-143` | `2025-12-01 06:17:19` | `2025-12-01 07:43:51` | `日保養` | `hash_resolved` | source `37db9e5a3ce1d6d321609d7274006b9e05b555800f0722ec9f7ecc11174659e9` |
| 9 | `D-024-144` | `2025-12-01 09:31:00` | `2025-12-01 13:15:40` | `日保養` | `skip_due_existing_duplicate` | target `9fdb817871622f3bc54c0224276a14bcf973f2d766fcd2e313860ccda0ed3405` |
| 10 | `D-024-140` | `2025-12-01 02:47:59` | `2025-12-01 05:24:45` | `日保養` | `hash_resolved` | source `9fa96daa85054f4eaab8fafac84e4c6e1890a8ecc40095c8e5e81065859885aa` |
| 11 | `D-024-074` | `2025-12-01 08:31:04` | `2025-12-01 09:38:43` | `月保養` | `skip_due_existing_duplicate` | target `4741567ac8de541e89265bc8e2dcf5f2934e7a1953ad067fe3ad9139463b85b3` |
| 12 | `D-024-109` | `2025-12-01 08:11:37` | `2025-12-01 13:23:03` | `計劃保養` | `skip_due_existing_duplicate` | target `3b124b92412ca2a336fc4ebc2b4b2eb5fed574dc4a0c166bb231894983acd7d5` |
| 13 | `D-024-089` | `2025-12-01 09:01:00` | `2025-12-01 09:43:37` | `日保養` | `skip_due_existing_duplicate` | target `8e68e6118ff114d73598f509a261e8df438f3420f93f63f6e6febeb33c1a997c` |
| 14 | `D-024-063` | `2025-12-01 11:07:13` | `2025-12-01 20:00:00` | `計劃保養` | `skip_due_existing_duplicate` | target `56f4161b75ef70e80732de8aca1133015c81ee15d72f22967e28e0f60d292acc` |
| 15 | `D-024-120` | `2025-12-01 06:01:43` | `2025-12-01 07:46:11` | `日保養` | `hash_resolved` | source `340a312d71a2d671fcce365e4cc19102675b02dd8fcbf057b2ca9970435552e8` |

All `15` candidates are maintenance or planned-maintenance rows with `NULL` material and `NULL` good quantity in the DB-normalized surfaces.

## Root-cause classification

| Root cause | Count | Decision |
| --- | ---: | --- |
| `null_material_good_qty_normalization_mismatch` | `8` | Include as hash-resolved; relaxed null-equivalent matching recovered November-source `source_row_hash` evidence. |
| `existing_target_duplicate_after_null_equivalent_matching` | `7` | Skip; relaxed null-equivalent matching found December target-package raw/silver evidence with `source_row_hash`. |

No candidate remained `block_unresolved`.

## Alternative matching attempts

B10.4 tried these read-only alternatives:

- timestamp normalization to second precision;
- trimmed string normalization for machine, order, material, and quantity fields;
- null-equivalent handling for workbook `NaN` versus database `NULL`;
- raw payload fingerprinting where matched raw rows exposed `raw_payload_json`;
- canonical stable identity only as a reviewed fallback.

Results:

| Attempt result | Count |
| --- | ---: |
| source hash recovered by null-equivalent identity | `8` |
| stable-identity fallback safe | `0` |
| existing target duplicate to skip | `7` |
| block unresolved | `0` |

The successful match did not mint or fabricate any `source_row_hash`. It either recovered an existing November-source hash or found an existing December-target hash that makes insertion unsafe for that candidate.

## Fallback policy decision

Stable-identity fallback is not required for B10.5.

Policy:

```text
fallback_policy = not_required_with_duplicate_skips
```

Reason:

- `8` source-hash gaps recover real source-row-hash evidence after safe normalization.
- `7` source-hash gaps are existing target duplicates and must be skipped.
- `0` candidates require stable-identity-only insertion.
- `0` candidates remain blocked.

## Include/skip/block plan

| Plan item | Count |
| --- | ---: |
| B10.3 hash-proven include | `127` |
| B10.4 hash-resolved include | `8` |
| stable-identity fallback include | `0` |
| skip existing duplicate | `7` |
| block unresolved | `0` |
| total candidates | `142` |

The B10.5 candidate insertion set should therefore be `135` rows, not `142`.

## Execution safety decision

B10.5 temp-only execution can proceed only under the B10.4 decision above.

Safety decision:

```text
safe_for_b10_5_temp_reconciliation = true
```

This means B10.5 is safe to design as a temp-only execution that inserts only the `135` include candidates and excludes the `7` target duplicates.

It does not approve live/shared DB writes, temp DB promotion, runtime wiring, source-discovery default changes, canonical predicate changes, DQ runtime wiring, ML retraining, or broad multi-month rehearsal.

## Duplicate-prevention requirements for B10.5

B10.5 must:

- reject any candidate whose `source_row_hash` already exists in `raw_csi_event` or `csi_job_event` for December canonical scope;
- exclude all `7` `skip_due_existing_duplicate` identities from insertion;
- insert no stable-identity-only fallback row unless a later report explicitly approves that fallback;
- prove duplicate `source_row_hash` groups are zero in raw and silver after temp-only execution;
- report the `127` B10.3 hash-proven rows, `8` B10.4 hash-resolved rows, and `7` skipped duplicate rows separately;
- prove post-run raw and silver traceability for every included candidate.

## What remains unproven

Stage B10.4 does not prove:

- carry-forward insertion;
- canonical materialization after insertion;
- post-run raw/silver traceability for the `135` include set;
- duplicate source-hash groups after insertion;
- Gold aggregate deltas;
- rollback behavior;
- runtime adoption readiness;
- live/shared DB promotion readiness.

## Runtime behavior impact

No runtime behavior changed.

The helper and script are read-only proof tooling. They do not change source discovery defaults, ETL extraction, canonical predicates, DQ wiring, carry-forward runtime behavior, Streamlit behavior, model artifacts, or `app.py`.

## Tests run

Focused commands run while preparing this report:

```text
python3.11 -m unittest tests.test_november_december_hash_gap_decision
python3.11 scripts/resolve_november_december_source_hash_gaps.py --db-path /tmp/leopaper_stage_b10_4_hash_gap/nov_dec_hash_gap.db
```

The full required validation matrix is run after this report and docs index update; see the final terminal reply for exact pass/fail status.

## Unsafe file scan

Unsafe file checks are run before commit; see the final terminal reply for exact results.

B10.4 intentionally stages only code, tests, and documentation. It does not stage DB, SQLite, raw Excel, generated `etl_outputs`, local environment folders, model artifacts, or `app.py`.

## Recommended B10.5

Recommended B10.5 should be a temp-only November-to-December carry-forward reconciliation execution with this exact gate:

1. Copy or use an explicit temp DB outside Git and outside the original runtime repo.
2. Reproduce the `142` candidate set and the B10.4 `135` include / `7` skip / `0` block plan before any write.
3. Insert only the `135` include candidates.
4. Preserve source-package provenance and existing `source_row_hash` values.
5. Materialize only in the temp DB if the B10.5 prompt explicitly opens that execution scope.
6. Prove raw/silver traceability and duplicate source-hash groups after execution.
7. Keep runtime behavior and live/shared DB state unchanged.
