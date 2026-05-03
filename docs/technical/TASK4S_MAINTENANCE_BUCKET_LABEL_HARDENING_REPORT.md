# TASK4S Maintenance Bucket Label Hardening Report

## Outcome

This very narrow maintenance bucket label hardening micro-task passed.

Scope stayed extremely narrow:

- no live DB write was performed
- no live `good_qty` / `scrap_qty` semantics changed
- no anomaly policy changed
- no model retraining ran
- no `unified_view` regeneration ran
- no bucket-scope widening was folded into this task
- no dormant helper cleanup or causal maintenance-policy study was folded into this task

## Live Path Confirmation

Direct-source-verified live repo paths audited from the real repo tree:

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)

Result:

- the live repo tree matched the task prompt for those paths
- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) required the live contract label fix plus one minimal out-of-bin guard so capped-scope rows do not leak back as an unlabeled bucket
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py) required one focused deterministic regression test
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py) did not require a direct code edit because the routed chart x-axis labels are sourced from the bucket values returned by [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)

## Final Bucket Scope Audit

Direct-source-verified code audit:

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) uses `bins=[0, 200, 500, 800, 1200, 2000, 4000]`
- the final bucket condition implied by `pd.cut(..., right=True, include_lowest=False)` is `hours_since_last_maintenance > 2000 and <= 4000`
- the prior label `2000h+` was therefore broader than the implemented scope
- before this micro-task closed, out-of-bin rows above `4000h` could still group back into an unlabeled `NaN` bucket if they existed in sufficient count; this task now excludes those unlabeled rows from the returned curve so the capped scope is enforced explicitly

Direct-source-verified validation SQL audit from the latest narrative hardening report:

- the read-only SQL in [`TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md) used the same capped final condition `> 2000 AND <= 4000`
- the same capped label mismatch also appeared in the prior Task 4S energy-metric and summary-contract reports

Conclusion:

- the final bucket was not truly open-ended
- the honest final bucket contract after this task is `2000-4000h`

## Read-Only >4000h Eligible Row Check

Smoke source:

- active DB opened read-only via SQLite URI `file:.../manufacturing_data.db?mode=ro`
- canonical source table: `fact_machine_hour`
- eligible row scope: `hours_since_last_maintenance > 4000`, `good_qty > 0`, `energy_total_kwh IS NOT NULL`, and `0 < energy_total_kwh / good_qty < 20`

Direct-source-verified outputs:

- eligible row count beyond `4000h`: `0`
- total good qty beyond `4000h`: `none`
- total energy kWh beyond `4000h`: `none`

Grounded interpretation:

- there is no live read-only evidence in the current eligible slice that requires widening the capped final bucket in this task
- label hardening is the safe resolution

## Exact Final Bucket Contract After Hardening

- bucket edges remain unchanged: `[0, 200, 500, 800, 1200, 2000, 4000]`
- bucket inclusion remains unchanged: right-closed, left-open
- final bucket condition remains unchanged: `hours_since_last_maintenance > 2000 and <= 4000`
- final bucket label now matches that scope exactly: `2000-4000h`

## Exact File List Touched

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)
- [`docs/technical/TASK4S_DOWNSTREAM_ALIGNMENT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_DOWNSTREAM_ALIGNMENT_REPORT.md)
- [`docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md)
- [`docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md)
- [`docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md)
- [`docs/technical/TASK4S_MAINTENANCE_BUCKET_LABEL_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_MAINTENANCE_BUCKET_LABEL_HARDENING_REPORT.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)

## Exact Reason For Each Change

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
  - relabeled the final maintenance-age bucket from `2000h+` to `2000-4000h` so the returned routed bucket values match the actual capped bin edges already implemented
  - added a minimal guard that drops unlabeled out-of-bin rows from the returned grouped curve so `>4000h` rows do not surface as a `NaN` bucket
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)
  - added one focused deterministic test proving that a `2500h` row lands in `2000-4000h` and a `4500h` row is excluded rather than silently treated as part of an open-ended bucket
- [`docs/technical/TASK4S_DOWNSTREAM_ALIGNMENT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_DOWNSTREAM_ALIGNMENT_REPORT.md)
  - corrected the historical bucket label in the live smoke summary to match the capped implementation
- [`docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md)
  - corrected the historical bucket label and validation SQL snippet to match the capped implementation
