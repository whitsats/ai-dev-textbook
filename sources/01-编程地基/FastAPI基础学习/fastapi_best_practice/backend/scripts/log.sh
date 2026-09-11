#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

LOG_FILE="logs/app.log"

if [ ! -f "$LOG_FILE" ]; then
  echo "[log] Log file not found: $LOG_FILE"
  exit 0
fi

tail -n 200 "$LOG_FILE"
