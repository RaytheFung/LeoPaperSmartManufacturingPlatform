# Post-FYP Stage B11.1 CSI Carry-Forward Runtime Hook Design Report

## Purpose

Stage B11.1 designs a future disabled-by-default runtime hook for CSI boundary-month carry-forward.

This is a design report only. It converts the B9 and B10 temp-only evidence into a proposed configuration, call-site, provenance, duplicate-prevention, source-selection, rollback, test, and abort contract for later review.

## Scope

This stage creates a design boundary for future implementation.

It does not implement runtime wiring, run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire DQ rules into runtime behavior, modify `app.py`, or create Streamlit write controls.

## Design goal

The design goal is to make carry-forward available only as an explicit, auditable, temp-safe flow.

The future hook should support preflight and temp reconciliation for a named target month while preserving current runtime defaults unless an operator or task explicitly selects a non-default mode in code or configuration.

## Disabled-by-default principle

Carry-forward must default to disabled.

Default behavior:

```text
carry_forward_mode = "disabled"
```

In disabled mode:

- no adjacent source package is added to runtime source selection;
- no carry-forward preflight is executed;
- no carry-forward reconciliation is executed;
- no DB mutation occurs;
- canonical predicates remain timestamp-based;
- source-discovery defaults remain unchanged;
- Streamlit runtime behavior remains unchanged.

Any non-disabled mode must be explicit and visible in returned diagnostics.

## Proposed configuration flag names

Proposed flags for a future implementation:

| Flag | Default | Allowed values | Purpose |
| --- | --- | --- | --- |
| `carry_forward_mode` | `disabled` | `disabled`, `preflight_only`, `temp_reconcile` | Selects whether the hook is inactive, evidence-only, or temp-reconciliation-capable. |
| `carry_forward_target_month` | none | explicit month label, for example `December 2025` | Names the target canonical month. Required for non-disabled modes. |
| `carry_forward_source_package_month` | none | explicit adjacent package label, for example `November 2025` | Names the source package that may spill into the target month. Required for non-disabled modes. |
| `carry_forward_target_db_path` | none | explicit path | Required for `temp_reconcile`; must be outside Git and outside the original runtime repo. |
| `carry_forward_require_existing_plan` | `true` | `true`, `false` | Requires the approved candidate plan to be reproduced before mutation. Should remain `true` for B11. |
| `carry_forward_allow_live_db` | `false` | `false` only in B11 | Documents that live/shared DB mode is unavailable in B11. |

No B11 mode may permit live/shared DB writes.

## Proposed call sites

Proposed future call sites are design-only:

| Layer | Proposed boundary | B11.1 decision |
| --- | --- | --- |
| `modules.etl_module.ETLPipelineModule.run_historical_canonical_backfill()` | Optional preflight hook before or after source resolution for a single explicit month. | Do not wire in B11.1. Future B11.2 may add a disabled default parameter only. |
| `core.canonical_materializer.CanonicalMaterializer.materialize_backfill_month()` | Optional temp-only reconciliation gate before Silver/Gold refresh. | Do not wire in B11.1. Future work must avoid changing timestamp predicates. |
| `core.silver_normalizer.SilverNormalizer` | Provenance-preserving normalization verification for carried raw CSI rows. | Do not wire in B11.1. Existing `source_row_hash` semantics remain unchanged. |
| `scripts/run_*_csi_carry_forward_reconciliation.py` | Existing temp-only rehearsal scripts provide the reference implementation shape. | Keep as explicit scripts until a reviewed runtime hook exists. |
| Streamlit `app.py` and ETL page controls | No write-capable carry-forward control. | Out of scope for B11. |

The lowest-risk future implementation is a helper boundary called from scripts first, then optionally exposed to runtime code behind `carry_forward_mode="disabled"` by default.

## Proposed helper boundaries

A future helper should be separated into three layers:

| Helper layer | Responsibility | Write behavior |
| --- | --- | --- |
| inventory/preflight | Reproduce boundary candidates, overlap evidence, source-row-hash availability, and candidate plan. | Read-only. |
| plan approval | Classify include, skip, and block rows; require zero unresolved blockers. | Read-only. |
| temp reconciliation | Apply only the approved include set to an explicit temp DB, refresh target Silver/Gold, and report deltas. | Temp DB only. |

The helper must refuse:

- DB paths inside the GitHub-safe tree;
- DB paths inside the original runtime repo;
- missing explicit target month;
- missing explicit source package month;
- missing explicit temp DB path in `temp_reconcile` mode;
- live/shared DB paths;
- broad multi-month implicit scope;
- unresolved blockers;
- duplicate source-hash or stable-identity gate failures.

## Required provenance contract

Any future implementation must preserve enough provenance to distinguish where a row came from and where timestamp semantics assign it.

Required provenance fields or equivalent audit metadata:

| Field | Required meaning |
| --- | --- |
| `source_package_month` | Physical package month carrying the source row. |
| `canonical_event_month` | Timestamp-derived target canonical month. |
| `carry_forward_from_package` | Adjacent package whose row is being included. |
| `target_canonical_month` | Explicit target month for the run. |
| `carry_forward_reason` | Controlled reason code such as `previous_package_timestamp_spill_to_target_month`. |
| `source_row_hash` | Existing raw source hash, preserved unchanged. |
| `stable_identity_key` | Composite identity: machine, start, end, prep end, order, material, and good quantity. |
| `source_file` or payload reference | Existing source provenance path or raw payload reference. |
| `reconciliation_run_id` | Audit identifier for the preflight, insertion, traceability, and rollback evidence. |

