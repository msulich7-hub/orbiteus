#!/bin/sh
# Restore drill — restore the latest backup into a throwaway DB and run a
# smoke pg_dump --schema-only diff. Exits non-zero on schema drift.
#
# Usage:
#   DATABASE_URL=...                # source of truth
#   DRILL_DATABASE_URL=...          # disposable target
#   BACKUP_DIR=/var/orbiteus/backups
set -eu

: "${BACKUP_DIR:=/var/orbiteus/backups}"
: "${DATABASE_URL:?DATABASE_URL must be set (source schema)}"
: "${DRILL_DATABASE_URL:?DRILL_DATABASE_URL must be set (target)}"

LATEST=$(ls -1t "$BACKUP_DIR"/orbiteus_*.sql.gz 2>/dev/null | head -n 1 || true)
if [ -z "$LATEST" ]; then
  echo "[drill] no backup found in $BACKUP_DIR" >&2
  exit 2
fi
echo "[drill] using backup: $LATEST"

echo "[drill] restoring into $DRILL_DATABASE_URL"
gunzip -c "$LATEST" | psql "$DRILL_DATABASE_URL" >/dev/null

echo "[drill] schema diff vs source"
SRC=$(mktemp); DST=$(mktemp)
pg_dump --schema-only --no-owner --no-privileges "$DATABASE_URL" > "$SRC"
pg_dump --schema-only --no-owner --no-privileges "$DRILL_DATABASE_URL" > "$DST"

if diff -u "$SRC" "$DST" >/dev/null; then
  echo "[drill] OK — schemas match"
  rc=0
else
  echo "[drill] FAILED — schema drift detected:" >&2
  diff -u "$SRC" "$DST" | head -100
  rc=1
fi

rm -f "$SRC" "$DST"
exit $rc
