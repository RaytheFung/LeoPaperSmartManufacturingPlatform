# TASK4S Canonical Path Sync Verification Report

## Outcome

This separate canonical-path sync verification task passed.

Scope stayed very narrow:

- no live DB write was performed
- no live `good_qty` / `scrap_qty` semantics changed
- no anomaly policy changed
- no model retraining ran
- no `unified_view` regeneration ran
- no dormant helper cleanup or bucket-policy redesign was folded into this task

Direct-source-verified result:

- the live routed maintenance curve already uses [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py), not a legacy `unified_view` query
- the live routed final bucket label is already `2000-4000h`
- no code retarget was needed in this task; the close here is repo-facing sync and verification only

## Live Path Confirmation

Direct-source-verified live repo paths audited from the real repo tree:

- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`tests/test_canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_energy_reader.py)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)

Result:

- the task prompt paths matched the real live repo tree
- the live routed maintenance curve path was already canonical before this task started
- the handover-facing repo docs already contained the later Task 4S downstream reports and the maintenance bucket label micro-task

## Exact Routed Maintenance Curve Source Path After Verification

Direct-source-verified routed call chain:

- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - builds `db_path = str(get_database_path())`
  - instantiates `canonical_energy_reader = CanonicalEnergyReader(db_path)`
  - calls `bucket_stats = canonical_energy_reader.build_maintenance_efficiency_curve()`
- [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py)
  - `build_maintenance_efficiency_curve()` uses `self.read_all_energy_dataframe()` when no month is supplied
  - `read_all_energy_dataframe()` returns `self._read_energy_dataframe()`
  - `_read_energy_dataframe()` executes a `SELECT ... FROM fact_machine_hour WHERE hour_ts IS NOT NULL`

Exact helper bucket contract audited from live code:

- `pd.cut(..., bins=[0, 200, 500, 800, 1200, 2000, 4000], labels=["0-200h", "200-500h", "500-800h", "800-1200h", "1200-2000h", "2000-4000h"], include_lowest=False, right=True)`
- grouped rows with `bucket IS NULL` are dropped before return

Direct-source-verified routed-path judgment:

- no routed `SELECT ... FROM unified_view` maintenance-curve path remains in [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- no routed `2000h+` label remains on the active maintenance-curve path

## Docs And Ledger Anchor Verification

Direct-source-verified status/index audit:

- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) already included:
  - Task 4S downstream alignment
  - Task 4S canonical energy metric hardening
  - Task 4S canonical summary contract audit
  - Task 4S maintenance curve narrative hardening
  - Task 4S maintenance bucket label hardening
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md) already indexed those same later Task 4S reports

Evidence-based note:

- the conflicting flattened/handover snapshot referenced by this task was not a repo file, so it was not edited directly here
- this task closes the repo-facing sync gap by adding a dedicated verification report plus explicit current-ledger/index anchors for the live canonical path

## Exact File List Touched

- [`docs/technical/TASK4S_CANONICAL_PATH_SYNC_VERIFICATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_PATH_SYNC_VERIFICATION_REPORT.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)

## Exact Reason For Each Change

