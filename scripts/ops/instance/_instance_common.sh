#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  }
}

usage_env_required() {
  echo "Usage: $0 <path/to/instance.env>" >&2
  exit 64
}

load_instance_env() {
  local env_file="${1:-}"
  [[ -n "$env_file" ]] || usage_env_required
  [[ -f "$env_file" ]] || {
    echo "ERROR: env file does not exist: $env_file" >&2
    exit 66
  }

  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a

  : "${INSTANCE_NAME:?INSTANCE_NAME is required in env file}"
  : "${OPENMORK_HOME:?OPENMORK_HOME is required in env file}"
  : "${OPENMORK_REPO:?OPENMORK_REPO is required in env file}"
  : "${OPENMORK_ENV_FILE:?OPENMORK_ENV_FILE is required in env file}"
  : "${PID_FILE:?PID_FILE is required in env file}"
  : "${LOG_FILE:?LOG_FILE is required in env file}"
  : "${MODEL:?MODEL is required in env file}"

  INSTANCE_LOCK_FILE="${INSTANCE_LOCK_FILE:-${PID_FILE}.lock}"
  HEALTH_URL="${HEALTH_URL:-}"
  STARTUP_WAIT_SECONDS="${STARTUP_WAIT_SECONDS:-20}"
  STOP_WAIT_SECONDS="${STOP_WAIT_SECONDS:-20}"
  OPENMORK_BIN="${OPENMORK_BIN:-}"
  OPENMORK_START_CMD="${OPENMORK_START_CMD:-}"
}

ensure_parent_dirs() {
  mkdir -p "$(dirname "$PID_FILE")"
  mkdir -p "$(dirname "$LOG_FILE")"
  mkdir -p "$(dirname "$INSTANCE_LOCK_FILE")"
}

log_msg() {
  local msg="$1"
  printf '%s [%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$INSTANCE_NAME" "$msg" | tee -a "$LOG_FILE"
}

is_pid_running() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

read_pid_file() {
  [[ -f "$PID_FILE" ]] || return 1
  tr -d '[:space:]' < "$PID_FILE"
}

start_command() {
  if [[ -n "$OPENMORK_START_CMD" ]]; then
    echo "$OPENMORK_START_CMD"
    return 0
  fi

  if [[ -n "$OPENMORK_BIN" ]]; then
    echo "\"$OPENMORK_BIN\" run"
    return 0
  fi

  if [[ -x "$OPENMORK_REPO/openmork" ]]; then
    echo "\"$OPENMORK_REPO/openmork\" run"
  elif [[ -x "$OPENMORK_REPO/.venv/bin/openmork" ]]; then
    echo "\"$OPENMORK_REPO/.venv/bin/openmork\" run"
  elif [[ -x "$OPENMORK_REPO/.venv/bin/python" ]]; then
    echo "\"$OPENMORK_REPO/.venv/bin/python\" -m openmork_cli.main run"
  else
    echo "python3 -m openmork_cli.main run"
  fi
}
