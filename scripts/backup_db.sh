#!/bin/sh
# Production backup script (PR 14, docs/31-backups-and-dr.md).
#
# Run from a sidecar container or host cron. Set:
#   DATABASE_URL              postgres://user:pass@host:5432/db
#   BACKUP_DIR                /var/orbiteus/backups (or S3-compatible mount)
#   BACKUP_RETENTION_DAYS     default 30
#
# pg_dump → gzip → atomically rename → expire old files.
set -eu

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${BACKUP_DIR:=/var/orbiteus/backups}"
: "${BACKUP_RETENTION_DAYS:=30}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
TARGET="$BACKUP_DIR/orbiteus_$TIMESTAMP.sql.gz"
TMP="$TARGET.partial"

echo "[backup] dumping → $TMP"
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip --best > "$TMP"
mv "$TMP" "$TARGET"
echo "[backup] done: $TARGET ($(du -h "$TARGET" | cut -f1))"

echo "[backup] expiring files older than $BACKUP_RETENTION_DAYS days"
find "$BACKUP_DIR" -name 'orbiteus_*.sql.gz' -type f -mtime "+$BACKUP_RETENTION_DAYS" -delete || true
