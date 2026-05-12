#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

backup_dir="${1:-}"
if [[ -z "$backup_dir" ]]; then
  echo "Usage: RESTORE_CONFIRM=YES scripts/restore-postgres.sh <backup-dir>" >&2
  exit 2
fi

if [[ "${RESTORE_CONFIRM:-}" != "YES" ]]; then
  echo "Refusing to restore PostgreSQL without RESTORE_CONFIRM=YES." >&2
  echo "This operation overwrites database tables in the target PostgreSQL service." >&2
  exit 2
fi

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-kinframe-postgres}"
POSTGRES_USER="${POSTGRES_USER:-kinframe}"
POSTGRES_DB="${POSTGRES_DB:-kinframe}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"
dump_file="$backup_dir/postgres/postgres.dump"

if [[ ! -s "$dump_file" ]]; then
  echo "PostgreSQL dump is missing or empty: $dump_file" >&2
  exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$POSTGRES_CONTAINER" 2>/dev/null || true)" != "true" ]]; then
  echo "PostgreSQL container is not running: $POSTGRES_CONTAINER" >&2
  exit 1
fi

cat "$dump_file" | docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges

printf 'PostgreSQL restored from: %s\n' "$dump_file"