The helper must not mint replacement `source_row_hash` values for carry-forward rows.

## Required duplicate-prevention contract

Duplicate prevention must happen before any temp insertion and be verified after any temp reconciliation.

Before insertion:

- reproduce the candidate set for the explicit target month;
- confirm candidate duplicate stable-identity groups are zero or fully resolved;
- reject any include candidate whose `source_row_hash` already exists in target raw or silver scope;
- reject any stable-identity fallback candidate unless a prior report explicitly approved the fallback;
- skip candidates classified as existing target duplicates;
- block the run if any candidate remains unresolved.

After insertion and materialization:

- duplicate `source_row_hash` groups in `raw_csi_event` for target scope must be `0`;
- duplicate `source_row_hash` groups in `csi_job_event` for target scope must be `0`;
- duplicate stable-identity groups in raw and silver target scope must be `0`;
- raw traceability must match every included candidate;
- silver traceability must match every included candidate;
- skipped candidates must stay documented and not be inserted.

## Required source-selection boundary

Runtime predicates remain timestamp-based.

For target month `M`, the helper may inspect:

- the current target package `M`;
- the previous package `M-1` for rows whose canonical event month equals `M`;
- the next package `M+1` only if a later stage proves backward spill behavior and explicitly opens that scope.

The helper must not:

- change source-discovery default policy;
- silently widen historical source discovery;
- treat source package month as canonical event month;
- include adjacent packages without a boundary reason;
- run broad multi-month ingestion as a side effect of a target-month request;
- include March 2026 unless a later accepted-source decision reopens that boundary.

## Required rollback behavior

B11 allows no live DB mode.

For `temp_reconcile`, rollback is temp DB discardability:

- the target DB path must be outside Git and outside the original runtime repo;
- the helper must record temp DB path, size, mtime, and checksum before mutation;
- the helper must record the same evidence after reconciliation;
- the original runtime DB must be copied only and verified unchanged when used as the seed;
- no temp DB may be promoted by the helper.

Any future live/shared DB mode requires a separate approval stage with backup, SQL/write plan, rollback script, pre/post traceability checks, Gold deltas, runtime smoke, and reviewer sign-off.

## Required temp-only rehearsal before enabling

Before any runtime hook moves beyond disabled design, a future stage must run a temp-only rehearsal through the proposed hook path.

Required evidence:

- explicit source package month and target canonical month;
- reproduced candidate count;
- include, skip, and block plan;
- raw and silver traceability;
- raw and silver duplicate source-hash groups;
- stable-identity duplicate groups;
- Gold row-count and aggregate deltas;
- original runtime DB size and mtime unchanged;
- no DB inside the GitHub-safe tree;
- no temp DB promotion.

## Test strategy

Future B11.2 tests should cover configuration and refusal behavior before any runtime adoption.

Required tests:

- `carry_forward_mode="disabled"` returns unchanged behavior;
- invalid mode names fail fast;
- `preflight_only` requires explicit target and source package months;
- `temp_reconcile` requires an explicit temp DB path;
- helper refuses DB paths inside the GitHub-safe tree;
- helper refuses DB paths inside the original runtime repo;
- helper refuses live/shared DB paths;
- helper refuses non-explicit or broad multi-month scope;
- helper blocks unresolved candidates;
- helper blocks duplicate `source_row_hash` overlap;
- helper reports include, skip, and block counts separately;
- helper does not expose Streamlit write controls.

Regression tests should continue to run the B9 and B10 safety suites so the existing temp-only rehearsal scripts remain stable.

## Abort criteria

Abort any future implementation or rehearsal if:

- `carry_forward_mode` is not explicit and non-default;
- target month is missing;
- source package month is missing;
- DB path is inside the GitHub-safe tree;
- DB path is inside the original runtime repo;
- DB path points at the live/shared runtime DB;
- candidate count cannot be reproduced;
- include, skip, and block plan cannot be reproduced;
- block count is nonzero;
- duplicate source-hash groups are nonzero;
- duplicate stable-identity groups are unresolved;
- raw or silver traceability does not match included candidates;
- Gold deltas cannot be explained;
- source-discovery defaults would change;
- runtime canonical predicates would change;
- Streamlit write controls would be added;
- temp DB promotion is requested.

## Out of scope

- Runtime carry-forward implementation.
- Live/shared DB writes.
- Live/shared DB promotion.
- Streamlit controls.
- `app.py` changes.
- Source-discovery default changes.
- Runtime canonical predicate changes.
- DQ runtime wiring.
- ML retraining or artifact promotion.
- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- Broad multi-month carry-forward.
- March 2026 carry-forward.

## Recommended B11.2

Recommended B11.2 should implement configuration scaffolding and refusal tests only.

The implementation should add disabled-by-default flags and pure helper routing without enabling runtime execution. It should prove that disabled mode preserves existing behavior and that non-disabled modes refuse unsafe scope, unsafe DB paths, missing target months, unresolved candidate plans, and live/shared DB writes.

B11.2 should not add live DB mode, Streamlit write controls, source-discovery default changes, canonical predicate changes, DQ runtime wiring, or temp DB promotion.
