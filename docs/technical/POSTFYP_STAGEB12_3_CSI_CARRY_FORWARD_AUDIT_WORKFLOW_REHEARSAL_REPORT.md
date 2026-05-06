# Post-FYP Stage B12.3 CSI Carry-Forward Audit Workflow Rehearsal Report

## Purpose

Stage B12.3 runs a temp-only CSI carry-forward audit workflow rehearsal and closes the implementation proof loop started by B12.1 and B12.2.

The goal is to prove that the B12.1 audit schema and B12.2 workflow helper can be applied to a real SQLite temp DB under `/tmp`, with representative audit records, backup/checksum evidence, and restore validation, without touching the live/original runtime DB.

## Scope

This stage adds a temp-only rehearsal script, focused tests, this report, a Stage B12 closeout report, and documentation index/contract updates.

It does not run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation execution, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, execute live DB migration, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active ETL runtime, wire DQ rules into runtime behavior, modify `app.py`, add Streamlit write controls, or create live DB mode.

## Temp DB boundary

The rehearsal script is:

```text
scripts/rehearse_csi_carry_forward_audit_workflow.py
```

The default rehearsal paths are under `/tmp/leopaper_stage_b12_3_audit_workflow/`.
On macOS these resolve to `/private/tmp/...`.

The rehearsal refuses DB paths outside `/tmp`, inside the GitHub-safe repo, or inside the original runtime repo.

## Audit schema applied

The rehearsal applied the B12.1 schema to the temp DB and created:

- `csi_carry_forward_audit_runs`
- `csi_carry_forward_candidates`
- `csi_carry_forward_gold_deltas`

Schema validation returned valid with all required columns present.

## Sample audit records inserted

The rehearsal inserted representative records for the proven November 2025 source package -> December 2025 canonical month case:

| Record type | Count |
| --- | ---: |
| audit run | `1` |
| candidate records | `3` |
| include decisions | `2` |
| skip decisions | `1` |
| block decisions | `0` |
| Gold delta records | `1` |

The sample audit run ID is:

```text
cfaudit_november_2025_to_december_2025_b12_3_temp_rehearsal
```

Workflow count validation matched expected and actual candidate/include/skip/block counts.

## Reviewer status used

The rehearsal used reviewer status:

```text
accepted
```

This validates the workflow path for a reviewed sample record without approving live/shared DB migration.

## Backup/checksum evidence

The rehearsal copied the temp audit DB to a backup DB under `/tmp` and verified that the backup checksum matched the temp DB checksum.

The validation command output records the exact SHA-256 values for the run. No backup was created inside the GitHub-safe tree.

## Rollback/restore rehearsal evidence

The rehearsal restored the backup into a separate temp DB path under `/tmp` and validated:

- restored checksum matches backup checksum;
- restored schema is valid;
- restored workflow counts are valid.

This proves the audit workflow rehearsal DB can be restored and revalidated in temp scope.

## Abort gates exercised or documented

Tests exercised path refusal for:

- repo-local DB path;
- original-runtime DB path.

The rehearsal evidence also carries documented abort gate IDs from B12.2:

- missing backup;
- failed checksum;
- duplicate source hash groups;
- unresolved candidate decisions;
- unexpected Gold deltas;
- app smoke failure;
- unsafe DB path;
- reviewer status not accepted;
- migration touches tables outside plan.

## Live DB migration boundary

No live DB migration was run.

The original runtime DB was not opened for mutation, no DB was written inside the GitHub-safe tree, and no temp DB was promoted.

## Runtime behavior impact

No runtime behavior changed.

The rehearsal script is standalone and is not wired into active ETL, historical backfill, canonical materialization, Silver normalization, Streamlit, source discovery, DQ runtime behavior, or ML code paths. It does not change CSI canonical predicates and does not execute carry-forward reconciliation.

## Tests run

Required validation is run after this report and docs update. See the terminal closeout for exact pass/fail status.

## Unsafe file scan

Unsafe file scans are run before commit. See the terminal closeout for exact results.

B12.3 intends to stage only the rehearsal script, rehearsal tests, the B12.3 report, the B12 closeout report, and documentation updates.

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

## Remaining risks

- The rehearsal uses representative sample audit records, not full production carry-forward evidence rows.
- Live/shared DB migration, restore execution against a promoted DB, and app runtime smoke after migration remain unproven.
- Reviewer workflow ownership and archive/retention operations remain future governance decisions.

## Recommended Stage B13

Recommended Stage B13 should decide whether to proceed to a live/shared DB migration design gate or keep the audit schema as temp-only evidence tooling.

If migration is considered, B13 should require a reviewed migration script, live DB backup path, checksum proof, rollback procedure, app/runtime smoke plan, reviewer acceptance, and explicit refusal criteria before any promoted DB write.