- [`docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md)
  - corrected the historical returned-bucket wording, bucket output line, and validation SQL snippet to match the capped implementation
- [`docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md)
  - corrected the prior read-only bucket label and SQL snippet to match the capped implementation
- [`docs/technical/TASK4S_MAINTENANCE_BUCKET_LABEL_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_MAINTENANCE_BUCKET_LABEL_HARDENING_REPORT.md)
  - recorded the scope audit, `>4000h` read-only smoke, exact final contract, validation, and closure of this micro-task
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this micro-task report in the Task 4S chain
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - updated the live ledger to reflect closure of the maintenance bucket label hardening micro-task

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/canonical_energy_reader.py tests/test_canonical_energy_reader.py
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_canonical_energy_reader
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python - <<'PY'
from pathlib import Path
import sqlite3

db_uri = f"file:{Path('manufacturing_data.db').resolve()}?mode=ro"
conn = sqlite3.connect(db_uri, uri=True)
curve = conn.execute(
    """
    WITH eligible AS (
        SELECT
            CASE
                WHEN hours_since_last_maintenance > 0 AND hours_since_last_maintenance <= 200 THEN '0-200h'
                WHEN hours_since_last_maintenance > 200 AND hours_since_last_maintenance <= 500 THEN '200-500h'
                WHEN hours_since_last_maintenance > 500 AND hours_since_last_maintenance <= 800 THEN '500-800h'
                WHEN hours_since_last_maintenance > 800 AND hours_since_last_maintenance <= 1200 THEN '800-1200h'
                WHEN hours_since_last_maintenance > 1200 AND hours_since_last_maintenance <= 2000 THEN '1200-2000h'
                WHEN hours_since_last_maintenance > 2000 AND hours_since_last_maintenance <= 4000 THEN '2000-4000h'
                ELSE NULL
            END AS bucket,
            energy_total_kwh,
            good_qty
        FROM fact_machine_hour
        WHERE hours_since_last_maintenance IS NOT NULL
          AND good_qty > 0
          AND energy_total_kwh IS NOT NULL
          AND (energy_total_kwh / good_qty) > 0
          AND (energy_total_kwh / good_qty) < 20
    )
    SELECT
        bucket,
        COUNT(*) AS row_count,
        SUM(good_qty) AS total_good_qty,
        SUM(energy_total_kwh) AS total_energy_kwh,
        SUM(energy_total_kwh) / SUM(good_qty) AS weighted_kwh_per_good_unit
    FROM eligible
    WHERE bucket IS NOT NULL
    GROUP BY bucket
    HAVING COUNT(*) >= 20 AND SUM(good_qty) > 0
    ORDER BY CASE bucket
        WHEN '0-200h' THEN 1
        WHEN '200-500h' THEN 2
        WHEN '500-800h' THEN 3
        WHEN '800-1200h' THEN 4
        WHEN '1200-2000h' THEN 5
        WHEN '2000-4000h' THEN 6
        ELSE 7
    END
    """
).fetchall()
beyond = conn.execute(
    """
    SELECT
        COUNT(*) AS row_count,
        SUM(good_qty) AS total_good_qty,
        SUM(energy_total_kwh) AS total_energy_kwh
    FROM fact_machine_hour
    WHERE hours_since_last_maintenance > 4000
      AND good_qty > 0
      AND energy_total_kwh IS NOT NULL
      AND (energy_total_kwh / good_qty) > 0
      AND (energy_total_kwh / good_qty) < 20
    """
).fetchone()
conn.close()
print("CURVE", curve)
print(">4000H", beyond)
PY
```

Results:

- `py_compile`: passed
- focused tests: passed
- read-only maintenance-curve smoke with the corrected final label: passed
- read-only `>4000h` eligible-row smoke: passed

## Whether The Routed Maintenance-Curve Contract Is Now Fully Honest

Direct-source-verified judgment:

- yes on the capped-final-bucket label issue
- the routed maintenance curve no longer uses an open-ended label for a capped `<= 4000h` final bin

Residual scope note:

- this micro-task did not revisit formula/filter/floor semantics because they were already hardened separately

## Recommended Next Clean Boundary

- no further maintenance bucket-label hardening is needed on the current routed maintenance curve
- if any future follow-up is desired, keep it separate and explicit:
  - either a real decision to widen the capped final bin to a true open-ended bucket
  - or dormant legacy cleanup outside the routed canonical maintenance curve
- do not widen the next step into quantity semantics, anomaly policy, model retraining, or `unified_view` regeneration
