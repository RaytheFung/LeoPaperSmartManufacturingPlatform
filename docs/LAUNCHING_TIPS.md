Quick Launch and Troubleshooting (Streamlit)

Recommended one‑liner
- `bash scripts/bootstrap_py311_and_run.sh`

What it does
- Installs Miniforge (user‑space) into `.miniforge` if missing
- Creates Python 3.11 env at `.conda311`
- Installs `requirements.txt`
- Starts Streamlit on `http://localhost:8502`
- Writes logs to `.streamlit/server.log` and PID to `.streamlit/server.pid`

Start/stop/restart
- Start: `bash scripts/bootstrap_py311_and_run.sh`
- Stop: `pkill -f "streamlit run app.py"`
- Manual start from env: `.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true`

Ports and config
- Config: `.streamlit/config.toml` sets `port = 8502`, `address = "0.0.0.0"`
- Open: `http://localhost:8502`

Troubleshooting
- Segmentation fault on macOS
  - Cause: Apple/Xcode Python 3.9 + compiled libs (`numpy`, etc.) on new macOS.
  - Fix: Use the Python 3.11 env (`.conda311`) via the bootstrap script above.
- tzpath warning (zoneinfo)
  - Cause: Special characters like `:` or some non‑ASCII in folder name.
  - Action: Safe to ignore; or rename the project folder to a simpler name.
- No page loads / blank tab
  - Check port: `nc -z 127.0.0.1 8502` should be open.
  - Check logs: `tail -n 200 .streamlit/server.log`
  - Restart: `pkill -f "streamlit run app.py" && bash scripts/bootstrap_py311_and_run.sh`

For assistants (Codex CLI)
- Prefer the bootstrap script.
- If you must, install Miniforge and create `.conda311`:
  - Download Miniforge (arm64/x86_64), install to `.miniforge`
  - `/.miniforge/bin/mamba create -y -p ./.conda311 python=3.11`
  - `./.conda311/bin/pip install -r requirements.txt`
  - Start Streamlit as above

