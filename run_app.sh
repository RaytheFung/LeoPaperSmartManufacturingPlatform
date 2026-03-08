#!/usr/bin/env bash
set -euo pipefail

echo "Starting Smart Manufacturing App..."
echo "========================================="
echo "App will be available at:"
echo "  → http://localhost:8502"
echo "  → http://127.0.0.1:8502"
echo "Press Ctrl+C to stop the server"
echo "========================================="

# Create and use a local venv if missing
if [[ ! -d .venv ]]; then
  echo "Creating Python virtual environment (.venv)..."
  /usr/bin/python3 -m venv .venv
fi

echo "Ensuring dependencies are installed..."
"$(pwd)"/.venv/bin/pip install -q --upgrade pip
"$(pwd)"/.venv/bin/pip install -q -r requirements.txt

# Prepare log directory/file
mkdir -p .streamlit
LOG_FILE=.streamlit/server.log
PID_FILE=.streamlit/server.pid

# Start the app on port 8502 (matches .streamlit/config.toml)
echo "Launching Streamlit..."
nohup "$(pwd)"/.venv/bin/streamlit run app.py \
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
