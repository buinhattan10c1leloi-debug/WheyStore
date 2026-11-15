#!/usr/bin/env sh
set -eu
mkdir -p backups
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
if [ "${DB_ENGINE:-sqlite}" = "postgresql" ]; then
  pg_dump -h "${DB_HOST:-db}" -U "${DB_USER:-wheystore}" "${DB_NAME:-wheystore}" > "backups/wheystore_${TIMESTAMP}.sql"
else
  cp db.sqlite3 "backups/db_${TIMESTAMP}.sqlite3"
fi
echo "Backup created at backups/ (${TIMESTAMP})"
