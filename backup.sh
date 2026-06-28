#!/bin/bash
# HongShing — nightly DB backup (local + off-box to S3). Cron: 0 2 * * * /opt/hongshing/backup.sh
set -uo pipefail

BACKUP_DIR="/opt/hongshing/backups"
RETENTION_DAYS=30
S3_BUCKET="${BACKUP_S3_BUCKET:-hongshing-db-backups-274016496814}"
# Compose project is "hongshing" → db container is hongshing-db-1.
DB_CONTAINER="${DB_CONTAINER:-hongshing-db-1}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/hongshing-$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

if ! docker exec "$DB_CONTAINER" pg_dump -U hongshing hongshing | gzip > "$BACKUP_FILE"; then
  echo "$(date): ERROR pg_dump failed (container=$DB_CONTAINER)" >&2
  exit 1
fi

if [ -n "$S3_BUCKET" ]; then
  if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$(basename "$BACKUP_FILE")" --region us-east-1; then
    echo "$(date): Uploaded to s3://$S3_BUCKET/$(basename "$BACKUP_FILE")"
  else
    echo "$(date): WARNING off-box S3 upload failed — local copy kept" >&2
  fi
fi

find "$BACKUP_DIR" -name "hongshing-*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "$(date): Backup saved to $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
