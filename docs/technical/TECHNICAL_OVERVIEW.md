# Technical Overview

This document orients contributors for the current production-readiness cleanup path.

Canonical references:
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` is the current routed-runtime ownership map.
- `docs/technical/DATA_CONTRACTS_GUIDE.md` is the current source, data-quality metadata, local DB, and carry-forward boundary guide.
- `docs/technical/REBUILD_DOCS_INDEX.md` is the evidence ledger and Stage A/B/C report index.
- `project_context.md` is historical context only.

## Architecture Map

- Streamlit entry point: `app.py`
- Routed pages: `modules/etl_module.py`, `modules/unified_view_module.py`, `modules/energy_module.py`, `modules/optimization_module.py`, `modules/ml_module.py`, `modules/maintenance_module.py`, `modules/experimental_intelligence_lab_module.py`
- ETL and canonical backbone: `core/enhanced_etl_solution_CURRENT.py`, `core/bronze_raw_store.py`, `core/silver_normalizer.py`, `core/canonical_materializer.py`, `core/gold_fact_builder.py`, `core/etl/`
- Canonical readers: `core/canonical_gold_reader.py`, `core/canonical_energy_reader.py`, `core/canonical_ml_reader.py`, `core/canonical_optimization_reader.py`
- ML artifacts and inference: `core/ml_predictor.py`, `core/ml_trainer.py`, `models/production_efficiency_model.pkl`, `models/production_preprocessor.pkl`, and provenance manifests
- Maintenance evidence: `core/maintenance_evidence.py`, `core/maintenance_integration.py`
- Source discovery and contracts: `config/source_manifest.v1.json`, `config/data_quality_rules.v1.json`, `core/source_manifest_discovery.py`, `core/data_contracts.py`
- Runtime path contract: `core/runtime_paths.py`
- Local runtime DB: `manufacturing_data.db`, local-only and never staged or pushed

## Production-Readiness Boundary

The active objective is controlled factory deployment pilot readiness. The repo is being cleaned and documented for deployment hygiene, not declared fully production-launched.

Still gated:
- live/shared DB migration;
- promoted DB writes;
- runtime CSI carry-forward adoption;
- data-quality rule runtime enforcement;
- source-discovery policy expansion;
- runtime canonical predicate changes;
- ML retraining or artifact promotion;
- production ownership/rollback acceptance.

## Active Runtime Notes

- Defended routed analytics read canonical `fact_machine_hour` surfaces where current ownership docs say they do.
- `modules/unified_view_module.py` remains active for the Canonical Operations Overview route, but older `unified_view` helper paths in the same file are legacy/support debt.
- `modules/euvg_module.py`, `modules/shared_ml_components.py`, and `modules/dormant_legacy_app_helpers.py` remain legacy or historical-support candidates. Do not move or edit them without dependency proof and explicit approval.
- The Experimental Intelligence Lab is an internal review lane, not defended production execution.

## Lightweight Validation

These checks support Stage C docs/navigation and branch hygiene without running ETL, backfill, materialization, live migration, or model promotion:

```bash
python3.11 -m compileall core modules scripts tests
python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities
python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
python3.11 scripts/compare_source_discovery_modes.py
python3.11 scripts/compare_source_discovery_modes.py --json
```

Manual checks under `tests/manual_checks/` require explicit approval and DB backup review before execution.
