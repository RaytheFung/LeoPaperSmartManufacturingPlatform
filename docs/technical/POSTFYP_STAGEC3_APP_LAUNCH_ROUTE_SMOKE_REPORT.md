# Post-FYP Stage C3 App Launch Route Smoke Report

## Purpose

Stage C3 records app launch and routed smoke evidence for controlled factory deployment pilot readiness.

This stage proves the selected branch can pass the existing route/runtime contract tests and start Streamlit safely from a temporary workspace outside Git. It does not change active runtime behavior.

## Scope

This is a smoke-evidence and deployment-checklist task.

Changed files are limited to this C3 report and the rebuild docs index. Stage C3 did not modify `app.py`, `core/`, `modules/`, `scripts/`, tests, source data, generated outputs, model artifacts, or DB files.

Stage C3 did not run ETL, historical backfill, canonical materialization, carry-forward reconciliation execution, live/shared DB migration, model retraining, artifact promotion, source-discovery policy changes, runtime canonical predicate changes, data-quality runtime wiring, Streamlit write-control additions, or live DB mode creation.

## Factory deployment objective

The active objective remains controlled factory deployment pilot readiness with production-grade safety gates.

Stage C3 supports that objective by proving:

- the selected C3 branch launches the app shell in a local read-only runtime mode;
- core route visibility remains aligned with the defended runtime contract;
- loader-dependent legacy pages are not visible in the routed shell;
- the experimental route stays hidden in `demo_readonly` and visible only in `standard` / `pilot_review`;
- the app smoke can be run from `/tmp` without creating DB files inside the GitHub-safe tree;
- carry-forward remains disabled-by-default governance/preflight scaffolding, not active routed behavior.

This report does not claim production deployment is complete. Live/shared DB migration, promoted DB writes, operational owner acceptance, runtime carry-forward adoption, and ML artifact promotion remain gated future work.

## Static route contract smoke

