# Post-FYP Stage B9.3 CSI Carry-Forward Adoption Gate Report

## Purpose

Stage B9.3 defines the adoption design and review gate for CSI boundary-month carry-forward after the successful Stage B9.2 temp-only reconciliation rehearsal.
It converts the B9.2 execution evidence into a provenance contract, duplicate-prevention contract, source-selection boundary, runtime adoption gate, and live/shared DB promotion gate.

This is a governance and design stage only.
It does not wire carry-forward behavior into production runtime.

## Scope

This stage adds this adoption-gate report and updates the rebuild docs index.

It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, retrain or promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire carry-forward into active runtime, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## B9.2 evidence summary

Stage B9.2 proved the narrow July-to-August 2025 carry-forward path in a temp DB only.

| Evidence point | Result |
| --- | ---: |
| candidate count | `235` |
| raw rows inserted | `235` |
| silver rows reconciled | `235` |
| raw spill traceability | `235/235` |
| silver spill traceability | `235/235` |
| raw/silver duplicate source-hash groups | `0` |
| raw CSI August row delta versus B8.2 | `+235` |
| silver CSI August row delta versus B8.2 | `+235` |
| `csi_job_event` good qty delta | `+739769.0` |
| `fact_machine_hour` row count delta | `0` |
| `fact_machine_hour` good qty delta | `+687151.0` |
| original runtime DB changed | `false` |
| DB/raw/model/generated artifacts staged | `false` |

B9.2 also kept the runtime boundary clean:

- the original runtime DB was copied only and stayed unchanged by size and mtime;
- the execution target was `/tmp/leopaper_stage_b9_2_carry_forward/august_carry_forward.db`;
- no temp DB was promoted;
- no runtime canonical predicate changed;
- no source-discovery default policy changed;
- no `app.py` change was made;
- March 2026 was not run.

## Provenance contract

Any future permanent carry-forward implementation must store enough provenance to distinguish source-package origin from canonical event assignment.
The permanent contract should include these fields or equivalent auditable metadata:

| Field | Required meaning |
| --- | --- |
| `source_package_month` | Month label of the source package that physically carried the row, for B9.2 `July 2025`. |
| `canonical_event_month` | Month key assigned by timestamp semantics, for B9.2 `2025-08`. |
| `carry_forward_from_package` | Previous package included into the target canonical month, for B9.2 `July 2025`. |
| `carry_forward_reason` | Controlled reason code, for example `previous_package_timestamp_spill_to_target_month`. |
| `source_row_hash` | Existing raw source hash, preserved unchanged across raw and silver surfaces. |
| `stable_identity_key` | Composite CSI identity: `machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty`. |
| `original_raw_payload_reference` | Pointer to the original raw payload or source-file path used to reconstruct the row. |
| `target_canonical_month` | Target month key selected for reconciliation, for B9.2 `2025-08`. |
| `reconciliation_run_id` | Audit identifier tying the candidate set, duplicate checks, and post-run evidence together. |
| `reconciliation_audit_id` | Optional durable audit row or report identifier for review and rollback traceability. |

Contract rules:

- `source_row_hash` semantics must not be redefined.
- A carry-forward row remains a source-provenance row from its original package, not a same-month package row.
- The canonical event month remains timestamp-based.
- Reports must separate identity-level proof from raw-row provenance counts.
- If multiple source-file path variants represent the same identity, one canonical provenance path must be selected or the duplicate path variants must be explicitly deduplicated before inclusion.

## Duplicate-prevention contract

Future adoption must enforce duplicate prevention before any write and verify it after any temp or live execution.

Required checks:

1. Block duplicate `source_row_hash` in `raw_csi_event` for target canonical scope.
2. Block duplicate `source_row_hash` in `csi_job_event` after silver materialization.
3. If `source_row_hash` is unavailable, block duplicate stable CSI identity.
4. Reject ambiguous candidates where multiple raw rows share the same stable identity and no approved source-hash or source-path tie-breaker exists.
5. Distinguish identity-level proof from raw-row provenance counts, especially when a temp DB contains absolute-path and repo-relative path variants for the same source row.
6. Preserve existing `source_row_hash` values rather than minting new hashes for carry-forward copies.
7. Abort if a candidate overlaps the current package by hash or stable identity unless a separate reviewer-approved rule resolves the conflict.

Post-run checks:

- duplicate raw CSI source-hash groups for target month must equal `0`;
- duplicate silver CSI source-hash groups for target month must equal `0`;
- carried-forward identity count must equal expected candidate count or every skipped identity must have a documented reason;
- raw-to-silver traceability must be proven by `source_row_hash`;
- Gold aggregate deltas must be explained against the previous temp-only baseline.

## Source-selection boundary

For target month `M`, a future carry-forward helper may inspect:

1. package `M`, the current target package;
2. package `M-1`, the previous package, for CSI rows whose timestamp canonical month equals `M`;
3. package `M+1` only if later evidence proves rows can canonicalize backward into `M` and the review gate explicitly opens that scope.

