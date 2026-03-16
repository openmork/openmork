#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_instance_common.sh
source "$SCRIPT_DIR/_instance_common.sh"

ENV_FILE="${1:-}"
load_instance_env "$ENV_FILE"
ensure_parent_dirs

if ! pid="$(read_pid_file 2>/dev/null)"; then
  log_msg "health fail: missing pid file"
  exit 1
fi

if ! is_pid_running "$pid"; then
  log_msg "health fail: pid not running pid=$pid"
  exit 1
fi

if [[ -n "$HEALTH_URL" ]]; then
  require_cmd curl
  if curl --silent --show-error --fail --max-time 5 "$HEALTH_URL" >/dev/null; then
    log_msg "health ok: pid=$pid url=$HEALTH_URL"
    exit 0
  else
    log_msg "health fail: pid alive but url check failed ($HEALTH_URL)"
    exit 1
  fi
fi

log_msg "health ok: pid=$pid"
