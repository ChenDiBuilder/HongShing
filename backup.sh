#!/bin/bash
# Restaurant clone — nightly DB backup (local + off-box to S3). Cron: 0 2 * * * /opt/<slug>/backup.sh
# Slug-parameterized (PRD-11 / SCRUM-53): the script lives at /opt/<slug>/backup.sh,
# so the slug is the basename of its own directory. The compose project name = that
# app-dir basename, so the db container is <slug>-db-1. Both can be overridden by env.
set -uo pipefail

SLUG="${SLUG:-$(basename "$(cd "$(dirname "$0")" && pwd)")}"
BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)/backups"
RETENTION_DAYS=30
S3_BUCKET="${BACKUP_S3_BUCKET:-$SLUG-db-backups-274016496814}"
# Compose project is "<slug>" → db container is <slug>-db-1.
DB_CONTAINER="${DB_CONTAINER:-$SLUG-db-1}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/$SLUG-$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# Postgres role + database are both named "hongshing" in docker-compose.prod.yml
# (the template's fixed POSTGRES_USER/POSTGRES_DB); override via PGUSER/PGDATABASE.
PGUSER="${PGUSER:-hongshing}"
PGDATABASE="${PGDATABASE:-hongshing}"

if ! docker exec "$DB_CONTAINER" pg_dump -U "$PGUSER" "$PGDATABASE" | gzip > "$BACKUP_FILE"; then
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

find "$BACKUP_DIR" -name "$SLUG-*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "$(date): Backup saved to $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
