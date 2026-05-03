#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "Starting Smart Manufacturing App..."
echo "========================================="
echo "App will be available at:"
echo "  → http://localhost:8502"
echo "  → http://127.0.0.1:8502"
echo "Press Ctrl+C to stop the server"
echo "========================================="

ENV_DIR="$ROOT_DIR/.conda311"
BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/bootstrap_py311_and_run.sh"

if [[ ! -x "$ENV_DIR/bin/streamlit" ]]; then
  echo "Repo-local Python 3.11 env missing or incomplete."
  echo "Bootstrapping Miniforge + .conda311 ..."
  exec bash "$BOOTSTRAP_SCRIPT"
fi

# Prepare log directory/file
mkdir -p .streamlit
LOG_FILE=.streamlit/server.log
PID_FILE=.streamlit/server.pid

# Start the app on port 8502 (matches .streamlit/config.toml)
echo "Launching Streamlit..."
pkill -f "streamlit run app.py" 2>/dev/null || true
nohup "$ENV_DIR/bin/streamlit" run app.py \
  --server.port 8502 \
  --server.address 0.0.0.0 \
  --server.headless true \
  > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

sleep 1
if grep -qiE "(Running on|Network URL|Local URL)" "$LOG_FILE"; then
  echo "Streamlit started successfully."
else
  echo "Note: Streamlit starting in background. Check logs: $LOG_FILE"
fi

echo "Open: http://localhost:8502"