- [`docs/technical/TASK4S_CANONICAL_PATH_SYNC_VERIFICATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_CANONICAL_PATH_SYNC_VERIFICATION_REPORT.md)
  - records the exact routed maintenance-curve source path, current bucket-label contract, repo-tree verification, and validation outputs for this separate sync task
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexes this verification close in the Task 4S chain so future handoff reads have an explicit repo-state reconciliation anchor
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - adds one factual live-ledger line stating the exact routed maintenance-curve call chain now source-verified end to end

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/canonical_energy_reader.py modules/maintenance_module.py tests/test_canonical_energy_reader.py
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_canonical_energy_reader
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python - <<'PY'
from pathlib import Path
import sqlite3

maintenance_source = Path("modules/maintenance_module.py").read_text(encoding="utf-8")
helper_source = Path("core/canonical_energy_reader.py").read_text(encoding="utf-8")

db_uri = f"file:{Path('manufacturing_data.db').resolve()}?mode=ro"
conn = sqlite3.connect(db_uri, uri=True)
curve = conn.execute(
    """
    WITH eligible AS (
        SELECT
            CASE
                WHEN hours_since_last_maintenance > 0 AND hours_since_last_maintenance <= 200 THEN '0-200h'
                WHEN hours_since_last_maintenance > 200 AND hours_since_last_maintenance <= 500 THEN '200-500h'
                WHEN hours_since_last_maintenance > 500 AND hours_since_last_maintenance <= 800 THEN '500-800h'
                WHEN hours_since_last_maintenance > 800 AND hours_since_last_maintenance <= 1200 THEN '800-1200h'
                WHEN hours_since_last_maintenance > 1200 AND hours_since_last_maintenance <= 2000 THEN '1200-2000h'
                WHEN hours_since_last_maintenance > 2000 AND hours_since_last_maintenance <= 4000 THEN '2000-4000h'
                ELSE NULL
            END AS bucket,
            energy_total_kwh,
            good_qty
        FROM fact_machine_hour
        WHERE hours_since_last_maintenance IS NOT NULL
          AND good_qty > 0
          AND energy_total_kwh IS NOT NULL
          AND (energy_total_kwh / good_qty) > 0
          AND (energy_total_kwh / good_qty) < 20
    )
    SELECT
        bucket,
        COUNT(*) AS row_count,
        SUM(good_qty) AS total_good_qty,
        SUM(energy_total_kwh) AS total_energy_kwh,
        SUM(energy_total_kwh) / SUM(good_qty) AS weighted_kwh_per_good_unit
    FROM eligible
    WHERE bucket IS NOT NULL
    GROUP BY bucket
    HAVING COUNT(*) >= 20 AND SUM(good_qty) > 0
    ORDER BY CASE bucket
        WHEN '0-200h' THEN 1
        WHEN '200-500h' THEN 2
        WHEN '500-800h' THEN 3
        WHEN '800-1200h' THEN 4
        WHEN '1200-2000h' THEN 5
        WHEN '2000-4000h' THEN 6
        ELSE 7
    END
    """
).fetchall()
conn.close()

print("ROUTED_CANONICAL_CALL", "canonical_energy_reader.build_maintenance_efficiency_curve()" in maintenance_source)
print("ROUTED_NO_LEGACY_UNIFIED_VIEW_QUERY", "FROM unified_view" not in maintenance_source)
print("ROUTED_NO_2000H_PLUS_LABEL", "2000h+" not in maintenance_source)
print("HELPER_HAS_2000_4000H_LABEL", '2000-4000h' in helper_source)
print("HELPER_READS_FACT_MACHINE_HOUR", "FROM fact_machine_hour" in helper_source)
print("CURVE_LAST_BUCKET", curve[-1] if curve else None)
PY
```

Results:

- `py_compile`: passed
- focused tests: passed
- read-only routed-path smoke: passed
- read-only helper bucket-label smoke: passed

## Whether The Live Repo And Flattened Snapshot Now Agree

Direct-source-verified:

- the live routed maintenance page, canonical helper, live ledger, and docs index now agree explicitly on the active canonical path and final bucket contract

Evidence-based:

- the external flattened/handover snapshot referenced by this task is not stored in the repo, so this task could not rewrite that external artifact itself
- the repo-facing handover surface is now synchronized to the real live path and should be used instead of any older flattened snapshot

## Whether The Routed Maintenance-Curve Contract Is Now Truly Source-Verified End To End

Direct-source-verified judgment:

- yes
- source path: [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py) -> [`core/canonical_energy_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_energy_reader.py) -> `fact_machine_hour`
- surfaced final routed bucket label: `2000-4000h`
- routed legacy `2000h+` label remaining on the active path: `no`

## Recommended Next Clean Boundary

- no further Task 4S canonical-path sync work is needed on the routed maintenance curve
- if future cleanup is desired, keep it separate as dormant legacy helper cleanup only
- do not widen the next step into quantity semantics, anomaly policy, model retraining, or `unified_view` regeneration
