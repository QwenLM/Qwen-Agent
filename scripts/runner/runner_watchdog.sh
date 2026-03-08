#!/usr/bin/env bash
set -euo pipefail

# Runner watchdog:
# - Ensures GitHub runner service is active.
# - Restarts service if inactive.
# - Emits lightweight diagnostics to runner/watchdog log dir.

RUNNER_DIR="${RUNNER_DIR:-/Users/ahjan/Qwen-Agent/actions-runner}"
LOG_DIR="${LOG_DIR:-$RUNNER_DIR/_diag/watchdog}"
MAX_BROKER_ERRORS_WINDOW="${MAX_BROKER_ERRORS_WINDOW:-20}"

mkdir -p "$LOG_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/watchdog_${TS}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "[watchdog] ts=${TS}"
echo "[watchdog] runner_dir=${RUNNER_DIR}"

if [ ! -d "$RUNNER_DIR" ]; then
  echo "[watchdog] ERROR: runner dir not found"
  exit 1
fi

cd "$RUNNER_DIR"

STATUS_OUT="$(./svc.sh status 2>&1 || true)"
echo "$STATUS_OUT"

if ! echo "$STATUS_OUT" | grep -qi "Started"; then
  echo "[watchdog] service not started; restarting"
  ./svc.sh stop || true
  sleep 2
  ./svc.sh start
  sleep 3
  ./svc.sh status || true
fi

LATEST_LOG="$(ls -t _diag/Runner_*.log 2>/dev/null | head -n 1 || true)"
if [ -n "$LATEST_LOG" ]; then
  echo "[watchdog] latest_log=${LATEST_LOG}"
  BROKER_ERRS="$(tail -n 1000 "$LATEST_LOG" | grep -c "BrokerServer" || true)"
  echo "[watchdog] broker_errs_last_1000=${BROKER_ERRS}"
  if [ "${BROKER_ERRS:-0}" -ge "$MAX_BROKER_ERRORS_WINDOW" ]; then
    echo "[watchdog] high broker error count detected; proactive runner restart"
    ./svc.sh stop || true
    sleep 3
    ./svc.sh start
    sleep 3
    ./svc.sh status || true
  fi
else
  echo "[watchdog] no Runner_*.log found yet"
fi

echo "[watchdog] done"
