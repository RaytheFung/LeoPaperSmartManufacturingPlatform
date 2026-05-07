# Smart Manufacturing Analytics Platform

Streamlit application for monthly manufacturing ETL, canonical operations review, energy analysis, maintenance evidence, ML-assisted efficiency prediction, and operational decision support.

## Current Direction

This repository is being hardened for controlled factory deployment pilot readiness with production-grade safety gates.

The current state is not a completed production launch. Live/shared DB migration, promoted DB writes, runtime carry-forward adoption, and model artifact promotion remain gated future work. The local runtime database is a rehearsal and review boundary until a later production migration gate approves backup, checksum, rollback, app smoke, reviewer acceptance, and abort criteria.

## Current Working Set

Primary runtime files:
- `app.py` - Streamlit entry point.
- `modules/` - routed page modules used by the app.
- `core/` - ETL, canonical readers/materializers, ML, maintenance, runtime-mode, and support logic.
- `config/source_manifest.v1.json` - accepted source-scope and source-discovery contract.
- `config/data_quality_rules.v1.json` - data-quality rule metadata; not active runtime enforcement.
- `manufacturing_data.db` - local SQLite runtime data store used by the app; ignored by Git and never staged, committed, or pushed.
- `models/production_efficiency_model.pkl` and `models/production_preprocessor.pkl` - active model/preprocessor artifacts with provenance manifests.
- `source_data/` - source truth for accepted historical packages.
- `etl_outputs/` - generated ETL reports, mappings, summaries, and cache files; ignored except for `ETL_OUTPUTS_GUIDE.md` and `.gitkeep`.
- `scripts/bootstrap_py311_and_run.sh` - recommended launcher on macOS.
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` - authoritative routed-runtime ownership map.
- `docs/technical/DATA_CONTRACTS_GUIDE.md` - source, data-quality, local DB, and carry-forward boundary guide.
- `docs/technical/REBUILD_DOCS_INDEX.md` - technical evidence ledger and reading order.

Historical or review-support files:
- `project_context.md` is historical context only, not current deployment truth.
- `data/` contains older sample inputs and should not be treated as the production source-of-truth folder.
- Older `docs/technical/TASK*` reports remain evidence records, not current operator runbooks.

## Safety Boundaries

- Do not stage or commit `manufacturing_data.db`, `*.db`, `*.sqlite`, or `*.sqlite3`.
- Do not stage raw Excel source changes unless a future source-data governance task explicitly approves them.
- Do not stage generated `etl_outputs` files.
- Do not retrain or promote ML artifacts unless a separate model-promotion gate approves it.
- Do not treat carry-forward as active ETL runtime behavior. CSI carry-forward scaffolding is disabled-by-default and remains governance/preflight evidence until a separate adoption gate approves runtime wiring.
- Do not treat live/shared DB migration as abandoned. It remains gated and must pass production-grade migration, backup, rollback, traceability, app-smoke, reviewer-acceptance, and abort-criteria checks before any promoted DB write.
- Do not change source-discovery default policy or runtime canonical predicates without an explicit approved stage.

## Source And Generated Data

- `source_data/2025_jan_jun_initial/` contains accepted January 2025 through June 2025 source scope.
- `source_data/2025_jul_2026_feb_collected/` contains accepted July 2025 through February 2026 extension source scope. Grouped energy files can contain March 2026 rows, but March 2026 remains blocked/out of canonical scope unless a later task reopens that boundary.
- `etl_outputs/` is generated output, not source truth. Generated reports, cache files, and mappings should be recreated by controlled ETL runs rather than committed as product state.

## Run The App

Recommended on macOS:

```bash
bash scripts/bootstrap_py311_and_run.sh
```

Then open:

```text
http://localhost:8502
```

Alternative if the local Python 3.11 environment already exists:

```bash
.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true
```

Stop the app:

```bash
pkill -f "streamlit run app.py"
```

## Deployment-Readiness Checks

Use these checks for lightweight branch hygiene and runtime-surface confidence. They do not run ETL, historical backfill, canonical materialization, live DB migration, or model promotion.

```bash
python3.11 -m compileall core modules scripts tests
python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities
python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
python3.11 scripts/compare_source_discovery_modes.py
python3.11 scripts/compare_source_discovery_modes.py --json
```

Manual checks under `tests/manual_checks/` are not production deployment scripts. Some may query or mutate the local DB. Read `tests/manual_checks/README.md` before running them.

## Docs Navigation

- `docs/DOCS_GUIDE.md` - production-readiness navigation guide.
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` - current routed-runtime ownership map.
- `docs/technical/DATA_CONTRACTS_GUIDE.md` - source manifest, data-quality metadata, local DB, and carry-forward boundaries.
- `docs/technical/REBUILD_DOCS_INDEX.md` - Stage A/B/C evidence ledger.
- `docs/LAUNCHING_TIPS.md` - local app launch tips.
- `docs/technical/POSTFYP_STAGEC1_PRODUCTION_READINESS_INVENTORY_REPORT.md` and later Stage C reports - production-readiness cleanup evidence.

## Notes

- `run_app.sh` exists, but the Python 3.11 bootstrap path is the safer default on macOS.
- If current docs conflict, trust `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`, `docs/technical/DATA_CONTRACTS_GUIDE.md`, the live code under `app.py`, `core/`, `modules/`, and the latest Stage C report.
