# Tests Guide

## Automated Tests

These are the current repeatable tests worth keeping in the main `tests/` path:
- `tests/test_etl_modules.py`
- `tests/test_euvg_stage3.py`

Run them with:

```bash
python3 -m unittest tests.test_etl_modules tests.test_euvg_stage3
```

## Manual Checks

Ad hoc diagnostics and one-off verification scripts live in `tests/manual_checks/`.
They are useful for investigation, but they are not part of the automated regression suite.

Examples:

```bash
python3 tests/manual_checks/check_dynamic_predictions.py
python3 tests/manual_checks/verify_energy_fix.py
```
