# TASK4S Downstream Alignment Report

## Outcome

This separate downstream alignment task passed.

Scope stayed narrow:

- no live DB write was performed
- no live `good_qty` / `scrap_qty` semantics changed
- no anomaly policy changed
- no model retraining or artifact promotion ran
- no legacy `unified_view` rematerialization ran

## Direct-Source-Verified Scope Classification

### Currently user-routed and aligned now

- Energy Analysis route in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- maintenance efficiency curve inside [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)

### Currently latent or helper-only and intentionally left out of scope

- dormant Overview helper in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- dormant Team Performance helper in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- dormant legacy optimization demo helper in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- shared ML helper tabs in [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py)
- legacy dropdown / baseline / recommendation helpers in [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
- legacy month helper in [`core/data_utils.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/data_utils.py)

Reason they were left out:

- they are not the primary source for currently routed runtime analytics after this task
- rewriting them now would widen scope into dormant cleanup rather than routed-surface alignment

## Exact File List Touched

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)

## Exact Reason For Each Change

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
  - added one small canonical runtime helper backed by `fact_machine_hour` only
  - exposes month discovery, month-scoped energy rows, state-attributed energy breakdown, machine efficiency ranking, hourly energy profile, and the maintenance-age efficiency curve
  - keeps legacy-only gaps honest by leaving residual energy in explicit `unallocated_energy_kwh` instead of fabricating EUVG-style buckets
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - retargeted the routed Energy Analysis page from EUVG/in-memory `unified_view` data to `CanonicalEnergyReader`
  - removed EUVG / `unified_view` fallback behavior from that routed page
  - added explicit copy that the route now reads canonical `fact_machine_hour`
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - retargeted the maintenance efficiency curve from persisted `unified_view.kwh_per_unit` to canonical `fact_machine_hour`
  - made the curve wording explicit about the canonical formula: `energy_total_kwh / good_qty` on positive-good-qty rows with maintenance recency
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)
  - added focused regression coverage for the new canonical reader, including minute-share attribution, row-state fallback, and maintenance-curve aggregation

## Before / After Source Mapping

| Routed surface | Before | After | Result |
|---|---|---|---|
| Energy Analysis route | EUVG in-memory dataframe from `load_data()` in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) | `fact_machine_hour` through [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) | legacy dependence removed |
| Maintenance efficiency curve | persisted `unified_view.kwh_per_unit` in [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py) | `fact_machine_hour` through [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) | legacy dependence removed |

## Dependence Removal Summary

- `unified_view` dependence on the routed Energy Analysis page: removed
- EUVG dependence on the routed Energy Analysis page: removed as the primary analytics source
- `unified_view` dependence on the maintenance efficiency curve: removed
- `unified_view` / EUVG dependence on dormant helper pages and unused helper modules: intentionally retained and documented as out of scope

## Direct-Source-Verified Live Smoke Summary

Smoke source:

- active DB: `manufacturing_data.db`
- canonical helper: [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)

### Energy Analysis smoke on `June 2025`

Direct-source-verified outputs:

- available canonical months: `January 2025` through `June 2025`
- selected month rows loaded: `62,639`
- distinct machines: `87`
- total energy: `1,243,942.5813 kWh`
- total good quantity: `119,306,012.80570014`
- average `kWh / good unit`: `0.0675119290140781`
- explicit unallocated energy: `77,653.644 kWh`

Top canonical energy buckets:

- `Production: 514,056.2879237941 kWh`
- `Setup: 279,657.5555209016 kWh`
- `Planned Stop: 264,909.3580501975 kWh`
- `Unplanned Stop: 102,873.41201495811 kWh`
- `Unallocated / Energy-Only: 77,653.644 kWh`

Top machine efficiency rows:

- `024-112: 0.0012467962139691578 kWh / good unit`
- `024-088: 0.0018248496350780328 kWh / good unit`
- `024-089: 0.003197603451760675 kWh / good unit`

Interpretation:

- the routed page now loads stable month-scoped output from canonical inputs only
- legacy EUVG / `unified_view` is no longer required as the primary analytics source
- the remaining non-reproducible slice is surfaced honestly as explicit unallocated energy instead of hidden fallback logic

### Maintenance efficiency curve smoke on live Jan-Jun canonical data

Direct-source-verified outputs:

- curve buckets returned: `6`
- `0-200h`: mean `0.032383169327516795`, count `39,450`
- `200-500h`: mean `0.035925012539702365`, count `34,616`
- `500-800h`: mean `0.03016963805581548`, count `21,101`
- `800-1200h`: mean `0.034262573455261264`, count `18,416`
- `1200-2000h`: mean `0.03151254560765287`, count `14,403`
- `2000-4000h`: mean `0.0257247810510339`, count `5,268`

Interpretation:

- the maintenance page can now build its efficiency-vs-maintenance-age curve directly from canonical rows
- no `unified_view` read is required for that user-facing chart anymore

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/canonical_energy_reader.py tests/test_canonical_energy_reader.py app.py modules/maintenance_module.py
./.conda311/bin/python -m unittest tests.test_canonical_energy_reader tests.test_canonical_gold_reader tests.test_canonical_ml_reader tests.test_canonical_optimization_reader
./.conda311/bin/python -c "from core.canonical_energy_reader import CanonicalEnergyReader; r=CanonicalEnergyReader(); month='June 2025'; df=r.read_month_energy_dataframe(month); summary=r.build_month_summary(df); breakdown=r.build_energy_breakdown(df).head(5); ranking=r.build_machine_efficiency_ranking(df).head(3); hourly=r.build_hourly_energy_profile(df).head(3); print('MONTHS', r.get_available_months()); print('ENERGY_ROWS', len(df)); print('SUMMARY', summary); print('BREAKDOWN_TOP5', breakdown.to_dict('records')); print('RANKING_TOP3', ranking.to_dict('records')); print('HOURLY_TOP3', hourly.to_dict('records'))"
./.conda311/bin/python -c "from core.canonical_energy_reader import CanonicalEnergyReader; r=CanonicalEnergyReader(); curve=r.build_maintenance_efficiency_curve(); print('CURVE_ROWS', len(curve)); print('CURVE', curve.to_dict('records'))"
```

Results:

- `py_compile`: passed
- focused/unit regression suite: `Ran 24 tests`, `OK`
- live June canonical energy smoke: passed
- live canonical maintenance curve smoke: passed

## Remaining Canonical / Runtime Split After This Task

Direct-source-verified:

- routed Energy Analysis is now canonical
- routed maintenance efficiency curve is now canonical
- canonical Unified View, canonical ML, and canonical Optimization were already canonical before this task

Still remaining:

- dormant Overview / Team Performance / legacy optimization helper code in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- unused shared ML helper tabs in [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py)
- unused legacy lookup helpers in [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)

Grounded judgment:

- current runtime canonical/legacy divergence is materially reduced
- the remaining split is now primarily dormant or helper-level technical debt, not the main routed analytics path

## Recommended Next Clean Task Boundary

- legacy cleanup of dormant helpers only

Not recommended as the next step from this task:

- no anomaly-policy follow-up
- no quantity follow-up on Task 4S
- no canonical retraining requirement caused by this alignment task
- no legacy compatibility-table regeneration