Static route/runtime tests were run from the GitHub-safe tree:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_pycache python3.11 -m unittest tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities tests.test_runtime_paths
```

Result:

- `10` tests ran.
- Result was `OK`.

Defended core route labels confirmed by `tests.test_app_route_contract`:

- `🔄 ETL Pipeline`
- `📊 Canonical Operations Overview`
- `⚡ Energy Analysis`
- `🎯 Operational Decision Support`
- `🤖 Efficiency Prediction & Governance`
- `🔧 Maintenance`

The same route-contract test confirmed `loader_dependent_visible_pages` is empty in `standard`, `demo_readonly`, and `pilot_review`.

The same test confirmed:

- `🧪 Experimental Intelligence Lab` is visible in `standard`;
- `🧪 Experimental Intelligence Lab` is not visible in `demo_readonly`;
- `🧪 Experimental Intelligence Lab` is visible in `pilot_review`;
- routed shell routes do not use the dormant legacy loader;
- an artificial non-routed label remains classified as dormant-loader-dependent.

## Streamlit launch smoke method

Actual process smoke was run from a temporary workspace only:

```text
/tmp/leopaper_stage_c3_app_smoke/
```

Runtime environment:

- Python: `Python 3.11.15`
- Streamlit: `Streamlit, version 1.31.0`
- runtime mode: `SMART_MFG_RUNTIME_MODE=demo_readonly`
- port: `8502`
- address: `127.0.0.1`
- headless: `true`
- log path outside Git: `/tmp/leopaper_stage_c3_logs/streamlit_8502_foreground.log`

Launch command used from the `/tmp` smoke workspace:

```bash
SMART_MFG_RUNTIME_MODE=demo_readonly PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_pycache python3.11 -m streamlit run app.py --server.port 8502 --server.address 127.0.0.1 --server.headless true 2>&1 | tee /tmp/leopaper_stage_c3_logs/streamlit_8502_foreground.log
```

No buttons were clicked. No files were uploaded. No browser navigation beyond the Streamlit bootstrap GET was attempted. ETL, backfill, materialization, carry-forward reconciliation, and DB promotion were not triggered.

## Smoke workspace boundary

The temporary smoke workspace was created under `/tmp`, not inside the GitHub-safe tree and not inside the original runtime repo.

Copied into `/tmp/leopaper_stage_c3_app_smoke/`:

- `app.py`
- `core/`
- `modules/`
- `config/`
- `static/`
- `.streamlit/`
- `requirements.txt`

Intentionally not copied:

- `.git`
- `manufacturing_data.db`
- `*.db`, `*.sqlite`, `*.sqlite3`
- `source_data/`
- `data/`
- `models/`
- `etl_outputs/`
- `.venv/`, `.conda311/`, `.miniforge/`
- `temp_uploads/`

Raw source workbooks were skipped because the app shell bootstrap and route-contract smoke do not require them. Model artifacts were skipped because import-time shell smoke does not require model loading, and this stage must not retrain, promote, or alter artifacts. Generated output folders were skipped because they are not source truth and should not be part of process-smoke evidence.

Temporary workspace unsafe scan:

```bash
find /tmp/leopaper_stage_c3_app_smoke -maxdepth 5 \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print
```

Result: no DB or SQLite file was found.

## HTTP/log/process evidence

Before launch, `8502` and `8503` had no listener.

Process evidence:

- Streamlit started successfully from `/tmp/leopaper_stage_c3_app_smoke/`.
- Listener observed on `127.0.0.1:8502`.
- Observed process command: `python3.1 ... TCP 127.0.0.1:8502 (LISTEN)`.

HTTP evidence:

```bash
curl -sS -o /tmp/leopaper_stage_c3_logs/http_8502_body_second.txt -w '%{http_code} %{content_type} %{size_download}\n' http://127.0.0.1:8502/
```

Result:

```text
200 text/html 891
```

Log evidence:

```text
You can now view your Streamlit app in your browser.
URL: http://127.0.0.1:8502
For better performance, install the Watchdog module:
Stopping...
```

Traceback scan:

```bash
rg -n "Traceback|Exception|Error|Stopping" /tmp/leopaper_stage_c3_logs/streamlit_8502_foreground.log || true
```

Result: no `Traceback`, `Exception`, or `Error` lines were found. The only match was the expected `Stopping...` line after termination.

Termination evidence:

- The Streamlit process was stopped with `kill <pid>`.
- A follow-up listener check on `127.0.0.1:8502` returned no listener.
- A follow-up `curl` returned `000` because the process was no longer listening.

## Route visibility evidence

The route visibility probe was run from the GitHub-safe tree without importing or executing routed page bodies:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_pycache python3.11 - <<'PY'
import json
from core.runtime_capabilities import get_runtime_capabilities, get_visible_pages
from core.runtime_mode import STANDARD_RUNTIME_MODE, DEMO_READONLY_RUNTIME_MODE, PILOT_REVIEW_RUNTIME_MODE
for mode in (STANDARD_RUNTIME_MODE, DEMO_READONLY_RUNTIME_MODE, PILOT_REVIEW_RUNTIME_MODE):
    print(json.dumps({"mode": mode, "visible_pages": get_visible_pages(mode), "capabilities": get_runtime_capabilities(mode)}, ensure_ascii=False, sort_keys=True))
PY
```

Observed visibility:

