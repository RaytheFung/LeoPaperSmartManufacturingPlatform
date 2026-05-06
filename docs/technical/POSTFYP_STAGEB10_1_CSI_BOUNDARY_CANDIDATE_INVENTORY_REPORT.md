# Post-FYP Stage B10.1 CSI Boundary Candidate Inventory Report

## Purpose

Stage B10.1 builds a read-only inventory of CSI boundary-month candidates across accepted extension source packages before generalizing carry-forward beyond the July-to-August case.

The stage identifies source-package rows whose canonical event month differs from the source package month under the accepted first-available timestamp rule:

```text
production start -> production end -> preparation end -> shift date
```

## Scope

This stage adds `core/csi_boundary_inventory.py`, `scripts/inventory_csi_boundary_candidates.py`, and focused tests in `tests/test_csi_boundary_inventory.py`.

It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active runtime, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence basis from B9

Stage B9.2 proved the narrow July-to-August CSI carry-forward case in a temp DB:

| B9.2 evidence point | Result |
| --- | ---: |
| July-package candidates carried into August | `235` |
| raw rows inserted | `235` |
| silver rows reconciled | `235` |
| raw spill traceability | `235/235` |
| silver spill traceability | `235/235` |
| raw/silver duplicate source-hash groups | `0` |
| original runtime DB changed | `false` |

Stage B9.3 then defined the adoption gate: provenance, duplicate prevention, source selection, runtime adoption, and live/shared DB promotion must remain separate review gates before runtime wiring.

Stage B10.1 uses that evidence only as context. It does not repeat B9.2 execution and does not write any database.

## Inventory method

The inventory helper:

- resolves source packages through `config/source_manifest.v1.json` and `core.source_manifest_discovery`;
- uses the default extended raw dataset root from `core.runtime_paths.get_extended_raw_dataset_root()`;
- inspects only accepted extension CSI packages from July 2025 through February 2026;
- reads CSI workbooks with pandas using `.xls` support from the active Python 3.11 environment;
- computes canonical event month using production start, production end, preparation end, then shift date;
- classifies rows as same month, forward spill to next month, backward spill to previous month, or other/out-of-range;
- summarizes affected machines, orders, good quantity, timestamp ranges, source hash availability, and duplicate stable identity groups;
- returns structured evidence without creating DB files.

Source-row hashes are not directly present in the CSI source workbooks. Any later reconciliation stage must compute or prove source-row hashes through Bronze/raw payload handling, as B9.2 did.

## Source packages inspected

| Source package | Manifest CSI path | Status |
| --- | --- | --- |
| July 2025 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年7月.xls` | resolved |
| August 2025 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年8月.xls` | resolved |
| September 2025 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年9月.xls` | resolved |
| October 2025 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年10月.xls` | resolved |
| November 2025 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年11月.xls` | resolved |
| December 2025 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年12月.xls` | resolved |
| January 2026 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2026年1月.xls` | resolved |
| February 2026 | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2026年2月.xls` | resolved |

All eight packages resolved. The `.xls` reader emitted OLE/file-size warnings for the source files, but the workbooks were readable and no package was marked unresolved.

## Boundary candidate summary table

| Source package | Total rows | Boundary candidates | Forward | Backward | Other | Machines | Orders | Good qty | Candidate target |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| July 2025 | `24958` | `241` | `241` | `0` | `0` | `71` | `138` | `739769.0` | `2025-08` |
| August 2025 | `22579` | `180` | `180` | `0` | `0` | `49` | `89` | `598974.0` | `2025-09` |
| September 2025 | `20094` | `0` | `0` | `0` | `0` | `0` | `0` | `0.0` | none |
| October 2025 | `19422` | `252` | `252` | `0` | `0` | `72` | `141` | `1022013.0` | `2025-11` |
| November 2025 | `22690` | `142` | `142` | `0` | `0` | `44` | `85` | `489580.0` | `2025-12` |
| December 2025 | `23047` | `0` | `0` | `0` | `0` | `0` | `0` | `0.0` | none |
| January 2026 | `23181` | `217` | `217` | `0` | `0` | `70` | `123` | `920965.0` | `2026-02` |
| February 2026 | `12820` | `247` | `247` | `0` | `0` | `72` | `136` | `802574.0` | `2026-03` |

Inventory totals:

