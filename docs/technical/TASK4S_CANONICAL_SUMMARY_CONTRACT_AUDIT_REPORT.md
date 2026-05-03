# TASK4S Canonical Summary Contract Audit Report

## Outcome

This separate canonical summary contract audit passed.

Scope stayed narrow:

- no live DB write was performed
- no live `good_qty` / `scrap_qty` semantics changed
- no anomaly policy changed
- no model retraining ran
- no `unified_view` regeneration ran
- no dormant helper cleanup was folded into this task

## Direct-Source-Verified Scope Classification

### Currently routed user-facing canonical surfaces

- Canonical Unified Analytics page in [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) via [`core/canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py)
- Energy Analysis route in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) via [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- maintenance efficiency curve in [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py) via [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- Machine Learning route in [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) via [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) and row-level predictor calls through [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
- Optimization route in [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py) via [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py)

### Helper-only / latent canonical surfaces in the audit list

- no separate currently routed summary helper was found inside [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py); the current routed ML page uses it for row-level prediction calls, not a routed summary KPI

### Dormant legacy surfaces intentionally left out of scope

- dormant Overview helper in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- dormant Team Performance helper in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- shared ML helper tabs in [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py)
- legacy dropdown / baseline / recommendation helpers in [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)

## Audit Findings And Chosen Policy

### Energy Analysis month KPI

Direct-source-verified current contract:

- numerator: `sum(energy_total_kwh)`
- denominator: `sum(good_qty)`
- row eligibility: positive-good-qty canonical rows in the selected month
- group eligibility: none beyond the selected month slice
- support threshold: none beyond positive-good-qty row scope
- user-facing label/copy: already explicit from the prior hardening task

Result:

- no formula change in this audit
- no remaining hidden eligibility ambiguity on this touched surface

### Energy Analysis machine efficiency ranking

Direct-source-verified current contract:

- numerator per machine: `sum(energy_total_kwh)`
- denominator per machine: `sum(good_qty)`
- row eligibility: positive-good-qty canonical rows in the selected month
- group eligibility: per-machine aggregation in the selected month
- support threshold: current live policy remains `min_row_count = 1` plus positive total good qty

Audit decision:

- threshold policy kept unchanged in this audit

Reason:

- the current live June top-20 surfaced ranking already has nontrivial support without one-row outliers
- direct-source-verified live support range on the top 20 is `12` to `625` rows and `11,301.0` to `3,065,285.722651338` good qty
- changing the threshold now would alter ranking behavior without evidence of a current routed problem

Hardening applied:

- the routed page now states the formula and the current support rule explicitly

### Maintenance efficiency curve

Direct-source-verified current contract:

- numerator per bucket: `sum(energy_total_kwh)`
- denominator per bucket: `sum(good_qty)`
- row eligibility: maintenance recency present, `good_qty > 0`, `energy_total_kwh IS NOT NULL`, and retained guard `0 < kwh_per_good_unit < 20`
- group eligibility: maintenance-age buckets
- support threshold: `min_bucket_count = 20`

Audit finding:

- the page disclosed the weighted formula but still hid the retained row-level guard and bucket floor

Hardening applied:

- the routed maintenance copy now explicitly states the `0 < kwh_per_good_unit < 20` row guard and the `20`-row bucket floor

### Canonical Unified Analytics month KPI

Previous direct-source-verified behavior:

- [`core/canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py) still computed `average_kwh_per_good_unit` as a mean of row-level ratios
- [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) surfaced that as `Avg kWh/Good Unit`

Chosen contract now:

- numerator: `sum(energy_total_kwh)`
- denominator: `sum(good_qty)`
- row eligibility: positive-good-qty canonical rows in the selected month
- group eligibility: none beyond the selected month slice
- support threshold: none beyond positive-good-qty row scope
- user-facing label: `Weighted kWh/Good Unit`

Reason:

- this is a routed month KPI and should match the same aggregate contract already adopted on the routed Energy Analysis page

### Optimization page summary helpers

Direct-source-verified audit result:

- machine summary in [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py) already used a weighted ratio on safe rows
- schedule summary in [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py) already used a weighted ratio on eligible rows
- team insights in [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py) already used a weighted ratio on named-team rows with positive good qty

Ambiguity found:

- the routed UI still labeled those weighted outputs as `Avg kWh/Good Unit`

Hardening applied:

- the routed Optimization copy now labels them as `Weighted kWh/Good Unit`
- the routed captions/notes now state the relevant safe-row eligibility more explicitly

### ML page summary helpers

Direct-source-verified audit result:

- the routed ML page readiness tiles are count metrics, not energy-intensity summary KPIs
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) already discloses hard block rules and adapter rules in the contract tab
- no currently routed row-mean efficiency summary helper was found on the routed ML page

Result:

- no code change was needed on the routed ML page in this audit

## Exact File List Touched

- [`core/canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py)
- [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py)
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
- [`tests/test_canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_gold_reader.py)
- [`docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)

## Exact Reason For Each Change

- [`core/canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py)
  - replaced the routed Unified View month KPI row mean with a weighted ratio and exposed numerator/denominator fields
