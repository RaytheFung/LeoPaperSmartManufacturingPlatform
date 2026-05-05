# Post-FYP Stage B7.2 CSI Month-Assignment Policy Decision Report

## Purpose

Stage B7.2 records the policy decision for CSI canonical month assignment after the Stage B7.1 July spill-row audit.
It exists to prevent the July extracted-row versus canonical-row difference from being misread as data loss, a duplicate issue, or a runtime predicate defect before broader multi-month rehearsal work.

## Scope

This is a documentation and policy stage.
It adds this decision report, updates the rebuild docs index, and records a short data-contract note.
It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB in the GitHub-safe tree, promote a temp DB, retrain or promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## B7.1 evidence summary

Stage B7.1 audited the July 2025 CSI row-count gap from the Stage B6.4 temp-only clean-baseline run:

| Evidence point | Result |
| --- | --- |
| `etl_csi_data` July extracted/staging rows | `24,952` |
| canonical `raw_csi_event` July rows | `24,717` |
| canonical `csi_job_event` July rows | `24,717` |
| extracted-minus-canonical delta | `235` |
| excluded-row canonical month | `2025-08` |
| affected CSI machine IDs | `70` |
| affected order IDs | `138` |
| excluded-row good quantity sum | `739,769.0` |
| duplicate raw canonical source-row-hash groups | `0` |
| duplicate silver canonical source-row-hash groups | `0` |
| duplicate ETL July signature groups | `0` |

B7.1 concluded that the `235` excluded rows are legitimate August spill rows outside canonical July scope.
The gap is not a duplicate/hash issue and not a raw-versus-silver predicate mismatch.

## Current CSI canonical month rule

Current canonical materialization assigns CSI rows to a canonical month using first-available timestamp semantics.

For Bronze `raw_csi_event`, the month expression is:

```sql
COALESCE(
  substr(raw_start_time, 1, 7),
  substr(raw_end_time, 1, 7),
  substr(raw_prep_end_time, 1, 7),
  substr(json_extract(raw_payload_json, '$.班次內日期'), 1, 7)
)
```

For Silver `csi_job_event`, the month expression is:

```sql
COALESCE(
  substr(prod_start_ts, 1, 7),
  substr(prod_end_ts, 1, 7),
  substr(prep_end_ts, 1, 7),
  substr(shift_date, 1, 7)
)
```

The operational interpretation is:

- use production start month when production start exists;
- otherwise use production end month;
- otherwise use prep-end month;
- otherwise use shift-date month.

This rule is narrower than source-package extraction scope.
Source-package extraction can include rows from a selected July source package, while canonical materialization assigns each event to a canonical month by timestamp semantics.

## Policy decision

Accept the current first-available timestamp canonical month-assignment policy for Stage B7.

The accepted policy is:

- Treat extracted rows beyond the canonical month as source-package spill rows.
- Do not change runtime canonical predicates in Stage B7.2.
- Do not reinterpret the July `235` row gap as data loss.
- Require future multi-month rehearsal reports to show extracted row count, canonical row count, and spill-row count explicitly.
- Require an August follow-up to verify whether the July-package spill rows are captured under August canonical scope or otherwise remain traceable.

This is a hold-and-document decision, not a permanent guarantee that the predicate is the best long-term business rule.

## Accepted explanation of extracted-vs-canonical row difference

Use this explanation for reports, demos, and reviewer discussion:

ETL extraction may load rows from the source file package selected for July.
Canonical materialization assigns each CSI event to a canonical month using timestamp semantics.
Therefore extracted July package rows can exceed canonical July rows.
The Stage B7.1 `235` row gap is not data loss if those rows belong to August canonical scope.
Future August rehearsal must verify that the spill rows are captured under August scope or remain traceable through audit evidence.

## Why runtime predicate is not changed now

