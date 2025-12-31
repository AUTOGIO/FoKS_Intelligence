#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv_foks"

echo "[FoKS] Starting backend from: $BACKEND_DIR"
cd "$BACKEND_DIR"

if [ ! -d "$VENV_DIR" ]; then
  echo "[FoKS] Creating virtualenv..."
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "[FoKS] Installing dependencies..."
pip install --upgrade pip >/dev/null 2>&1
pip install -r requirements.txt >/dev/null 2>&1

echo "[FoKS] Running uvicorn on port 8000..."
# Always use python -m uvicorn to ensure .venv_foks is used
# Never rely on system uvicorn binaries
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