- [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py)
  - relabeled the routed Unified View month KPI to `Weighted kWh/Good Unit`
  - added explicit formula copy for the KPI scope
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - disclosed the current Energy Analysis machine-ranking formula and support rule directly in the routed page copy
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - disclosed the retained maintenance-curve row guard `0 < kwh_per_good_unit < 20` and the `20`-row bucket floor directly in the routed page copy
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - relabeled existing weighted optimization energy-intensity outputs to `Weighted kWh/Good Unit`
  - made the safe-row eligibility/disclosure copy more explicit in the routed page
- [`tests/test_canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_gold_reader.py)
  - added deterministic regression coverage that exposes the routed Unified View month KPI weighting difference
- [`docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_SUMMARY_CONTRACT_AUDIT_REPORT.md)
  - recorded the routed-surface audit findings, decisions, validation, and live smoke evidence
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this summary-contract audit report
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - updated the live ledger to reflect closure of the routed canonical summary-contract audit

## Direct-Source-Verified Read-Only Smoke

Smoke source:

- active DB opened read-only via SQLite URI `file:.../manufacturing_data.db?mode=ro`
- covered month: `June 2025`
- canonical source table: `fact_machine_hour`

### Unified View month KPI smoke

Direct-source-verified outputs:

- rows loaded: `62,639`
- distinct machines: `87`
- total energy kWh: `1,243,942.5813`
- total good qty: `119,306,012.80570014`
- total scrap qty: `1.0`
- weighted KPI numerator: `986,582.8915`
- weighted KPI denominator: `118,344,231.80570014`
- displayed weighted KPI: `0.008336552415328454`

Exact displayed formula:

- `986,582.8915 / 118,344,231.80570014`
- equivalently: `sum(energy_total_kwh) / sum(good_qty)` on positive-good-qty canonical rows in the selected month

### Energy ranking smoke

Direct-source-verified outputs:

- current formula: `sum(energy_total_kwh) / sum(good_qty)` per machine on positive-good-qty rows in the selected month
- current support rule from code: at least `1` positive-good row and positive total good qty
- live top-20 surfaced support range on `June 2025`: row count `12` to `625`, total good qty `11,301.0` to `3,065,285.722651338`
- live top 3 rows:
  - `024-088`: `347` rows, `694,407.0` good qty, `593.85 kWh`, weighted `0.000855190111850831`
  - `024-089`: `403` rows, `1,387,910.6485716428` good qty, `2,086.9265 kWh`, weighted `0.0015036461476448386`
  - `024-114`: `515` rows, `1,740,002.892901007` good qty, `2,639.2 kWh`, weighted `0.0015167790874185347`

### Maintenance curve smoke

Direct-source-verified outputs:

- retained row eligibility: maintenance recency present, `good_qty > 0`, `energy_total_kwh IS NOT NULL`, and `0 < kwh_per_good_unit < 20`
- retained bucket threshold: at least `20` rows
- returned buckets: `0-200h`, `200-500h`, `500-800h`, `800-1200h`, `1200-2000h`, `2000-4000h`
- `0-200h`: `39,450` rows, `140,889,130.90275884` good qty, `1,326,163.7058 kWh`, weighted `0.009412817704974796`
- `200-500h`: `34,616` rows, `117,294,712.99998711` good qty, `1,061,702.4423 kWh`, weighted `0.009051579693111288`
- `500-800h`: `21,101` rows, `65,348,677.562960766` good qty, `568,854.2248 kWh`, weighted `0.008704907979995957`
- `800-1200h`: `18,416` rows, `58,376,873.83368619` good qty, `470,869.129 kWh`, weighted `0.008066021663672688`
- `1200-2000h`: `14,403` rows, `42,800,221.501400195` good qty, `298,862.3229 kWh`, weighted `0.0069827284162588465`
- `2000-4000h`: `5,268` rows, `15,743,128.99263753` good qty, `94,982.4729 kWh`, weighted `0.006033265238722221`

### Additional routed helper formulas touched

Direct-source-verified from code:

