#!/bin/bash
# Backup script for RDTII Database
# Keeps the last 10 backups automatically.

# Get backups directory relative to script
BACKUP_DIR="$(dirname "$0")/../backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/rdtii_db_backup_$TIMESTAMP.sql"

echo "=== Starting PostgreSQL Database Backup ==="
echo "Target backup file: $BACKUP_FILE"

# Run pg_dump inside the docker container
docker exec rdtii-postgres pg_dump -U rdtii_user -d rdtii > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
  echo "✅ Backup successfully created!"
  echo "File location: $BACKUP_FILE"
  # Keep only the last 10 backups to save space
  ls -t "$BACKUP_DIR"/rdtii_db_backup_*.sql | tail -n +11 | xargs rm -f 2>/dev/null
else
  echo "❌ Error: Backup failed! Please make sure docker container 'rdtii-postgres' is running."
  exit 1
fi
