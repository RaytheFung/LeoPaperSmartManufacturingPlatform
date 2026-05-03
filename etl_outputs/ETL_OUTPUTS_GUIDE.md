# ETL Outputs

This folder is for generated ETL reports, mapping JSON files, processing summaries, and `.xls` conversion cache files.

These files are intentionally not treated as source data. Regenerate them with:

```bash
python3 scripts/process_jan_to_june_2025.py
```

Current canonical runtime truth is the repo-local `manufacturing_data.db` plus the raw source folders:

- `source_data/2025_jan_jun_initial/`
- `source_data/2025_jul_2026_feb_collected/`
