#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_instance_common.sh
source "$SCRIPT_DIR/_instance_common.sh"

ENV_FILE="${1:-}"
load_instance_env "$ENV_FILE"
ensure_parent_dirs

exec 9>"$INSTANCE_LOCK_FILE"
if ! flock -n 9; then
  echo "ERROR: restart lock active for instance '$INSTANCE_NAME' ($INSTANCE_LOCK_FILE)" >&2
  exit 75
fi

log_msg "restart start (scoped)"
"$SCRIPT_DIR/stop_instance.sh" "$ENV_FILE"
"$SCRIPT_DIR/start_instance.sh" "$ENV_FILE"
log_msg "restart done"
