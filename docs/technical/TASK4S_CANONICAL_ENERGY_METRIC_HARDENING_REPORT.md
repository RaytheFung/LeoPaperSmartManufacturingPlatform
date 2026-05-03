# TASK4S Canonical Energy Metric Hardening Report

## Outcome

This separate canonical energy metric hardening task passed.

Scope stayed narrow:

- no live DB write was performed
- no live `good_qty` / `scrap_qty` semantics changed
- no anomaly policy changed
- no model retraining ran
- no `unified_view` regeneration ran
- no dormant helper cleanup was folded into this task

## Live Path Confirmation

Direct-source-verified live repo paths edited in this task:

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)

The live repo tree matched the task prompt for those paths, so only the real repo files above were edited.

## Metric Audit And Chosen Policy

### Month summary `Avg kWh / Good Unit`

Previous direct-source-verified behavior:

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) computed row-level `kwh_per_good_unit`
- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) then summarized the month KPI as the simple mean of those row ratios
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) labeled that output as `Avg kWh / Good Unit`

Chosen policy now:

- weighted ratio on positive-good-qty canonical rows in the selected month
- exact formula: `sum(energy_total_kwh) / sum(good_qty)`

Reason:

- this is a month KPI and should not let tiny-volume rows distort the displayed efficiency
- positive-good-qty row scope is kept explicit because per-unit efficiency is undefined on zero-good rows

### Machine efficiency ranking

Previous direct-source-verified behavior:

- per-machine ranking used the mean of row-level `kwh_per_good_unit`

Chosen policy now:

- weighted ratio per machine on positive-good-qty canonical rows
- exact formula per machine: `sum(energy_total_kwh) / sum(good_qty)`

Reason:

- ranking machines by the mean of hourly ratios can invert the ordering when machines have very different row volumes
- the weighted ratio is the honest aggregate machine KPI for the routed ranking

### Maintenance efficiency curve

Previous direct-source-verified behavior:

- bucket curve used the mean of row-level `kwh_per_good_unit`

Chosen policy now:

- weighted ratio per maintenance-age bucket on positive-good-qty canonical rows with maintenance recency
- exact formula per bucket: `sum(energy_total_kwh) / sum(good_qty)`
- existing row-level curve eligibility guard stayed unchanged: `0 < kwh_per_good_unit < 20`

Reason:

- this curve is user-facing and can be read as a KPI trend
- keeping it as a row-mean would stay numerically misleading even with a better label
- the existing anomaly guard remained untouched to keep task scope narrow

## Exact File List Touched

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)
- [`docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)

## Exact Reason For Each Change

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
  - replaced the routed month summary KPI, machine ranking metric, and maintenance bucket metric with weighted ratios
  - added narrow aggregate numerator/denominator fields for the month KPI
  - added row counts and aggregate totals to machine-ranking and maintenance-bucket outputs so the routed UI can label and hover them honestly
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - relabeled the routed Energy Analysis summary KPI to `Weighted kWh / Good Unit`
  - relabeled the machine ranking to the same weighted definition and exposed aggregate hover context
  - added explicit formula copy so the routed page no longer implies a row-mean
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - relabeled the maintenance efficiency curve to the weighted bucket definition
  - exposed aggregate hover context and updated the explanatory copy
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)
  - added deterministic weighted-vs-unweighted regression fixtures for month summary, machine ranking, and maintenance buckets
- [`docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_ENERGY_METRIC_HARDENING_REPORT.md)
  - recorded the new metric contract, scope boundary, validation, and live smoke evidence
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this report in the Task 4S chain
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - updated the live execution ledger to reflect the new routed weighted metric contract

## Direct-Source-Verified Read-Only Smoke

Smoke source:

- active DB opened read-only via SQLite URI `file:.../manufacturing_data.db?mode=ro`
- canonical source table: `fact_machine_hour`
- covered month: `June 2025`

### Month summary smoke

Direct-source-verified outputs:

