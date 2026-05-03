# Task14E Loadability Benchmark Matrix

## 1. benchmark command

- `'/private/tmp/task14e_gate_env/bin/python' scripts/run_task14e_loadability_probe.py --repo-root /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform --local-root /private/tmp/task14e_probe_artifacts`

## 2. file sizes

| Artifact | Path class | Bytes | Approx size |
| --- | --- | ---: | ---: |
| live model | current live path | 19,392,395 | 18.5 MiB |
| staged candidate model | current staged path | 34,060,500 | 32.5 MiB |
| staged candidate preprocessor | current staged path | 2,059,247 | 2.0 MiB |
| staged candidate model | fresh local copy | 34,060,500 | 32.5 MiB |
| staged candidate preprocessor | fresh local copy | 2,059,247 | 2.0 MiB |

## 3. load timings

| Artifact | Loader | Path class | Elapsed seconds | Outcome |
| --- | --- | --- | ---: | --- |
| live model | `pickle.load` | current live path | 1.0728650420005579 | success |
| staged candidate model | `pickle.load` | current staged path | 0.7879939160011418 | success |
| staged candidate model | `pickle.load` | fresh local copy | 0.8101852919990051 | success |
| staged candidate model | `joblib.load` | current staged path | 0.6791852499991364 | success |
| staged candidate model | `joblib.load` | fresh local copy | 0.6813109169997915 | success |

## 4. direct interpretation

- The staged candidate is practical to load.
- Current staged path versus local `/private/tmp` copy shows no meaningful delta.
- The prior Task14D3 candidate-load stall is not reproducible on the fresh Task14E Python 3.11 gate.
- The helper classified the retired artifact blocker as:
  - `mixed`
