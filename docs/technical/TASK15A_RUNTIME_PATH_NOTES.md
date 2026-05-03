# Task15A Runtime Path Notes

## Default runtime DB path

- The accepted default runtime DB path is the repo-local file:
  - `manufacturing_data.db`
- Canonical runtime helpers resolve that path through:
  - `core/runtime_paths.get_database_path()`
- Normal runtime does **not** require a mirror DB path or a DB override.

## What the Task14F mirror means now

- `activation_validation_db_path` in the live Task14F provenance exists because Task14F validation used a verified mirror before the repo-local path had been re-proven.
- Task15A re-proved the repo-local path directly on:
  - raw SQLite access
  - `CanonicalGoldReader`
  - `CanonicalMLReader`
  - `CanonicalOptimizationReader`
  - `MLPredictor`
- After Task15A, the mirror path is historical validation/troubleshooting support only. It is not part of the normal default runtime contract.

## Launch reminder

- Recommended launch:
  - `bash scripts/bootstrap_py311_and_run.sh`
- Existing env launch:
  - `.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true`
- Those standard launch paths read the repo-local DB by default unless a caller explicitly passes a different `db_path` into lower-level helper code.
