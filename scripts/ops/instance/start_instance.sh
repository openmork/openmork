#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_instance_common.sh
source "$SCRIPT_DIR/_instance_common.sh"

ENV_FILE="${1:-}"
load_instance_env "$ENV_FILE"
ensure_parent_dirs

if [[ -f "$OPENMORK_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$OPENMORK_ENV_FILE"
  set +a
fi

if existing_pid="$(read_pid_file 2>/dev/null)" && is_pid_running "$existing_pid"; then
  log_msg "start skipped: already running pid=$existing_pid"
  exit 0
fi

cmd="$(start_command)"
log_msg "starting instance with command: $cmd"
(
  cd "$OPENMORK_REPO"
  nohup bash -lc "$cmd" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
)

new_pid="$(read_pid_file)"
for _ in $(seq 1 "$STARTUP_WAIT_SECONDS"); do
  if is_pid_running "$new_pid"; then
    log_msg "start ok pid=$new_pid"
    exit 0
  fi
  sleep 1
done

log_msg "start failed: process did not stay alive (pid=$new_pid)"
rm -f "$PID_FILE"
exit 1
