# Post-FYP Stage B10 CSI Carry-Forward Generalization Closeout Report

## Purpose

Stage B10 closes the first generalization pass for CSI boundary-month carry-forward.

The goal was to prove whether the July-to-August carry-forward pattern from Stage B9 repeats on at least one additional accepted boundary month before any runtime hook, live/shared DB write, source-discovery default change, canonical predicate change, or Streamlit behavior change is considered.

## Scope

This closeout consolidates the completed Stage B10.1 through B10.5 evidence.

It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active runtime, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## B10.1 summary

B10.1 inventoried accepted extension CSI source packages from July 2025 through February 2026 and found that every boundary candidate was a forward spill to the next canonical month.

Inventory evidence:

| Evidence point | Result |
| --- | ---: |
| packages inspected | `8` |
| resolved packages | `8` |
| total CSI rows read | `168791` |
| total boundary candidates | `1279` |
| forward spill candidates | `1279` |
| backward spill candidates | `0` |
| other/out-of-range candidates | `0` |

B10.1 recommended November 2025 package to December 2025 canonical scope because it was the lowest-count accepted-target forward case with complete stable identity fields and zero duplicate stable identity groups.

## B10.2 summary

B10.2 built a read-only November-to-December carry-forward preflight.

Preflight evidence:

| Evidence point | Result |
| --- | ---: |
| source package | `November 2025` |
| target canonical month | `December 2025` |
| candidate count | `142` |
| distinct machines | `44` |
| distinct orders | `85` |
| good quantity sum | `489580.0` |
| duplicate stable identity groups | `0` |
| workbook-level December overlaps | `7` |
| DB writes | `false` |

B10.2 blocked automatic reconciliation because the `7` overlap rows were workbook-level evidence only and source-row-hash availability was not yet proven.

## B10.3 summary

B10.3 copied the original runtime DB to a temp DB outside Git and opened it read-only to prove Bronze/hash overlap behavior.

Overlap proof evidence:

| Evidence point | Result |
| --- | ---: |
| candidates reproduced | `142` |
| workbook-level overlaps reproduced | `7` |
| workbook overlaps present in December target-package Bronze/Silver | `0` |
| workbook artifacts not present in Bronze | `7` |
| initial include candidates | `142` |
| skip true duplicate | `0` |
| unresolved/block | `0` |
| source-row-hash matched | `127/142` |
| source-row-hash unmatched | `15/142` |

B10.3 proved the workbook overlaps were not December target-package Bronze/Silver duplicates, but it still blocked execution until the `15` source-row-hash gaps were resolved.

## B10.4 summary

B10.4 resolved the `15` source-row-hash gaps through read-only analysis.

Gap decision evidence:

| Evidence point | Result |
| --- | ---: |
| source-hash gaps inspected | `15` |
| hash-resolved rows | `8` |
| target duplicates to skip | `7` |
| stable-identity fallback include | `0` |
| block unresolved | `0` |
| B10.5 approved include set | `135` |

The `8` resolved rows recovered existing November-source `source_row_hash` evidence after null-equivalent matching. The `7` skipped rows had target-package duplicate evidence and were excluded from the future insertion set.

## B10.5 summary

B10.5 executed the approved November-to-December plan against a copied temp DB only.

Temp-only reconciliation evidence:

| Evidence point | Result |
| --- | ---: |
| total candidates | `142` |
| include | `135` |
| skip existing duplicate | `7` |
| block unresolved | `0` |
| raw rows inserted | `135` |
| raw traceability | `135/135` |
| silver traceability | `135/135` |
| duplicate raw source-hash groups after run | `0` |
| duplicate silver source-hash groups after run | `0` |
| fact_machine_hour row count delta | `0` |
| fact_machine_hour good_qty delta | `+473257.0` |
| original runtime DB changed | `false` |

B10.5 rebuilt the December-only baseline in the temp DB, inserted only the `135` approved November-source carry-forward raw rows, refreshed December Silver and Gold in the temp DB, and kept the original runtime DB unchanged by size and mtime.

## What has been proven

Stage B10 proves that the controlled CSI carry-forward pattern is not limited to the July-to-August case.

