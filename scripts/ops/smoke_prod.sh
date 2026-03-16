#!/usr/bin/env bash
set -euo pipefail

PROD_HOME="/home/wosmim/.openmork-prod"
PROD_ENV="/home/wosmim/.config/openmork/openmork-prod.env"
PROD_REPO="/home/wosmim/apps/openmork-prod"

[ -d "$PROD_REPO/.git" ] || { echo "FAIL: missing prod repo"; exit 1; }
[ -f "$PROD_ENV" ] || { echo "FAIL: missing prod env"; exit 1; }
[ -d "$PROD_HOME" ] || { echo "FAIL: missing prod home"; exit 1; }

echo "OK: prod repo/env/home present"
git -C "$PROD_REPO" rev-parse --short HEAD
