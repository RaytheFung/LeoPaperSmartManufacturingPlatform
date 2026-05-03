# Source Data

Raw manufacturing source files are organized here by accepted ingestion scope.

## Folders

- `2025_jan_jun_initial/` - initial January-June 2025 source package used by the batch ETL rebuild path.
- `2025_jul_2026_feb_collected/` - later collected source package used for the accepted July 2025-February 2026 canonical extension. The grouped energy workbook includes March 2026 rows, but March 2026 remains outside the accepted canonical runtime scope unless reopened by a later task.

## Boundary

Keep this folder for raw source inputs only.

Generated ETL reports, mapping JSON files, summaries, and cache files belong under `etl_outputs/`, which is ignored except for `ETL_OUTPUTS_GUIDE.md` and the placeholder.
