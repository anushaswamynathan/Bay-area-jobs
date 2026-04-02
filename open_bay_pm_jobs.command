#!/bin/zsh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_URL="http://127.0.0.1:4174"

if ! curl -sf "$APP_URL/api/state" >/dev/null 2>&1; then
  cd "$SCRIPT_DIR"
  nohup env BAY_PM_JOBS_PORT=4174 python3 server.py >/tmp/bay-pm-jobs-local.out 2>/tmp/bay-pm-jobs-local.err &
  sleep 1
fi

open "$APP_URL"
