#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PID_FILE="run/app.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "[stop] No pid file: $PID_FILE"
  exit 0
fi

PID="$(cat "$PID_FILE" || true)"
if [ -z "${PID:-}" ]; then
  echo "[stop] Empty pid file. Removing $PID_FILE"
  rm -f "$PID_FILE"
  exit 0
fi

if ! kill -0 "$PID" 2>/dev/null; then
  echo "[stop] Process not running (pid=$PID). Removing stale pid file."
  rm -f "$PID_FILE"
  exit 0
fi

echo "[stop] Stopping pid=$PID ..."
kill "$PID" 2>/dev/null || true

# Wait up to ~10s for graceful shutdown
for i in {1..50}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "[stop] Stopped."
    exit 0
  fi
  sleep 0.2
done

echo "[stop] Still running, force kill pid=$PID"
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "[stop] Stopped (forced)."
