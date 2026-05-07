# Post-FYP Stage B13 Factory Deployment DB Migration Decision Report

## Purpose

Stage B13 decides how the completed B5-B12 governance evidence should enter the next factory production deployment path.

The corrected objective is controlled factory deployment pilot readiness, not an FYP product review, local demonstration, or presentation-polish trial. This report decides whether factory deployment readiness work can continue without immediate live/shared DB migration or active runtime carry-forward adoption.

This is a decision, checklist, and deployment-readiness gate. It does not execute live migration or promote any temp evidence into runtime state.

## Scope

Stage B13 adds this decision report and supporting documentation updates only.

It does not run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation execution, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, execute live DB migration, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active ETL runtime, wire DQ rules into runtime behavior, modify `app.py`, add Streamlit write controls, or create live DB mode.

## Evidence basis from B5-B12

| Stage | Evidence basis | Factory deployment interpretation |
| --- | --- | --- |
| B5.3 | Source-discovery default switch is closed for accepted extension months. July 2025 through February 2026 use manifest-backed discovery by default; January 2025 through June 2025 remain legacy; March 2026 remains blocked. | Factory deployment planning can explain the accepted source boundary without expanding it. |
| B6.3-B6.4 | July historical backfill rehearsal and baseline isolation were temp-only, with the original runtime DB preserved and no DB inside Git. | Temp-only rehearsal is a safe validation boundary, not a live/shared DB promotion precedent. |
| B7.1-B7.3 | The July extracted-versus-canonical CSI gap is explained by `235` August spill rows, and all `235` identities are traceable under August raw and silver canonical scope in the audited temp DB. | Boundary-month CSI semantics are understood and reportable for operational review. |
| B8.2-B8.3 | August-only ingestion succeeds operationally in temp scope but does not recover the July-package spill identities; canonical completeness needs controlled carry-forward or adjacent-package reconciliation. | Factory deployment cannot silently claim boundary-month completeness without a governed reconciliation path. |
| B9.2-B9.3 | July 2025 package to August 2025 canonical carry-forward is proven temp-only for `235/235` raw and silver traceability with duplicate source-hash groups at `0`, but adoption gates remain separate. | Carry-forward is validated as a controlled capability, not active production runtime behavior. |
| B10.5-B10 closeout | November 2025 package to December 2025 canonical carry-forward is proven temp-only with `135` included, `7` skipped duplicates, `0` blocked, `135/135` raw and silver traceability, and duplicate groups at `0`. | A second boundary-month case proves the pattern is not one-off, while live/shared DB safety is still unproven. |
| B11 closeout | Disabled-by-default configuration scaffolding and a read-only adapter exist; disabled mode is the default no-op and no active ETL/runtime path is wired. | The deployment-safe stance is to keep carry-forward disabled until adoption gates are approved. |
| B12 closeout | Audit schema/workflow helpers and a temp-only rehearsal prove schema, representative audit rows, backup checksum, and restore validation under `/tmp`. | The audit workflow is blueprint/preflight evidence only; live/shared DB migration still needs a separate production-grade approval stage. |

## Current factory deployment readiness state

The project can move into controlled factory deployment pilot readiness work without immediate live/shared DB migration if that work is framed around deployment hygiene, operational runbooks, app smoke, and documented governance evidence.

This does not mean the local runtime DB is the final deployment state. The local runtime DB remains a safe rehearsal and review boundary until production-grade migration gates pass.

The current state is:

- source discovery for accepted extension months is documented and defaults to `auto_manifest`;
- March 2026 remains blocked and out of canonical scope;
- carry-forward is disabled-by-default;
- audit schema and workflow remain blueprint/preflight only;
- temp-only carry-forward evidence exists for two boundary cases;
- no live/shared DB migration or rollback execution has been approved;
- no active runtime adoption of carry-forward has been implemented;
- Stage C production-readiness cleanup, app smoke, deployment hygiene, and operational checklist work are still required.

## Live/shared DB migration decision

Decision: no live/shared DB migration is approved in Stage B13.