The second proven case is:

```text
November 2025 source package -> December 2025 canonical month
```

The proven pattern requires:

- explicit source package and target canonical month selection;
- reproduction of the candidate set before mutation;
- source-row-hash proof or explicit reviewed skip decisions;
- duplicate checks before insertion;
- temp-only insertion into `raw_csi_event`;
- Silver and Gold refresh in the same temp DB;
- raw and silver traceability after reconciliation;
- duplicate source-hash and stable-identity checks after reconciliation;
- Gold row-count and quantity delta explanation;
- no live/shared DB promotion.

## What has not been proven

Stage B10 does not prove:

- production runtime adoption readiness;
- live/shared DB write safety;
- live rollback execution;
- long-term schema migration for permanent provenance fields;
- operator-facing workflow readiness;
- broad multi-month automatic carry-forward;
- March 2026 handling;
- behavior for every accepted forward-spill boundary;
- behavior for any future backward-spill case.

## Boundary cases proven

Two temp-only boundary cases are now proven:

| Case | Source package | Target canonical month | Include | Skip | Block | Raw traceability | Silver traceability |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| B9.2 | July 2025 | August 2025 | `235` | `0` | `0` | `235/235` | `235/235` |
| B10.5 | November 2025 | December 2025 | `135` | `7` | `0` | `135/135` | `135/135` |

The November-to-December case is stronger evidence for generalization because it included workbook-level overlaps, source-row-hash gaps, and explicit duplicate skips before the temp-only reconciliation run.

## Gold / aggregate impact

Gold impact must be reported separately from raw and silver row counts.

| Case | fact_machine_hour row count delta | fact_machine_hour good_qty delta | Interpretation |
| --- | ---: | ---: | --- |
| B9.2 July-to-August | `0` | `+687151.0` | The hour backbone already existed; CSI quantity overlay changed. |
| B10.5 November-to-December | `0` | `+473257.0` | The December hour backbone already existed; CSI quantity overlay changed. |

This proves that carry-forward can change aggregate quantities without changing Gold row counts.

## Duplicate-prevention evidence

B10 adds a duplicate-prevention case with real skip decisions.

Required evidence stayed clean:

| Surface | B10.5 result |
| --- | ---: |
| baseline raw duplicate `source_row_hash` groups | `0` |
| baseline silver duplicate `source_row_hash` groups | `0` |
| after raw duplicate `source_row_hash` groups | `0` |
| after silver duplicate `source_row_hash` groups | `0` |
| after raw duplicate stable-identity groups | `0` |
| after silver duplicate stable-identity groups | `0` |

The `7` target duplicates were skipped before insertion. No stable-identity-only fallback rows were inserted.

## Runtime behavior impact

No runtime behavior changed in Stage B10.

The active runtime still uses the existing timestamp-based canonical predicates. Source-discovery defaults remain unchanged from the already approved Stage B5 policy. Carry-forward is not wired into ETL, historical backfill, canonical materialization, Streamlit, DQ runtime behavior, or ML behavior.

## Live/shared DB boundary

The original runtime DB remains outside the GitHub-safe tree and remains local-only runtime state.

Stage B10 did not write the original runtime DB, did not write any DB inside the GitHub-safe tree, did not promote any temp DB, and did not approve live/shared DB replacement.

## Remaining risks

- Future boundary months may have different overlap or source-hash behavior.
- Permanent provenance fields still need a schema or audit-table decision.
- A disabled-by-default runtime hook can still add maintenance risk if it is wired before the helper boundary is reviewed.
- Live DB rollback is unproven because all successful execution has been temp-only.
- Gold quantity deltas require stakeholder review before any promoted run.
- March 2026 remains outside accepted canonical scope.

## Recommended Stage B11

Recommended Stage B11 should design a disabled-by-default runtime hook without enabling it.

The next stage should define explicit configuration modes, call-site boundaries, helper refusal rules, provenance and duplicate contracts, rollback behavior, temp-only rehearsal requirements, tests, and abort criteria.

No live/shared DB mode, Streamlit write control, runtime predicate change, source-discovery default change, DQ runtime wiring, or active carry-forward execution should be approved by this closeout.
