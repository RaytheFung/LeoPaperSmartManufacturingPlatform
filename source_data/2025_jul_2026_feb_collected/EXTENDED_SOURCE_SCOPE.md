# Extended Source Scope

Repo-local raw source package for the post-June canonical extension.

## Scope

- CSI source files: July 2025 through February 2026
- Energy source files: July 2025 through March 2026 grouped workbooks
- MES source workbook: March 1, 2025 through February 28, 2026
- March 2026 remains intentionally excluded from the accepted canonical runtime scope unless a later task explicitly reopens that boundary.

## Runtime Use

`core.runtime_paths.get_extended_raw_dataset_root()` prefers `source_data/2025_jul_2026_feb_collected/` when present. If this folder is absent, it falls back to the older workspace-level package path.

## Notes

- Keep these files as raw source inputs.
- Do not place generated ETL reports or cache files here.
- Generated outputs belong under `etl_outputs/`, which is ignored except for `ETL_OUTPUTS_GUIDE.md` and the placeholder.