The source-selection boundary must not:

- change the first-available timestamp CSI canonical month semantics;
- assign source package month as canonical event month;
- silently include adjacent packages without reporting the boundary reason;
- change source-discovery default policy without a separate approved stage;
- widen to broad multi-month ingestion as a side effect of a target-month run.

Recommended target-month evidence should always report:

- source package month;
- target canonical month;
- previous-package candidate count;
- current-package overlap count;
- source-row-hash availability;
- raw/silver duplicate group counts;
- Gold row-count and aggregate deltas.

## Runtime adoption gate

Runtime wiring is not approved by B9.3.
Before any production runtime wiring, all of the following must pass:

| Gate item | Required status |
| --- | --- |
| July-to-August temp rehearsal | passed, as shown by B9.2 |
| One additional boundary-month temp rehearsal, if data is available | passed or explicitly blocked with evidence |
| Duplicate raw/silver source-hash groups | `0` |
| Raw carry-forward identities matched | all expected or documented skips |
| Silver carry-forward identities matched | all expected or documented skips |
| Gold delta | explained with row-count and aggregate evidence |
| Live DB write boundary | no live writes during rehearsal |
| Rollback plan | documented and tested for the intended write surface |
| Reviewer acceptance | explicit approval of provenance, duplicate, source-selection, and rollback contracts |

Runtime wiring, if later approved, should start disabled by default behind an explicit operator or configuration gate.
The default path must remain unchanged until the review gate accepts the feature.

## Live/shared DB promotion gate

Live/shared DB promotion must not happen in Stage B9.
It requires a separate task and a separate approval record.

Minimum promotion requirements:

1. A migration plan that names every table and column touched.
2. A verified DB backup with path, size, mtime, and checksum.
3. A dry-run SQL diff or equivalent row-level write plan.
4. A rollback script or deterministic rollback procedure.
5. Pre-write and post-write duplicate source-hash checks.
6. Pre-write and post-write raw/silver traceability checks.
7. Gold aggregate delta report.
8. App/runtime smoke test plan.
9. Reviewer sign-off before execution.
10. A no-force-push, no-main-push branch and review boundary for code changes.

No temp DB from B9.1 or B9.2 is eligible for promotion.

## Recommended next stage

Recommended Stage B10: generalize the temp-only carry-forward preflight and reconciliation helper to one more boundary month if source evidence is available.

This recommendation chooses the conservative path over live/shared DB promotion.
The next stage should prove whether the July-to-August pattern repeats elsewhere before any runtime adoption decision.

If no additional boundary month has usable evidence, B10 should instead define a disabled-by-default runtime hook design without enabling it, including config names, call sites, abort criteria, and test fixtures.

## Why runtime is not changed now

Runtime is not changed because B9.2 proves one concrete boundary case, not a complete production adoption contract.
Carry-forward affects source selection, Bronze provenance, Silver normalization, duplicate prevention, Gold aggregates, review reports, and rollback procedures.

Immediate runtime wiring would still risk:

- applying July-to-August assumptions to unproven month boundaries;
- hiding source-package versus canonical-month distinctions;
- introducing duplicate identities if current and adjacent packages overlap differently in another month;
- changing Gold quantities without an accepted operational review gate;
- creating live DB rollback risk before the provenance contract is approved.

## Risks

- A future boundary month may show different overlap behavior than July-to-August.
- Some packages may lack sufficient raw hash or identity evidence for safe carry-forward.
- Permanent provenance fields may require schema or audit-table design work.
- A disabled-by-default runtime hook can still add maintenance complexity if added before enough temp evidence exists.
- Gold aggregate deltas may need stakeholder review because row-count deltas and quantity deltas do not move identically.

## Out of scope

- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- Runtime carry-forward implementation.
- Source-discovery default changes.
- Runtime canonical predicate changes.
- DQ runtime wiring.
- Live/shared DB promotion.
- ML retraining or artifact promotion.
- Streamlit UI changes.
- `app.py` changes.
- March 2026 execution.
- Broad multi-month rehearsal.

## Validation

B9.3 is documentation-only.
The required validation set was run to prove that the B9.2 helper and existing safety surfaces still pass:

- `python3.11 -m unittest tests.test_csi_carry_forward_reconciliation_safety`
- `python3.11 -m unittest tests.test_csi_carry_forward_preflight`
- `python3.11 -m unittest tests.test_august_temp_backfill_rehearsal_safety`
- `python3.11 -m unittest tests.test_august_csi_spill_traceability_safety`
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

- Runtime adoption remains unimplemented.
- Live/shared DB promotion remains unapproved.
- Additional boundary-month evidence is still needed before generalizing from July-to-August.
- Permanent provenance storage is not yet designed as a schema migration.
- Reviewer acceptance is still required before any default behavior changes.
