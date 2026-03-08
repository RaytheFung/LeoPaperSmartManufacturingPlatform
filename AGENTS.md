Agent Notes: Launching the Streamlit App Fast and Safely

Scope: Entire repository

Primary goal: Avoid macOS Python segfaults and get the app running quickly on port 8502 with reliable logs.

Fast path (recommended)
- Run: `bash scripts/bootstrap_py311_and_run.sh`
- This installs Miniforge locally (user-space), creates `.conda311` (Python 3.11), installs `requirements.txt`, and launches Streamlit on `http://localhost:8502`.
- Logs: `.streamlit/server.log`, PID: `.streamlit/server.pid`
- Stop: `pkill -f "streamlit run app.py"`

If the app is already set up
- Start: `.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true`
- Or: `bash run_app.sh` (uses venv). Note: On some macOS setups Apple’s system Python 3.9 can segfault with Streamlit. Prefer the Python 3.11 path above.

What to check
- Port: `.streamlit/config.toml` sets `port = 8502` and `address = "0.0.0.0"`.
- Entry point: `app.py`
- Health: `tail -n 200 .streamlit/server.log`

Common pitfalls and fixes
- Segmentation fault on import of `streamlit`/`numpy`: Use Python 3.11 via `.conda311` (bootstrap script above). Avoid Apple’s `/usr/bin/python3`.
- Folder name warnings (zoneinfo): Non-ASCII or `:` in folder names may trigger tz warnings; safe to ignore, or rename the folder.
- Fresh install issues: If `pip` needs Xcode CLI tools for watchdog, advise `xcode-select --install` (optional).

Share link
- Use `http://localhost:8502`.

