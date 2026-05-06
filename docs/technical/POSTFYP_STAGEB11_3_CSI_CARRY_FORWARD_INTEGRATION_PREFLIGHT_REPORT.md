# Post-FYP Stage B11.3 CSI Carry-Forward Integration Preflight Report

## Purpose

Stage B11.3 adds a read-only integration preflight adapter around the disabled-by-default CSI carry-forward configuration helper.

The goal is to prove that disabled mode is a no-op, `preflight_only` can route to read-only candidate/preflight planning, and `temp_reconcile` remains guarded and not executable through active runtime.

## Scope

This stage adds adapter code, focused tests, this technical report, the Stage B11 closeout report, and documentation index/contract updates.

It does not run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active ETL runtime, wire DQ rules into runtime behavior, modify `app.py`, add Streamlit write controls, or create live DB mode.

## Files changed

- `core/csi_carry_forward_runtime_adapter.py`
- `tests/test_csi_carry_forward_runtime_adapter.py`
- `docs/technical/POSTFYP_STAGEB11_3_CSI_CARRY_FORWARD_INTEGRATION_PREFLIGHT_REPORT.md`
- `docs/technical/POSTFYP_STAGEB11_CSI_CARRY_FORWARD_DISABLED_HOOK_CLOSEOUT_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`

## Runtime adapter behavior

The adapter exposes:

- `build_carry_forward_runtime_preflight()`
- `summarize_carry_forward_runtime_policy()`
- `assert_carry_forward_runtime_not_live()`
- `maybe_build_preflight_only_result()`

It imports only guardrail/config logic at module import time. Existing read-only preflight helpers are imported lazily only when the caller explicitly selects a supported `preflight_only` path that can use them.

## Disabled-mode behavior

Disabled mode returns a no-op policy result.

It does not require a source package month, target canonical month, or DB path. It does not inspect source files, open DB files, call preflight helpers, run ETL, run backfill, run materialization, run reconciliation, write files, or change runtime behavior.

## Preflight-only behavior

`preflight_only` validates:

- explicit source package month;
- explicit target canonical month;
- supported boundary allowlist.

It may route to read-only planning only. November 2025 -> December 2025 can use the existing workbook-based read-only preflight helper. July 2025 -> August 2025 remains accepted by the adapter, but the existing B9 helper requires an explicit existing temp DB path for Bronze evidence, so the adapter returns a not-run planning result when no DB path is supplied.

## Temp-reconcile guard behavior

`temp_reconcile` validates the mode, explicit source package month, explicit target canonical month, proven boundary allowlist, and explicit safe temp DB path.

It returns a guarded plan with status:

```text
guarded_not_executed
```

It does not execute reconciliation, call reconciliation scripts, run ETL, run backfill, run materialization, insert rows, or write a DB.

## Active runtime behavior impact

No active runtime behavior changed.

No active ETL call site imports or invokes the adapter. `ETLPipelineModule.run_historical_canonical_backfill()` behavior is unchanged. `ETLPipelineModule.resolve_historical_month_sources()` still defaults to `auto`. `core/canonical_materializer.py`, `core/silver_normalizer.py`, Streamlit routes, and `app.py` are unchanged.

## Tests run

Required validation is run after this report and docs update. See the terminal closeout for exact pass/fail status.

## Unsafe file scan

Unsafe file scans are run before commit. See the terminal closeout for exact results.

B11.3 intends to stage only the adapter module, adapter tests, the two reports, and documentation updates.

## Out of scope

- Active ETL runtime wiring.
- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- Carry-forward reconciliation execution.
- Live/shared DB writes.
- Live/shared DB promotion.
- Streamlit write controls.
- `app.py` changes.
- Source-discovery default changes.
- Runtime canonical predicate changes.
- DQ runtime wiring.
- ML retraining or artifact promotion.
- Raw Excel staging.
- Generated `etl_outputs` staging.

## Remaining risks

- The adapter is not active runtime wiring; a later stage must still review any integration point before use.
- July-to-August read-only preflight still needs an explicit existing temp DB for Bronze evidence.
- Permanent provenance schema and audit-table design remain unresolved.
- Live/shared DB rollback remains unproven and unapproved.
- Additional boundary months require separate proof before allowlist expansion.

## Recommended Stage B12

Recommended Stage B12 should be a read-only adoption review pack.

It should decide whether the disabled adapter is ready for a narrow runtime-adjacent integration point, identify any required provenance/audit schema, and keep live/shared DB promotion as a separate approval stage.
