#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${HOME}/.openmork"
LOG_FILE="${LOG_DIR}/openmork-restart.log"
mkdir -p "${LOG_DIR}"

TIMEOUT_SECONDS="${OPENMORK_RESTART_TIMEOUT:-60}"
PING_TIMEOUT_SECONDS="${OPENMORK_PING_TIMEOUT:-20}"

log() {
  printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*" | tee -a "$LOG_FILE"
}

run_openmork() {
  if [[ -x "./openmork" ]]; then
    ./openmork "$@"
  elif [[ -x "./.venv/bin/openmork" ]]; then
    ./.venv/bin/openmork "$@"
  elif command -v openmork >/dev/null 2>&1; then
    openmork "$@"
  elif [[ -x "./.venv/bin/python" ]]; then
    ./.venv/bin/python -m openmork_cli.main "$@"
  else
    python3 -m openmork_cli.main "$@"
  fi
}

is_active_service() {
  if command -v systemctl >/dev/null 2>&1; then
    if systemctl --user is-active openmork-gateway >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

get_gateway_pid() {
  python3 - <<'PY'
from gateway.status import get_running_pid
pid = get_running_pid()
print(pid or "")
PY
}

bot_ping_check() {
  python3 - <<'PY'
import json
import os
import sys
import urllib.request

checks = []

def req(url, headers=None, timeout=10):
    r = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        code = getattr(resp, 'status', 200)
        body = resp.read(512).decode('utf-8', errors='ignore')
    return code, body

ok = False

telegram = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
if telegram:
    try:
        code, body = req(f"https://api.telegram.org/bot{telegram}/getMe")
        t_ok = code == 200 and '"ok":true' in body.replace(' ', '').lower()
        checks.append({'platform': 'telegram', 'ok': t_ok, 'status': code})
        ok = ok or t_ok
    except Exception as e:
        checks.append({'platform': 'telegram', 'ok': False, 'error': str(e)})

discord = os.getenv('DISCORD_BOT_TOKEN', '').strip()
if discord:
    try:
        code, _ = req('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bot {discord}'})
        d_ok = code == 200
        checks.append({'platform': 'discord', 'ok': d_ok, 'status': code})
        ok = ok or d_ok
    except Exception as e:
        checks.append({'platform': 'discord', 'ok': False, 'error': str(e)})

slack = os.getenv('SLACK_BOT_TOKEN', '').strip()
if slack:
    try:
        code, body = req('https://slack.com/api/auth.test', headers={'Authorization': f'Bearer {slack}'})
        s_ok = code == 200 and '"ok":true' in body.replace(' ', '').lower()
        checks.append({'platform': 'slack', 'ok': s_ok, 'status': code})
        ok = ok or s_ok
    except Exception as e:
        checks.append({'platform': 'slack', 'ok': False, 'error': str(e)})

if not checks:
    print(json.dumps({'ok': False, 'error': 'No supported bot token configured', 'checks': checks}))
    sys.exit(2)

print(json.dumps({'ok': ok, 'checks': checks}))
sys.exit(0 if ok else 1)
PY
}

log "=== restart_gateway_safe start ==="
old_pid="$(get_gateway_pid | tr -d '\n')"
if [[ -n "$old_pid" ]]; then
  log "Detected running gateway pid=${old_pid}"
else
  log "No running gateway PID detected before restart"
fi

was_active=0
if is_active_service; then
  was_active=1
  log "Gateway user service is active"
else
  log "Gateway user service is not active (manual mode or stopped)"
fi

if run_openmork gateway restart >>"$LOG_FILE" 2>&1; then
  log "Restart command completed"
else
  log "Restart command failed, attempting rollback"
  if [[ "$was_active" -eq 1 ]]; then
    run_openmork gateway start >>"$LOG_FILE" 2>&1 || true
  fi
  exit 1
fi

start_ts=$(date +%s)
healthy_pid=""
while true; do
  current_pid="$(get_gateway_pid | tr -d '\n')"
  if [[ -n "$current_pid" ]]; then
    healthy_pid="$current_pid"
    break
  fi
  now_ts=$(date +%s)
  if (( now_ts - start_ts > TIMEOUT_SECONDS )); then
    log "Timeout waiting for gateway process after restart"
    break
  fi
  sleep 2
done

if [[ -z "$healthy_pid" ]]; then
  log "Healthcheck failed: no gateway process detected"
  if [[ "$was_active" -eq 1 ]]; then
    log "Rollback: attempting to start gateway service"
    run_openmork gateway start >>"$LOG_FILE" 2>&1 || true
  fi
  exit 1
fi

log "Gateway process detected pid=${healthy_pid}"

if timeout "$PING_TIMEOUT_SECONDS" bot_ping_check >>"$LOG_FILE" 2>&1; then
  log "Bot ping healthcheck passed"
  log "=== restart_gateway_safe success ==="
  exit 0
else
  log "Bot ping healthcheck failed, attempting rollback"
  if [[ "$was_active" -eq 1 ]]; then
    run_openmork gateway restart >>"$LOG_FILE" 2>&1 || run_openmork gateway start >>"$LOG_FILE" 2>&1 || true
  fi
  log "=== restart_gateway_safe failed ==="
  exit 1
fi
