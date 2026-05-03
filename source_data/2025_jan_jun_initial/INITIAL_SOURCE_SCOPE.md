# Initial Source Scope

Repo-local raw source package for the January-June 2025 batch ETL rebuild path.

## Scope

- Maintenance source files: 2025 maintenance records used by the maintenance cleaning path.
- CSI source files: January 2025 through June 2025 monthly workbooks.
- Energy source files: January 2025 through June 2025 interval workbooks.
- MES source files: January 2025 through June 2025 monthly production workbooks.

## Runtime Use

`core.runtime_paths.get_raw_dataset_root()` prefers `source_data/2025_jan_jun_initial/` when present. If this folder is absent, it falls back to the older workspace-level package path.

## Notes

- Keep these files as raw source inputs.
- Do not place generated ETL reports or cache files here.
- Generated outputs belong under `etl_outputs/`, which is ignored except for `ETL_OUTPUTS_GUIDE.md` and the placeholder.
