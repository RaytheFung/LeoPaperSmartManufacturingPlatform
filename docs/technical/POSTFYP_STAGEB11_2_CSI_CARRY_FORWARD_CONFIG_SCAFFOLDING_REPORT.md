# Post-FYP Stage B11.2 CSI Carry-Forward Config Scaffolding Report

## Purpose

Stage B11.2 implements disabled-by-default CSI carry-forward configuration scaffolding and refusal guardrails.

The goal is to turn the B11.1 design boundary into a small pure helper module and focused tests without wiring carry-forward into active ETL, canonical materialization, Streamlit, source discovery defaults, DQ runtime behavior, live/shared DB behavior, or reconciliation execution.

## Scope

This stage adds configuration and guardrail code only.

It does not run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active ETL runtime, wire DQ rules into runtime behavior, modify `app.py`, add Streamlit write controls, or create live DB mode.

## Files changed

- `core/csi_carry_forward_config.py`
- `tests/test_csi_carry_forward_config.py`
- `docs/technical/POSTFYP_STAGEB11_2_CSI_CARRY_FORWARD_CONFIG_SCAFFOLDING_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`

## Configuration model

The new module defines:

- `CarryForwardMode.DISABLED`
- `CarryForwardMode.PREFLIGHT_ONLY`
- `CarryForwardMode.TEMP_RECONCILE`
- `DEFAULT_CARRY_FORWARD_MODE = "disabled"`
- `CarryForwardConfig`
- `build_default_carry_forward_config()`
- mode, boundary, target-month, live-mode, and temp-DB path validators

The module has no Streamlit dependency and performs no DB writes.

## Disabled-by-default behavior

The default config is:

```text
mode = "disabled"
```

Disabled mode is not enabled, does not require a target month or source package month, and does not imply any adjacent-package source selection, reconciliation execution, or DB mutation.

`require_disabled_by_default()` rejects non-disabled defaults.

## Supported modes

Supported mode strings are:

| Mode | Meaning | Write behavior |
| --- | --- | --- |
| `disabled` | Carry-forward is inactive. | none |
| `preflight_only` | Future read-only candidate discovery may be allowed with explicit source and target months. | none |
| `temp_reconcile` | Future temp-only helper/script execution may be allowed with explicit source, target, and temp DB path. | temp DB only |

Unsupported mode strings raise `ValueError`.

## Temp DB guardrails

`validate_temp_db_path()` refuses:

- DB paths inside the GitHub-safe repo;
- DB paths inside the original runtime repo;
- paths without `.db`, `.sqlite`, or `.sqlite3` suffixes.

It accepts temp DB paths such as `/tmp/.../*.db` without creating the file.

## Boundary allowlist

The default allowlist is based only on proven temp-only evidence:

| Source package month | Target canonical month | Evidence |
| --- | --- | --- |
| `July 2025` | `August 2025` | B9.2 temp-only reconciliation |
| `November 2025` | `December 2025` | B10.5 temp-only reconciliation |

The allowlist is used by guardrails and tests only. It is not wired into production ETL behavior.

## Refusal behavior

The scaffolding refuses:

- unknown modes;
- live/shared DB mode names such as `live_db`;
- `allow_live_db=True`;
- missing target month for non-disabled modes;
- missing source package month for non-disabled modes;
- unsupported source-package to target-canonical-month boundaries;
- repo-local DB paths;
- original-runtime-repo DB paths;
- `temp_reconcile` without an explicit target DB path.

## Runtime behavior impact

No runtime behavior changed.

No active ETL call site imports or invokes the new configuration module. No canonical materializer or Silver normalizer path changed. Source-discovery defaults and timestamp-based canonical predicates remain unchanged. Streamlit behavior remains unchanged.

## Tests run

Required validation is run after this report and docs update. See the terminal closeout for exact pass/fail status.

## Unsafe file scan

Unsafe file scans are run before commit. See the terminal closeout for exact results.

B11.2 intends to stage only the new guardrail module, its tests, this report, and the two documentation index/contract updates.

## Out of scope

- Runtime carry-forward wiring.
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

- The helper is not yet integrated into temp-only reconciliation scripts or active runtime call sites.
- Permanent provenance schema and audit-table design remain unresolved.
- Live/shared DB rollback remains unproven because B11.2 does not approve live mode.
- Additional boundary months may require separate proof before allowlist expansion.

## Recommended B11.3

Recommended B11.3 should add a read-only integration preflight around the new configuration helper.

It should prove that `disabled` mode preserves existing behavior and that `preflight_only` can route to candidate discovery without DB writes, ETL execution, materialization, Streamlit controls, source-discovery default changes, or runtime predicate changes.

B11.3 should not enable `temp_reconcile` in active runtime and should not introduce live/shared DB mode.