The current predicate is not changed in Stage B7.2 because B7.1 did not find a defect requiring a narrow fix.
Raw canonical July and silver canonical July both returned `24,717` rows with the same good quantity sum.
Duplicate source-row-hash and ETL signature checks did not indicate duplicate contamination.
The excluded rows consistently resolved outside July under the current first-available timestamp rule.

Changing runtime predicates now would expand scope from policy decision to canonical behavior migration.
That would require broader month-by-month evidence, downstream Gold impact analysis, compatibility review for historical reports, and an explicit rollback plan.

## Required future evidence

Future CSI month-scope evidence must include:

- extracted source-package row count by month and source family;
- canonical Bronze row count by month and source family;
- canonical Silver row count by month and source family;
- extracted-minus-canonical row delta;
- spill-row count and canonical-month classification;
- affected machine count, order count, good quantity sum, and timestamp range;
- duplicate/hash evidence where source hashes are available;
- a clear statement of whether spill rows are expected, accepted, unresolved, or a blocker.

The next August rehearsal must specifically test whether the July-package `235` August-resolving rows appear under August canonical scope or remain traceable through audit evidence.

## Impact on future multi-month rehearsal

Future multi-month rehearsal reports must not compare extracted CSI package rows and canonical CSI rows as if they are required to be equal.
They must separate:

- source package extraction scope;
- ETL staging month label;
- Bronze canonical month predicate;
- Silver canonical month predicate;
- Gold month partition effects.

For accepted extension months, row-count tables should include an explicit extracted-versus-canonical delta column.
If a source package carries spill rows, the report should identify their canonical month and state whether the delta is acceptable under the B7.2 policy.

## Risk if misunderstood

If this boundary is misunderstood, reviewers may incorrectly conclude that:

- July lost `235` CSI rows during canonical materialization;
- raw and silver predicates disagree;
- duplicate or source-row-hash behavior is corrupt;
- the ETL source-discovery default switch changed runtime semantics;
- broader predicate changes are needed before proving where spill rows land.

The correct interpretation is narrower: B7.1 proved the July delta is an extracted-source versus canonical-month boundary under current CSI timestamp semantics.

## Out of scope

- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- Runtime canonical predicate changes.
- Source-discovery default-policy changes.
- DQ rule runtime wiring.
- Live or temp DB promotion.
- ML retraining or model artifact promotion.
- Streamlit UI changes.
- `app.py` changes.
- August materialization proof.
- Permanent business-policy redesign for CSI month assignment.

## Validation

Validation for this stage is documentation-focused plus the required regression set.
No runtime code or test helper was added because the B7.1 audit helper already provides a pure `classify_csi_row_scope()` test for the first-available timestamp classification and no clean runtime helper needed extraction.

Required validation was run before commit:

- `python3.11 -m unittest tests.test_july_csi_spill_audit_safety`
- `python3.11 -m unittest tests.test_temp_backfill_rehearsal_safety`
- `python3.11 -m unittest tests.test_backfill_rehearsal_preflight`
- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface tests.test_source_discovery_default_switch`
- `python3.11 -m unittest tests.test_source_discovery_post_switch_audit tests.test_source_discovery_stage_b5_closeout`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

## Remaining risks

- B7.2 accepts the current policy for now but does not prove that first-available timestamp semantics are the best permanent business rule.
- B7.2 does not prove August capture of the `235` July-package spill rows.
- `etl_csi_data` does not store shift date, so ETL-stage spill summaries cannot fully report shift-date month without joining back to raw payload evidence.
- Future report readers can still misread extracted package rows as canonical month rows unless row-count tables keep the distinction explicit.

## Recommended B7.3

Recommended Stage B7.3 should be an August-focused read-only or temp-only traceability plan.
It should verify whether the July-package `235` August-resolving spill rows appear under August canonical scope or remain otherwise traceable, while preserving the no-live-DB-promotion and no-runtime-predicate-change boundary unless a separate approved task opens that scope.
