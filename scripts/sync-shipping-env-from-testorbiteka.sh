#!/usr/bin/env bash
# Sync carrier env vars from Testorbiteka crm-engine/.env into orbiteus/.env (VM or local).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TB_ENV="${TESTORBITEKA_ENV:-/home/marcins/apps/testorbiteka/crm-engine/.env}"
OB_ENV="${ORBITEUS_ENV:-$ROOT/.env}"

if [[ ! -f "$TB_ENV" ]]; then
  echo "Missing Testorbiteka .env: $TB_ENV" >&2
  exit 1
fi

cp "$OB_ENV" "${OB_ENV}.bak.sync-shipping" 2>/dev/null || true
touch "$OB_ENV"

grep -vE '^(SHIPPING_|DPD_|DSV_|GEODIS_|IFS_WEBHOOK|IFS_RELAY|LOGISTICS_|CARRIER_)' "$OB_ENV" > "${OB_ENV}.tmp" || true
mv "${OB_ENV}.tmp" "$OB_ENV"

{
  echo "# --- shipping carriers synced from testorbiteka ---"
  grep -E '^(SHIPPING_|DPD_|DSV_|GEODIS_|IFS_WEBHOOK|IFS_RELAY|LOGISTICS_|CARRIER_)' "$TB_ENV" || true
  echo "# --- end shipping carriers ---"
} >> "$OB_ENV"

echo "Synced carrier vars into $OB_ENV"
grep -E '^(SHIPPING_|DPD_|DSV_|GEODIS_)' "$OB_ENV" | cut -d= -f1 | sort -u
