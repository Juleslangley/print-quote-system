#!/usr/bin/env bash
# Backup the quote database to a dated file.
# Run from project root. With Docker: ./scripts/backup-db.sh
# Saves to ./backups/quote_YYYYMMDD_HHMM.sql (create backups/ if needed).

set -e
BACKUP_DIR="$(dirname "$0")/../backups"
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/quote_$(date +%Y%m%d_%H%M).sql"

if docker compose exec db pg_dump -U quote quote > "$FILE" 2>/dev/null; then
  echo "Backup saved: $FILE"
else
  echo "Docker backup failed. If Postgres runs locally, try:"
  echo "  pg_dump -U quote quote > $FILE"
fi
