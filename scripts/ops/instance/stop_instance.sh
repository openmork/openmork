#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_instance_common.sh
source "$SCRIPT_DIR/_instance_common.sh"

ENV_FILE="${1:-}"
load_instance_env "$ENV_FILE"
ensure_parent_dirs

if ! pid="$(read_pid_file 2>/dev/null)"; then
  log_msg "stop skipped: pid file not found"
  exit 0
fi

if ! is_pid_running "$pid"; then
  log_msg "stop cleanup: stale pid file pid=$pid"
  rm -f "$PID_FILE"
  exit 0
fi

log_msg "stopping instance pid=$pid"
kill "$pid"
for _ in $(seq 1 "$STOP_WAIT_SECONDS"); do
  if ! is_pid_running "$pid"; then
    rm -f "$PID_FILE"
    log_msg "stop ok pid=$pid"
    exit 0
  fi
  sleep 1
done

log_msg "stop timeout: sending SIGKILL to pid=$pid"
kill -9 "$pid"
rm -f "$PID_FILE"
log_msg "stop forced pid=$pid"