| Metric | Result |
| --- | ---: |
| packages inspected | `8` |
| resolved packages | `8` |
| unresolved packages | `0` |
| total CSI rows read | `168791` |
| total boundary candidates | `1279` |
| total forward spill candidates | `1279` |
| total backward spill candidates | `0` |
| total other/out-of-range candidates | `0` |

## Forward/backward spill classification

Every boundary candidate found in the accepted extension packages is a forward spill to the next month.

No backward spill candidates were found.
No other/out-of-range candidates were found inside the accepted July 2025 through February 2026 inspection set.

February 2026 has `247` forward candidates into March 2026, but March 2026 is not an accepted canonical package in the current manifest. That boundary is therefore not recommended for B10.2 under the current source-selection gate.

## Candidate selection rationale

The B10.2 recommendation applies these filters:

| Criterion | Required for recommendation |
| --- | --- |
| non-zero boundary candidates | yes |
| clear forward spill direction | yes |
| source package accepted | yes |
| target package accepted | yes |
| complete stable identity fields | yes |
| duplicate stable identity groups | lowest complexity first |
| candidate count | lowest count after duplicate complexity |

All accepted target-package forward cases had complete stable identity fields and zero duplicate stable identity groups in this raw-source inventory.

The lowest-count accepted target-package forward case is November 2025 package to December 2025 canonical scope:

| Recommendation evidence | Result |
| --- | --- |
| source package | November 2025 |
| target canonical month | December 2025 |
| candidate count | `142` |
| direction | forward spill to next month |
| affected machines | `44` |
| affected orders | `85` |
| good quantity sum | `489580.0` |
| duplicate stable identity groups | `0` |
| source package and target package accepted | `true` |
| source-row hash directly in workbook | `false` |

## Recommended B10.2 target boundary

Recommended B10.2 target:

```text
November 2025 source package -> December 2025 canonical month
```

B10.2 should be a read-only or temp-only preflight first. It should prove source-row-hash availability through Bronze/raw evidence and current December package overlap before any reconciliation rehearsal.

## What remains uncertain

- The July source-workbook inventory found `241` raw workbook rows that canonicalize to August, while B9 evidence used `235` ETL candidate identities. The good-quantity sum matches B9.2 at `739769.0`, so the difference likely reflects zero-quantity, filtering, or ETL-staging normalization details. This report does not resolve that difference because B10.1 does not run ETL or DB traceability.
- Source-row hashes are not direct workbook columns. Later stages must compute or prove them through raw Bronze handling.
- The inventory does not check current target-package overlap in a DB. B10.2 must do that read-only before any temp-only reconciliation.
- `.xls` reader warnings appeared during workbook reads. They did not block inventory, but they should remain visible as source-file quality context.
- February-to-March has candidates, but March 2026 remains outside accepted canonical scope.

## Runtime behavior impact

No runtime behavior changed.

The helper is read-only inventory code. It does not change source discovery defaults, ETL extraction, canonical predicates, DQ wiring, carry-forward runtime behavior, Streamlit UI behavior, model artifacts, or `app.py`.

## Tests run

Validation commands run for this stage:

```text
python3.11 -m unittest tests.test_csi_boundary_inventory
python3.11 scripts/inventory_csi_boundary_candidates.py
```

The full requested validation matrix was run after this report and docs index update; see the final terminal reply for exact pass/fail status.

## Unsafe file scan

Unsafe file checks were run before commit; see the final terminal reply for exact results.

B10.1 intentionally stages only code, tests, and documentation.
It does not stage DB, SQLite, raw Excel, generated `etl_outputs`, local environment folders, model artifacts, or `app.py`.

## Out of scope

- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- DB writes in the original runtime repo.
- DB writes in the GitHub-safe tree.
- Temp DB promotion.
- Runtime carry-forward wiring.
- Runtime source-discovery default changes.
- Runtime canonical predicate changes.
- DQ runtime behavior changes.
- ML retraining or artifact promotion.
- Raw Excel staging.
- Generated `etl_outputs` staging.
- `app.py` changes.
- Broad multi-month rehearsal.

## Recommended B10.2

Recommended B10.2 should target November 2025 source package to December 2025 canonical month with a controlled preflight:

1. Locate November and December CSI Bronze/raw evidence through manifest-backed source discovery.
2. Compute the `142` candidate stable identities using the same first-available timestamp rule.
3. Prove source-row-hash availability or define the exact fallback.
4. Check current December package overlap read-only.
5. Require zero duplicate raw/silver source-row-hash groups before any future temp-only reconciliation is accepted.
6. Keep runtime behavior disabled and unchanged.