- rows loaded: `62,639`
- distinct machines: `87`
- total energy kWh across the month slice: `1,243,942.5813`
- total good qty across the month slice: `119,306,012.80570014`
- displayed summary efficiency numerator: `986,582.8915 kWh`
- displayed summary efficiency denominator: `118,344,231.80570012 good_qty`
- displayed summary efficiency: `0.008336552415328456`

Exact displayed-summary formula:

- `986,582.8915 / 118,344,231.80570012`
- equivalently: `sum(energy_total_kwh) / sum(good_qty)` on positive-good-qty canonical rows in the selected month

### Machine ranking smoke

Direct-source-verified top routed machine ranking rows for `June 2025`:

- `024-088`: weighted `0.000855190111850831`, `347` rows, `694,407.0` good_qty, `593.85 kWh`
- `024-089`: weighted `0.0015036461476448386`, `403` rows, `1,387,910.6485716428` good_qty, `2,086.9265 kWh`
- `024-114`: weighted `0.0015167790874185347`, `515` rows, `1,740,002.892901007` good_qty, `2,639.2 kWh`

Exact ranking metric definition:

- per machine: `sum(energy_total_kwh) / sum(good_qty)` on positive-good-qty canonical rows for that machine in the selected month

### Maintenance curve smoke

Direct-source-verified bucket outputs on live Jan-Jun canonical data:

- `0-200h`: weighted `0.009412817704974796`, `39,450` rows, `140,889,130.90275884` good_qty, `1,326,163.7058 kWh`
- `200-500h`: weighted `0.009051579693111288`, `34,616` rows, `117,294,712.99998711` good_qty, `1,061,702.4423 kWh`
- `500-800h`: weighted `0.008704907979995957`, `21,101` rows, `65,348,677.562960766` good_qty, `568,854.2248 kWh`
- `800-1200h`: weighted `0.008066021663672688`, `18,416` rows, `58,376,873.83368619` good_qty, `470,869.129 kWh`
- `1200-2000h`: weighted `0.0069827284162588465`, `14,403` rows, `42,800,221.501400195` good_qty, `298,862.3229 kWh`
- `2000-4000h`: weighted `0.006033265238722221`, `5,268` rows, `15,743,128.99263753` good_qty, `94,982.4729 kWh`

Exact curve metric definition:

