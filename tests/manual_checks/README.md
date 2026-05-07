# Manual Checks Warning

The scripts in this folder are ad hoc investigation helpers. They are not production deployment scripts and are excluded from normal Stage C cleanup execution.

Some scripts may query or mutate the local `manufacturing_data.db`, alter legacy `unified_view` tables, or depend on historical assumptions. Do not run them without explicit approval, a confirmed DB backup/rollback path, and a clear reason tied to the current stage.

For routine Stage C branch hygiene, prefer the documented compile, unit-test, source-discovery compare, and unsafe-file scan commands in `README.md` and the current Stage C report.
