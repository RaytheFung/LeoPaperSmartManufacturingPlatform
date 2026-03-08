#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a local Python 3.11 env (user-space) and run Streamlit on 8502

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/5] Detecting platform..."
ARCH="$(uname -m)"
OS="$(uname -s)"
if [[ "$OS" != "Darwin" ]]; then
  echo "This script is tailored for macOS. Detected: $OS" >&2
  exit 1
fi

MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh"
if [[ "$ARCH" == "x86_64" ]]; then
  MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
fi

INSTALL_DIR="$ROOT_DIR/.miniforge"
ENV_DIR="$ROOT_DIR/.conda311"
CACHE_DIR="$ROOT_DIR/.installer_cache"
mkdir -p "$CACHE_DIR" .streamlit

echo "[2/5] Ensuring Miniforge is installed at $INSTALL_DIR ..."
if [[ ! -d "$INSTALL_DIR" ]]; then
  echo "Downloading Miniforge from: $MINIFORGE_URL"
  curl -L "$MINIFORGE_URL" -o "$CACHE_DIR/miniforge.sh"
  chmod +x "$CACHE_DIR/miniforge.sh"
  bash "$CACHE_DIR/miniforge.sh" -b -p "$INSTALL_DIR"
else
  echo "Miniforge already present. Skipping install."
fi

echo "[3/5] Creating Python 3.11 environment at $ENV_DIR ..."
if [[ ! -d "$ENV_DIR" ]]; then
  "$INSTALL_DIR/bin/mamba" create -y -p "$ENV_DIR" python=3.11
else
  echo "Conda env already exists. Skipping create."
fi

echo "[4/5] Installing requirements into the env..."
"$ENV_DIR/bin/python" -m pip install --upgrade pip
"$ENV_DIR/bin/pip" install -r requirements.txt

echo "[5/5] Launching Streamlit on port 8502 ..."
# Stop any existing server on this project
pkill -f "streamlit run app.py" 2>/dev/null || true

LOG_FILE=".streamlit/server.log"
PID_FILE=".streamlit/server.pid"
nohup "$ENV_DIR/bin/streamlit" run app.py \
  --server.port 8502 \
  --server.address 0.0.0.0 \
  --server.headless true \
  > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

sleep 1
echo "App starting... Logs: $LOG_FILE"
echo "Open: http://localhost:8502"

if command -v open >/dev/null 2>&1; then
  (sleep 1 && open "http://localhost:8502") >/dev/null 2>&1 || true
fi

exit 0