- per maintenance-age bucket: `sum(energy_total_kwh) / sum(good_qty)`
- scope retained from the existing route: rows with maintenance recency, `good_qty > 0`, and `0 < kwh_per_good_unit < 20`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/canonical_energy_reader.py tests/test_canonical_energy_reader.py app.py modules/maintenance_module.py
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_canonical_energy_reader
./.conda311/bin/python -c "from pathlib import Path; import sqlite3; month='June 2025'; db_uri=f\"file:{Path('manufacturing_data.db').resolve()}?mode=ro\"; conn=sqlite3.connect(db_uri, uri=True); start_ts='2025-06-01T00:00:00'; end_ts='2025-07-01T00:00:00'; summary = conn.execute(\"SELECT COUNT(*) AS rows_loaded, COUNT(DISTINCT canonical_machine_id) AS distinct_machines, SUM(energy_total_kwh) AS total_energy_kwh, SUM(good_qty) AS total_good_qty, SUM(CASE WHEN good_qty > 0 AND energy_total_kwh IS NOT NULL THEN energy_total_kwh END) AS efficiency_energy_kwh, SUM(CASE WHEN good_qty > 0 AND energy_total_kwh IS NOT NULL THEN good_qty END) AS efficiency_good_qty FROM fact_machine_hour WHERE hour_ts IS NOT NULL AND hour_ts >= ? AND hour_ts < ?\", (start_ts, end_ts)).fetchone(); ranking = conn.execute(\"SELECT canonical_machine_id AS machine_id, COUNT(*) AS row_count, SUM(good_qty) AS total_good_qty, SUM(energy_total_kwh) AS total_energy_kwh, SUM(energy_total_kwh) / SUM(good_qty) AS weighted_kwh_per_good_unit FROM fact_machine_hour WHERE hour_ts IS NOT NULL AND hour_ts >= ? AND hour_ts < ? AND good_qty > 0 AND energy_total_kwh IS NOT NULL GROUP BY canonical_machine_id HAVING COUNT(*) >= 1 AND SUM(good_qty) > 0 ORDER BY weighted_kwh_per_good_unit ASC, total_good_qty DESC, machine_id ASC LIMIT 3\", (start_ts, end_ts)).fetchall(); conn.close(); print('MONTH', month); print('SUMMARY', summary); print('RANKING_TOP3', ranking)"
./.conda311/bin/python -c "from pathlib import Path; import sqlite3; db_uri=f\"file:{Path('manufacturing_data.db').resolve()}?mode=ro\"; conn=sqlite3.connect(db_uri, uri=True); curve = conn.execute(\"WITH eligible AS ( SELECT CASE WHEN hours_since_last_maintenance > 0 AND hours_since_last_maintenance <= 200 THEN '0-200h' WHEN hours_since_last_maintenance > 200 AND hours_since_last_maintenance <= 500 THEN '200-500h' WHEN hours_since_last_maintenance > 500 AND hours_since_last_maintenance <= 800 THEN '500-800h' WHEN hours_since_last_maintenance > 800 AND hours_since_last_maintenance <= 1200 THEN '800-1200h' WHEN hours_since_last_maintenance > 1200 AND hours_since_last_maintenance <= 2000 THEN '1200-2000h' WHEN hours_since_last_maintenance > 2000 AND hours_since_last_maintenance <= 4000 THEN '2000-4000h' ELSE NULL END AS bucket, energy_total_kwh, good_qty FROM fact_machine_hour WHERE hours_since_last_maintenance IS NOT NULL AND good_qty > 0 AND energy_total_kwh IS NOT NULL AND (energy_total_kwh / good_qty) > 0 AND (energy_total_kwh / good_qty) < 20 ) SELECT bucket, COUNT(*) AS row_count, SUM(good_qty) AS total_good_qty, SUM(energy_total_kwh) AS total_energy_kwh, SUM(energy_total_kwh) / SUM(good_qty) AS weighted_kwh_per_good_unit FROM eligible WHERE bucket IS NOT NULL GROUP BY bucket HAVING COUNT(*) >= 20 AND SUM(good_qty) > 0 ORDER BY CASE bucket WHEN '0-200h' THEN 1 WHEN '200-500h' THEN 2 WHEN '500-800h' THEN 3 WHEN '800-1200h' THEN 4 WHEN '1200-2000h' THEN 5 WHEN '2000-4000h' THEN 6 ELSE 7 END\" ).fetchall(); conn.close(); print('CURVE', curve)"
```

Results:

- `py_compile`: passed
- focused tests: `Ran 6 tests`, `OK`
- read-only June 2025 month-summary smoke: passed
- read-only June 2025 machine-ranking smoke: passed
- read-only Jan-Jun maintenance-curve smoke: passed

## Coherence Result

Direct-source-verified conclusion:

- the routed canonical Energy Analysis month KPI is now numerically coherent and honestly labeled
- the routed canonical machine efficiency ranking is now numerically coherent and honestly labeled
- the routed maintenance efficiency curve is now numerically coherent and honestly labeled

In plain terms:

- these touched routed surfaces no longer present a simple mean of row-level ratios under aggregate-style wording

## Remaining Limitations

- this task did not change dormant legacy helpers
- this task did not rewrite adjacent user-facing canonical summary helpers outside the touched routed surfaces
- the maintenance curve still intentionally keeps the pre-existing row-level eligibility guard `0 < kwh_per_good_unit < 20`
- total month energy and total month good quantity are still shown separately from the weighted KPI scope, so the routed page now states the KPI formula explicitly to avoid implying that it is a raw `total_energy_kwh / total_good_qty` display

## Recommended Next Clean Boundary

- separate metric-contract audit for other user-facing canonical summary helpers that still present row-mean efficiency under aggregate-style wording

Out of scope for that next task unless separately approved:

- anomaly-policy changes
- quantity semantics changes
- ML retraining
- `unified_view` regeneration
- dormant helper cleanup folded into the same pass