| Runtime mode | Visible routes | Write-control stance | Experimental route |
| --- | --- | --- | --- |
| `standard` | `🔄 ETL Pipeline`, `📊 Canonical Operations Overview`, `⚡ Energy Analysis`, `🎯 Operational Decision Support`, `🤖 Efficiency Prediction & Governance`, `🔧 Maintenance`, `🧪 Experimental Intelligence Lab` | `suppress_write_controls = false` | exposed |
| `demo_readonly` | `🔄 ETL Pipeline`, `📊 Canonical Operations Overview`, `⚡ Energy Analysis`, `🎯 Operational Decision Support`, `🤖 Efficiency Prediction & Governance`, `🔧 Maintenance` | `suppress_write_controls = true` | hidden |
| `pilot_review` | `🔄 ETL Pipeline`, `📊 Canonical Operations Overview`, `⚡ Energy Analysis`, `🎯 Operational Decision Support`, `🤖 Efficiency Prediction & Governance`, `🔧 Maintenance`, `🧪 Experimental Intelligence Lab` | `suppress_write_controls = true` | exposed |

The required route labels were all present in the appropriate runtime modes.

## DB/artifact safety evidence

GitHub-safe tree DB scan:

```bash
find /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_github_safe -maxdepth 5 \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print
```

Result: no DB or SQLite file was found.

Temporary smoke workspace DB scan:

```bash
find /tmp/leopaper_stage_c3_app_smoke -maxdepth 5 \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print
```

Result: no DB or SQLite file was found.

Original runtime repo DB boundary check:

```text
/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db 7226900480 Apr 17 21:59:22 2026
```

Stage C3 did not run from the original runtime repo and did not write the original runtime DB.

No raw Excel files, model artifacts, generated `etl_outputs`, local env folders, upload folders, or DB files were staged.

## Deployment pilot checklist

| Item | C3 status |
| --- | --- |
| selected branch | `postfyp/stage-c3-app-launch-route-smoke` |
| base branch | `origin/postfyp/stage-c2-production-docs-navigation-cleanup` at `a69f3a8e0f4cd086a21c2d73292778b15a92a579` |
| Python launch path | `python3.11 -m streamlit` |
| Streamlit version | `1.31.0` |
| runtime mode for process smoke | `demo_readonly` |
| process smoke workspace | `/tmp/leopaper_stage_c3_app_smoke/` |
| DB local-only rule | preserved |
| no DB in Git rule | preserved |
| source-data boundary | raw source workbooks not copied into smoke workspace and not staged |
| generated output boundary | `etl_outputs/` not copied into smoke workspace and not staged |
| model artifact boundary | model artifacts not copied, retrained, promoted, or staged |
| carry-forward state | disabled-by-default; not active route behavior |
| live/shared DB migration gate | still gated; not executed |
| app smoke status | passed on `127.0.0.1:8502` with HTTP `200 text/html` |
| route contract status | passed, `10` tests OK |
| remaining blockers before real factory pilot | live/shared DB migration gate, rollback/restore proof for promoted writes, operational owner acceptance, production runbook ownership, runtime carry-forward adoption gate if ever approved, live environment secrets/access policy, monitoring and support process |

## Runtime behavior impact

No runtime behavior changed.

Stage C3 did not modify `app.py`, active runtime Python files, route definitions, runtime modes, runtime capabilities, source discovery, canonical predicates, DQ rules, carry-forward code, ML artifacts, Streamlit controls, source data, generated output, or DB state.

## Validation

Validation commands run from the GitHub-safe tree:

```bash
git status --short
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_pycache python3.11 -m unittest tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities tests.test_runtime_paths
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_pycache python3.11 - <<'PY'
import json
from core.runtime_capabilities import get_runtime_capabilities, get_visible_pages
from core.runtime_mode import STANDARD_RUNTIME_MODE, DEMO_READONLY_RUNTIME_MODE, PILOT_REVIEW_RUNTIME_MODE
for mode in (STANDARD_RUNTIME_MODE, DEMO_READONLY_RUNTIME_MODE, PILOT_REVIEW_RUNTIME_MODE):
    print(json.dumps({"mode": mode, "visible_pages": get_visible_pages(mode), "capabilities": get_runtime_capabilities(mode)}, ensure_ascii=False, sort_keys=True))
PY
python3.11 -V
python3.11 -m streamlit --version
```

Results:

