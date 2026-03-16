#!/usr/bin/env bash
set -euo pipefail

SRC_REPO="/home/wosmim/projects/openmork"
PROD_REPO="/home/wosmim/apps/openmork-prod"
PROD_ENV="/home/wosmim/.config/openmork/openmork-prod.env"
LOG="/home/wosmim/.openmork-prod/deploy.log"

REF="${1:-main}"
mkdir -p /home/wosmim/.openmork-prod

echo "[$(date -Is)] Deploy start ref=${REF}" | tee -a "$LOG"

git -C "$SRC_REPO" fetch --all --prune >/dev/null 2>&1 || true
if [ ! -d "$PROD_REPO/.git" ]; then
  git clone "$SRC_REPO" "$PROD_REPO"
fi

git -C "$PROD_REPO" fetch --all --prune
git -C "$PROD_REPO" checkout "$REF"
git -C "$PROD_REPO" reset --hard "$REF"

# optional restart hook (safe no-op if no process running)
pkill -f "openmork_cli.main gateway run" 2>/dev/null || true

echo "[$(date -Is)] Deploy done ref=${REF}" | tee -a "$LOG"
