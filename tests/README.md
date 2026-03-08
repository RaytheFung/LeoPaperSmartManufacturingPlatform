# Tests & Verification Scripts

This folder contains all test scripts and verification utilities for the Smart Manufacturing Platform.

## Contents

### Test Scripts
- `test_dynamic_predictions.py` - Tests ML prediction responsiveness to inputs
- `test_energy_attribution_fix.py` - Verifies energy attribution calculations
- `test_ui_fixes.py` - UI component testing

### Verification Scripts
- `verify_fix.py` - Verifies database fixes and column additions
- `explain_ml_status.py` - Explains current ML module status and data

## Usage

Run any test script directly:
```bash
python tests/test_dynamic_predictions.py
```

Or run verification:
```bash
python tests/verify_fix.py
```

## Note
These scripts are for development and testing purposes only. They are not required for production operation of the system.