- initial `git status --short` was clean;
- route/runtime unit tests passed with `10` tests;
- route visibility probe returned the expected standard, demo-readonly, and pilot-review route sets;
- Python version was `Python 3.11.15`;
- Streamlit version was `1.31.0`.

Final validation was rerun after the report/index edits.

Final validation commands and results:

- `git status --short` showed only `docs/technical/REBUILD_DOCS_INDEX.md` modified and `docs/technical/POSTFYP_STAGEC3_APP_LAUNCH_ROUTE_SMOKE_REPORT.md` untracked before staging.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_compile_pycache python3.11 -m compileall core modules scripts tests` passed.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_tests_a_pycache python3.11 -m unittest tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities tests.test_runtime_paths` passed with `10` tests.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_tests_b_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter` passed with `34` tests.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_compare_pycache python3.11 scripts/compare_source_discovery_modes.py` returned `overall: PASS`.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c3_compare_json_pycache python3.11 scripts/compare_source_discovery_modes.py --json` returned `"success": true`, `accepted_month_count: 8`, and `expected_blocked_month_count: 1`.

## Unsafe file scan

Unsafe scans required for Stage C3:

```bash
find . -maxdepth 5 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print
find . -maxdepth 5 \( -name ".venv" -o -name ".conda311" -o -name ".miniforge" -o -name "temp_uploads" \) -print
git ls-files manufacturing_data.db || true
git check-ignore --no-index -v manufacturing_data.db || true
git status --ignored --short | head -100
```

Observed before commit:

- DB scan returned no `*.db`, `*.sqlite`, or `*.sqlite3` files under max depth 5.
- Local environment/upload scan returned no `.venv`, `.conda311`, `.miniforge`, or `temp_uploads` folders under max depth 5.
- `git ls-files manufacturing_data.db || true` returned no tracked file.
- `git check-ignore --no-index -v manufacturing_data.db || true` returned `.gitignore:5:*.db manufacturing_data.db`.
- `git status --ignored --short | head -100` showed only intended docs changes plus ignored `__pycache__/` folders; no DB, raw Excel, model artifact, generated `etl_outputs`, or local env/upload artifact was staged.

## Skipped/blocked smoke items

Browser-click navigation was skipped. Stage C3 used existing route-contract tests, the runtime-capability probe, and a non-interactive HTTP bootstrap GET instead.

This was intentional because the prompt prohibited write actions and said not to attempt browser-click navigation unless a stable AppTest pattern already exists and is known not to write DB.

No AppTest smoke was added in C3. Existing route/runtime contract tests already cover the requested route labels and visibility behavior without invoking routed page write paths.

An initial background-wrapper process attempt was not counted as evidence because it exited before a listener was observed and produced no useful log. The durable evidence in this report comes from the foreground Streamlit process with output captured to `/tmp/leopaper_stage_c3_logs/streamlit_8502_foreground.log`.

## Remaining risks

- Streamlit bootstrap smoke proves app shell availability, not full page-by-page functional execution.
- No production/shared DB migration has been executed.
- Original runtime DB safety was preserved by not running from the original repo, but real factory deployment still needs backup, checksum, rollback, restore, and reviewer acceptance gates.
- CSI carry-forward remains disabled-by-default and is not active runtime behavior.
- Experimental Intelligence Lab remains an internal review lane, not defended production execution.
- Operational monitoring, support ownership, incident response, access policy, and real factory environment configuration remain future work.

## Recommended C4

Recommended C4 should prepare a deployment runbook and migration-gate checklist without executing live/shared DB migration.

C4 should define:

- operator startup and stop procedure;
- accepted runtime mode for pilot review;
- local DB backup/checksum/restore checklist;
- no-DB-in-Git verification checklist;
- source-data and generated-output handling rules;
- explicit live/shared DB migration approval gates;
- rollback and abort criteria;
- operational owner acceptance checklist;
- smoke matrix required before any factory pilot handoff.