Live/shared DB migration is deferred, not abandoned. It remains part of the factory deployment roadmap, but only after a separate production-grade migration gate defines and accepts:

- exact migration SQL or an equivalent row-level write plan;
- pre-migration DB backup path, size, mtime, and checksum;
- dry-run SQL diff or row-count/write-scope proof;
- duplicate source-hash baseline;
- raw/silver traceability baseline;
- Gold aggregate delta review;
- rollback procedure and restore proof;
- reviewer acceptance;
- app/runtime smoke plan after migration;
- explicit abort criteria.

## Runtime carry-forward adoption decision

Decision: runtime carry-forward should not be enabled in Stage B13.

Carry-forward remains disabled-by-default because production adoption requires additional migration, provenance, rollback, operational approval, and post-migration smoke gates. It should be presented as validated governance/preflight capability supported by temp-only execution evidence, a disabled runtime adapter, and audit workflow rehearsal evidence.

It must not be presented as current active ETL, materialization, Streamlit, DQ, ML, or app behavior.

## Recommended factory deployment pilot readiness mode

Recommended mode: controlled factory deployment pilot readiness using the local runtime DB as a rehearsal boundary with no promoted DB writes.

The next readiness work should:

- launch and smoke the app from the reviewed branch or approved local runtime branch;
- keep `manufacturing_data.db` local-only until migration gates pass;
- avoid live/shared DB migration until the production migration gate is approved;
- avoid carry-forward execution until runtime adoption gates pass;
- explain source-discovery policy in the ETL diagnostic/reference surface;
- explain carry-forward as disabled-by-default and governance-ready;
- use B5-B12 reports as auditable supporting evidence;
- record app launch, route smoke, deployment hygiene, and operational checklist evidence during Stage C.

## Factory deployment readiness checklist

| Checklist item | Required state before controlled factory deployment pilot | B13 status |
| --- | --- | --- |
| Safe branch selected | Use a reviewed branch, not `main` direct work. | Required for Stage C readiness work. |
| DB local-only boundary clear | `manufacturing_data.db` remains local runtime state and outside Git. | Accepted as rehearsal boundary only. |
| No DB in Git | No `.db`, `.sqlite`, or `.sqlite3` file is staged or committed. | Required safety gate. |
| App launch smoke planned | Port/app route smoke should be run during Stage C readiness work. | Planned, not run by B13. |
| Source discovery default state explained | B5 default policy is documented: accepted extension months use manifest-backed discovery; Jan-Jun remain legacy; March 2026 remains blocked. | Accepted. |
| Carry-forward disabled state explained | B11 default mode remains `disabled`; adapter no-op behavior is documented. | Accepted. |
| Temp-only evidence reports available | B9.2, B10.5, B11, B12.3, and B12 closeout reports remain available. | Accepted. |
| Known deployment limitations documented | Live migration, rollback, runtime adoption, and full production audit insertion remain unproven. | Accepted. |
| Rollback not needed for B13 | No promoted DB write is performed, so no B13 runtime rollback is required. | Accepted. |
| Stage C cleanup required | Active-vs-legacy inventory, production-readiness cleanup, deployment hygiene, app smoke, and operational checklist remain necessary. | Required next stage. |

## Stage C entry criteria

Stage C can begin when all of the following are accepted:

- no active B-stage blocker remains for production-readiness cleanup;
- live/shared DB migration is explicitly gated rather than silently skipped;
- carry-forward disabled-by-default is accepted until a runtime adoption gate passes;
- audit schema remains blueprint/preflight only;
- source-discovery default policy remains unchanged from B5;
- runtime canonical predicates remain unchanged;
- no DB, raw Excel, model artifact, or generated `etl_outputs` file is staged;
- Stage C scope is limited to active-vs-legacy cleanup, app launch/route smoke, docs/readme cleanup, deployment hygiene, operational checklist, and future migration-gate preparation.

## What must remain disabled

The following must remain disabled or unimplemented for Stage B13 and Stage C readiness cleanup unless a later prompt explicitly reopens the boundary:

