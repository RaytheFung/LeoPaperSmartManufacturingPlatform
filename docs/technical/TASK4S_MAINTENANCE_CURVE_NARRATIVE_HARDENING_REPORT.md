# TASK4S Maintenance Curve Narrative Hardening Report

## Outcome

This separate maintenance curve narrative hardening task passed.

Scope stayed narrow:

- no live DB write was performed
- no live `good_qty` / `scrap_qty` semantics changed
- no anomaly policy changed
- no model retraining ran
- no `unified_view` regeneration ran
- no dormant legacy cleanup was folded into this task

## Live Path Confirmation

Direct-source-verified live repo paths audited from the real repo tree:

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)

Result:

- the live repo tree matched the task prompt for those paths
- only [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py) required code edits
- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) and [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py) were audited but left unchanged

## Read-Only Maintenance Curve Audit On The Active DB

Smoke source:

- active DB opened read-only via SQLite URI `file:.../manufacturing_data.db?mode=ro`
- canonical source table: `fact_machine_hour`
- eligible row scope: maintenance recency present, `good_qty > 0`, `energy_total_kwh IS NOT NULL`, and `0 < energy_total_kwh / good_qty < 20`
- bucket floor: `20` rows

Direct-source-verified bucket outputs:

- `0-200h`: `39,450` rows, `140,889,130.90275884` total good qty, `1,326,163.7058` total kWh, weighted `0.009412817704974796`
- `200-500h`: `34,616` rows, `117,294,712.99998711` total good qty, `1,061,702.4423` total kWh, weighted `0.009051579693111288`
- `500-800h`: `21,101` rows, `65,348,677.562960766` total good qty, `568,854.2248` total kWh, weighted `0.008704907979995957`
- `800-1200h`: `18,416` rows, `58,376,873.83368619` total good qty, `470,869.129` total kWh, weighted `0.008066021663672688`
- `1200-2000h`: `14,403` rows, `42,800,221.501400195` total good qty, `298,862.3229` total kWh, weighted `0.0069827284162588465`
- `2000-4000h`: `5,268` rows, `15,743,128.99263753` total good qty, `94,982.4729` total kWh, weighted `0.006033265238722221`

Curve direction classification:

- `monotonically improving`

Grounded interpretation:

- the observed bucket profile does not show monotonically worsening energy intensity as maintenance age increases
- the live routed curve therefore does not support directional wording such as `degradation as maintenance is delayed`
- the live routed curve also does not support a prescriptive PM threshold recommendation derived from the highest bucket alone

## Narrative Claim Audit Before Hardening

### Chart title

Previous routed title:

- `Weighted canonical efficiency degradation as maintenance is delayed`

Classification:

- not supported / too strong

Reason:

- the active read-only curve is monotonically improving, not worsening
- the wording also overstates causality by implying that delay itself causes degradation

### Explanatory caption

Previous routed caption content:

- stated canonical source
- stated maintenance recency and `good_qty > 0`
- stated `0 < kwh_per_good_unit < 20`
- stated `20`-row bucket floor
- stated weighted formula

Classification:

- directly supported for the disclosed formula/filter/floor contract, but incomplete as narrative hardening

Reason:

- the disclosed formula and floor were consistent with the active read-only query
- the caption did not explicitly say `energy_total_kwh IS NOT NULL`
- the caption did not explicitly warn that the chart is descriptive rather than causal

### Best observed line annotation

Previous routed annotation:

- `Best observed`

Classification:

- not supported / too strong

Reason:

- the line implied a normative benchmark or target that the read-only smoke does not prove
- on this evidence, a lowest observed bucket is an observation in the current snapshot, not a policy threshold

### Info callout / recommendation text

Previous routed callout:

- recommended scheduling PM before the `worst bucket` to stay in `optimum efficiency bands`

Classification:

- not supported / too strong

Reason:

- the curve does not show worsening with age
- the recommendation overclaimed causality and prescriptive certainty from a descriptive bucket profile

## Exact User-Facing Narrative After Hardening

### Section heading

- `Observed Energy Intensity vs Maintenance Age`

### Caption

- `Canonical source: fact_machine_hour only. Eligible curve rows require maintenance recency, good_qty > 0, energy_total_kwh IS NOT NULL, and 0 < kwh_per_good_unit < 20. Buckets require at least 20 rows. Each bucket shows weighted energy intensity = sum(energy_total_kwh) / sum(good_qty). This is a descriptive bucketed profile from observed rows, not a causal maintenance-threshold rule; no unified_view fallback.`

### Chart title

- `Observed weighted energy intensity by maintenance-age bucket`

### Annotation

- the prior `Best observed` line annotation was removed

### Info callout

- `This chart summarizes observed weighted kWh per good unit by maintenance-age bucket in the current eligible slice. The lowest bucket in the profile is descriptive only, not a causal maintenance threshold, and this chart should not be used by itself to schedule PM before any specific bucket.`

## Exact File List Touched

- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)

## Exact Reason For Each Change

- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - removed unsupported directional and prescriptive maintenance-curve wording from the routed maintenance page
  - preserved and clarified the explicit curve eligibility/filter/floor disclosure
  - relabeled the chart as observational rather than causal
  - removed the `Best observed` benchmark annotation because it overstated what the curve proves
- [`docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_MAINTENANCE_CURVE_NARRATIVE_HARDENING_REPORT.md)
  - recorded the read-only bucket outputs, curve-direction classification, narrative-claim audit, and the exact routed copy after hardening
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this maintenance-curve narrative hardening report in the Task 4S chain
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - updated the live ledger to reflect closure of the routed maintenance-curve narrative hardening task

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile modules/maintenance_module.py
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python - <<'PY'
from pathlib import Path
import sqlite3

db_uri = f"file:{Path('manufacturing_data.db').resolve()}?mode=ro"
conn = sqlite3.connect(db_uri, uri=True)
rows = conn.execute(
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
conn.close()
print(rows)
PY
```

Results:

- `py_compile`: passed
- read-only maintenance-curve smoke: passed
- focused unit tests: none, because no helper logic or contract field changed in this task

## Whether Any Routed Maintenance Interpretation Overclaim Still Remains

Direct-source-verified judgment:

- no material overclaim remains in the touched routed maintenance-curve title/caption/callout path
- the chart is now framed as descriptive and non-causal

Residual caution:

- the chart is still an observed bucket profile and should not be reused as evidence for a causal PM rule unless a separate evidence task is approved

## Recommended Next Clean Boundary

- no further maintenance-curve narrative hardening is needed on the current routed page
- if future maintenance follow-up is desired, keep it separate and evidence-only as either a causal maintenance-policy study or broader dormant legacy cleanup
- do not widen the next step into quantity semantics, anomaly policy, model retraining, or `unified_view` regeneration
