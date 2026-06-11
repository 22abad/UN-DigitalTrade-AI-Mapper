#!/bin/bash
# Restore and Rollback script for RDTII Database
# Prompts the user with a menu of available backups to select from.

BACKUP_DIR="$(dirname "$0")/../backups"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "❌ Error: No backups directory found at $BACKUP_DIR"
  exit 1
fi

# List available backups
echo "=== Available Database Backups ==="
backups=($(ls -t "$BACKUP_DIR"/rdtii_db_backup_*.sql 2>/dev/null))

if [ ${#backups[@]} -eq 0 ]; then
  echo "❌ No backup files found in $BACKUP_DIR"
  exit 1
fi

for i in "${!backups[@]}"; do
  echo "[$i] $(basename "${backups[$i]}")"
done

echo ""
# Ask user to choose which backup to restore
read -p "Select backup to restore [0-$((${#backups[@]} - 1))]: " choice

if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -ge "${#backups[@]}" ]; then
  echo "❌ Invalid choice!"
  exit 1
fi

SELECTED_BACKUP="${backups[$choice]}"

echo ""
echo "⚠️  WARNING: This will completely overwrite the current database with the backup from $(basename "$SELECTED_BACKUP")!"
read -p "Are you sure you want to proceed? (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "❌ Operation cancelled."
  exit 0
fi

echo "=== Restoring Database from $(basename "$SELECTED_BACKUP") ==="

echo "1. Terminating active database connections..."
docker exec rdtii-postgres psql -U rdtii_user -d postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'rdtii' AND pid <> pg_backend_pid();" > /dev/null

echo "2. Re-creating database 'rdtii'..."
docker exec rdtii-postgres psql -U rdtii_user -d postgres -c "DROP DATABASE IF EXISTS rdtii;" > /dev/null
docker exec rdtii-postgres psql -U rdtii_user -d postgres -c "CREATE DATABASE rdtii;" > /dev/null

echo "3. Importing backup SQL dump..."
docker exec -i rdtii-postgres psql -U rdtii_user -d rdtii < "$SELECTED_BACKUP" > /dev/null

if [ $? -eq 0 ]; then
  echo "✅ Database successfully restored to $(basename "$SELECTED_BACKUP")!"
else
  echo "❌ Error: Restore failed!"
  exit 1
fi
