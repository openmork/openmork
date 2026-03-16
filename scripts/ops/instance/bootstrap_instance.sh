#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_instance_common.sh
source "$SCRIPT_DIR/_instance_common.sh"

ENV_FILE="${1:-}"
load_instance_env "$ENV_FILE"
ensure_parent_dirs

[[ -d "$OPENMORK_HOME" ]] || mkdir -p "$OPENMORK_HOME"
[[ -d "$OPENMORK_REPO" ]] || {
  echo "ERROR: OPENMORK_REPO does not exist: $OPENMORK_REPO" >&2
  exit 66
}
[[ -f "$OPENMORK_ENV_FILE" ]] || {
  echo "ERROR: OPENMORK_ENV_FILE does not exist: $OPENMORK_ENV_FILE" >&2
  exit 66
}

: >"$LOG_FILE"
log_msg "bootstrap ok"
log_msg "env_file=$ENV_FILE"
log_msg "repo=$OPENMORK_REPO"
log_msg "pid_file=$PID_FILE"
log_msg "lock_file=$INSTANCE_LOCK_FILE"
