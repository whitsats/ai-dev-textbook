#!/usr/bin/env bash
set -euo pipefail

# Run from backend/ root
cd "$(dirname "$0")/.."

mkdir -p logs run

# Pick venv python (Linux/Mac or Windows Git-Bash)
PYTHON=""
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/Scripts/python" ]; then
  PYTHON=".venv/Scripts/python"
else
  echo "[start] ERROR: .venv python not found under backend/.venv" >&2
  echo "[start] Expected .venv/bin/python or .venv/Scripts/python(.exe)" >&2
  exit 1
fi

PID_FILE="run/app.pid"
LOG_FILE="logs/app.log"

# Prevent duplicate start
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[start] Already running (pid=$OLD_PID)."
    echo "[start] Log: $LOG_FILE"
    exit 0
  fi
fi

# Start backend/main.py using backend/.venv
nohup "$PYTHON" -u main.py > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "[start] Started (pid=$NEW_PID)"
echo "[start] Log: $LOG_FILE"