- Canonical Unified Analytics month KPI now uses the same weighted month contract as the routed Energy Analysis KPI
- Optimization machine, schedule, and team energy-intensity values were already weighted before this audit; this task hardened only their user-facing labels/captions

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/canonical_gold_reader.py modules/unified_view_module.py app.py modules/maintenance_module.py modules/optimization_module.py tests/test_canonical_gold_reader.py
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_canonical_gold_reader tests.test_canonical_energy_reader
./.conda311/bin/python -c "from pathlib import Path; import sqlite3; db_uri=f\"file:{Path('manufacturing_data.db').resolve()}?mode=ro\"; conn=sqlite3.connect(db_uri, uri=True); summary = conn.execute(\"SELECT COUNT(*) AS rows_loaded, COUNT(DISTINCT canonical_machine_id) AS distinct_machines, SUM(energy_total_kwh) AS total_energy_kwh, SUM(good_qty) AS total_good_qty, SUM(scrap_qty) AS total_scrap_qty, SUM(CASE WHEN good_qty > 0 AND energy_total_kwh IS NOT NULL THEN energy_total_kwh END) AS efficiency_energy_kwh, SUM(CASE WHEN good_qty > 0 AND energy_total_kwh IS NOT NULL THEN good_qty END) AS efficiency_good_qty FROM fact_machine_hour WHERE hour_ts >= '2025-06-01T00:00:00' AND hour_ts < '2025-07-01T00:00:00'\").fetchone(); top20 = conn.execute(\"WITH ranked AS ( SELECT canonical_machine_id AS machine_id, COUNT(*) AS row_count, SUM(good_qty) AS total_good_qty, SUM(energy_total_kwh) / SUM(good_qty) AS weighted_kwh_per_good_unit FROM fact_machine_hour WHERE hour_ts >= '2025-06-01T00:00:00' AND hour_ts < '2025-07-01T00:00:00' AND good_qty > 0 AND energy_total_kwh IS NOT NULL GROUP BY canonical_machine_id HAVING SUM(good_qty) > 0 ORDER BY weighted_kwh_per_good_unit ASC, total_good_qty DESC, machine_id ASC LIMIT 20 ) SELECT MIN(row_count), MAX(row_count), MIN(total_good_qty), MAX(total_good_qty) FROM ranked\").fetchone(); top3 = conn.execute(\"SELECT canonical_machine_id AS machine_id, COUNT(*) AS row_count, SUM(good_qty) AS total_good_qty, SUM(energy_total_kwh) AS total_energy_kwh, SUM(energy_total_kwh) / SUM(good_qty) AS weighted_kwh_per_good_unit FROM fact_machine_hour WHERE hour_ts >= '2025-06-01T00:00:00' AND hour_ts < '2025-07-01T00:00:00' AND good_qty > 0 AND energy_total_kwh IS NOT NULL GROUP BY canonical_machine_id HAVING SUM(good_qty) > 0 ORDER BY weighted_kwh_per_good_unit ASC, total_good_qty DESC, machine_id ASC LIMIT 3\").fetchall(); conn.close(); print('UNIFIED_SUMMARY', summary); print('RANKING_TOP20_SUPPORT_RANGE', top20); print('RANKING_TOP3', top3)"
./.conda311/bin/python -c "from pathlib import Path; import sqlite3; db_uri=f\"file:{Path('manufacturing_data.db').resolve()}?mode=ro\"; conn=sqlite3.connect(db_uri, uri=True); curve = conn.execute(\"WITH eligible AS ( SELECT CASE WHEN hours_since_last_maintenance > 0 AND hours_since_last_maintenance <= 200 THEN '0-200h' WHEN hours_since_last_maintenance > 200 AND hours_since_last_maintenance <= 500 THEN '200-500h' WHEN hours_since_last_maintenance > 500 AND hours_since_last_maintenance <= 800 THEN '500-800h' WHEN hours_since_last_maintenance > 800 AND hours_since_last_maintenance <= 1200 THEN '800-1200h' WHEN hours_since_last_maintenance > 1200 AND hours_since_last_maintenance <= 2000 THEN '1200-2000h' WHEN hours_since_last_maintenance > 2000 AND hours_since_last_maintenance <= 4000 THEN '2000-4000h' ELSE NULL END AS bucket, energy_total_kwh, good_qty FROM fact_machine_hour WHERE hours_since_last_maintenance IS NOT NULL AND good_qty > 0 AND energy_total_kwh IS NOT NULL AND (energy_total_kwh / good_qty) > 0 AND (energy_total_kwh / good_qty) < 20 ) SELECT bucket, COUNT(*) AS row_count, SUM(good_qty) AS total_good_qty, SUM(energy_total_kwh) AS total_energy_kwh, SUM(energy_total_kwh) / SUM(good_qty) AS weighted_kwh_per_good_unit FROM eligible WHERE bucket IS NOT NULL GROUP BY bucket HAVING COUNT(*) >= 20 AND SUM(good_qty) > 0 ORDER BY CASE bucket WHEN '0-200h' THEN 1 WHEN '200-500h' THEN 2 WHEN '500-800h' THEN 3 WHEN '800-1200h' THEN 4 WHEN '1200-2000h' THEN 5 WHEN '2000-4000h' THEN 6 ELSE 7 END\").fetchall(); conn.close(); print('MAINTENANCE_CURVE', curve)"
```

Results:

- `py_compile`: passed
- focused tests: `Ran 12 tests`, `OK`
- read-only June summary/ranking smoke: passed
- read-only maintenance-curve smoke: passed

## Remaining Ambiguity After This Audit

Direct-source-verified on the touched routed canonical summary surfaces:

- no hidden formula ambiguity remains
- no hidden maintenance-curve eligibility/filter ambiguity remains
- no hidden routed machine-ranking support-policy ambiguity remains

Still out of scope:

- dormant legacy helpers
- non-summary predictive output wording beyond the audited summary/readiness surfaces

## Recommended Next Clean Boundary

- dormant legacy cleanup only

Not recommended as the next step from this audit:

- reopening Task 4S quantity work
- anomaly-policy changes
- ML retraining
- `unified_view` regeneration
- mixing dormant cleanup with a new contract audit on unrelated surfaces
