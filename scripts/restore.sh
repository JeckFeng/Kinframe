#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

backup_dir="${1:-}"
if [[ -z "$backup_dir" ]]; then
  echo "Usage: RESTORE_CONFIRM=YES scripts/restore.sh <backup-dir>" >&2
  exit 2
fi

if [[ ! -s "$backup_dir/manifest.json" ]]; then
  echo "Backup manifest is missing: $backup_dir/manifest.json" >&2
  exit 1
fi

if [[ "${RESTORE_CONFIRM:-}" != "YES" ]]; then
  echo "Refusing to restore without RESTORE_CONFIRM=YES." >&2
  echo "This operation restores PostgreSQL and MinIO data into the running local services." >&2
  echo "Configuration files are backed up under $backup_dir/config but are not copied automatically." >&2
  exit 2
fi

scripts/restore-postgres.sh "$backup_dir"
scripts/restore-minio.sh "$backup_dir"

printf 'Restore completed from: %s\n' "$backup_dir"
printf 'Config backup is available at: %s\n' "$backup_dir/config"
