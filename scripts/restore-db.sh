#!/usr/bin/env bash
# Restore the quote database from a backup file.
# Usage: ./scripts/restore-db.sh [path/to/backup.sql]
# Run from project root. DB container must be running.

set -e
FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "Usage: $0 <backup.sql>"
  echo "Example: $0 backups/quote_20250208_1200.sql"
  exit 1
fi

docker compose exec -T db psql -U quote quote < "$FILE"
echo "Restored from $FILE"