- runtime carry-forward execution;
- live/shared DB mode;
- temp DB promotion;
- active ETL carry-forward wiring;
- canonical materializer carry-forward wiring;
- Silver normalizer carry-forward changes;
- Streamlit carry-forward write controls;
- DQ runtime enforcement;
- ML retraining or artifact promotion;
- source-discovery default policy changes;
- runtime canonical predicate changes;
- live creation of audit schema tables in promoted runtime DB state.

## What evidence can be shown for factory deployment readiness

Factory deployment readiness work can show:

- B5 source-discovery governance and default policy;
- B7 extracted-versus-canonical CSI month-scope explanation;
- B8 evidence that August-only ingestion is operationally possible but not complete for boundary spill identities;
- B9 July-to-August carry-forward temp-only reconciliation evidence;
- B10 November-to-December carry-forward temp-only generalization evidence;
- B11 disabled-by-default runtime hook and no-op adapter evidence;
- B12 audit schema/workflow blueprint and temp-only backup/restore rehearsal evidence;
- app route smoke evidence after Stage C production-readiness cleanup;
- explicit DB local-only and no-promoted-write boundary;
- explicit migration, rollback, provenance, and operational approval gates still required before live/shared deployment.

## Risks accepted for controlled factory deployment pilot readiness

The readiness path accepts these risks because they are documented and do not require live/shared DB mutation:

- carry-forward is not active runtime behavior;
- boundary-month CSI completeness is explained through reports rather than promoted runtime data;
- audit schema exists as blueprint/preflight only;
- app launch/route smoke remains a Stage C production-readiness task;
- Stage C cleanup is still needed to reduce legacy-file confusion;
- the local runtime DB remains local-only rehearsal state rather than the final deployment state.

## Risks not accepted for operational deployment

The following are not accepted for operational deployment:

- live/shared DB migration without backup, checksum, rollback, reviewer acceptance, and post-migration app smoke;
- active runtime carry-forward without an approved runtime adoption gate;
- silent source-selection expansion into adjacent packages;
- carry-forward execution without duplicate-prevention and traceability evidence;
- Gold quantity changes without explicit delta review;
- DQ rule enforcement without a separate runtime wiring decision;
- ML artifact promotion without a separate validation and rollback gate.

## Recommended Stage C

Recommended Stage C should be production-readiness repo simplification and deployment hygiene.

It should focus on:

- active-vs-legacy file inventory;
- quarantine/archive of misleading legacy files;
- docs/readme cleanup;
- app launch and route smoke;
- deployment runbook and operational checklist;
- migration-gate checklist preparation;
- final branch hygiene and artifact safety scans.

Stage C should not reopen live DB migration or runtime carry-forward adoption unless a separate prompt explicitly changes the approved boundary.

## Out of scope

- Live/shared DB migration.
- Live migration SQL execution.
- Original runtime `manufacturing_data.db` writes.
- DB creation inside the GitHub-safe tree.
- Temp DB promotion.
- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- Carry-forward reconciliation execution.
- Runtime carry-forward wiring.
- DQ runtime wiring.
- Streamlit write controls.
- `app.py` changes.
- Source-discovery default changes.
- Runtime canonical predicate changes.
- ML retraining or artifact promotion.
- Raw Excel staging.
- Generated `etl_outputs` staging.
- `CURRENT_REBUILD_STATUS.md` update.

## Validation

B13 is documentation-only. The original B13 validation matrix passed with `0` failures in that run and wrote validation logs outside Git under `/tmp/leopaper_stage_b13_validation`.

B13.1 records the factory deployment alignment correction and its validation in `POSTFYP_STAGEB13_1_FACTORY_DEPLOYMENT_ALIGNMENT_REPORT.md`.

## Remaining risks

- Live/shared DB migration remains deferred and unproven.
- Live rollback remains untested because no live migration has been approved.
- Production audit record insertion for every proven carry-forward candidate remains unimplemented.
- Operator ownership for carry-forward review and archive/retention workflow remains a future governance decision.
- Stage C production-readiness cleanup, app smoke, deployment hygiene, and operational checklist work are still required.
