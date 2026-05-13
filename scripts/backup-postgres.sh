#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

backup_dir="${1:-}"
if [[ -z "$backup_dir" ]]; then
  echo "Usage: scripts/backup-postgres.sh <backup-dir>" >&2
  exit 2
fi

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-kinframe-postgres}"
POSTGRES_USER="${POSTGRES_USER:-kinframe}"
POSTGRES_DB="${POSTGRES_DB:-kinframe}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"

postgres_dir="$backup_dir/postgres"
dump_file="$postgres_dir/postgres.dump"
counts_file="$postgres_dir/counts.env"

mkdir -p "$postgres_dir"

if [[ "$(docker inspect -f '{{.State.Running}}' "$POSTGRES_CONTAINER" 2>/dev/null || true)" != "true" ]]; then
  echo "PostgreSQL container is not running: $POSTGRES_CONTAINER" >&2
  exit 1
fi

docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$dump_file"

if [[ ! -s "$dump_file" ]]; then
  echo "PostgreSQL backup file is missing or empty: $dump_file" >&2
  exit 1
fi

user_count="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from users;"
)"
photo_count="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from photos;"
)"
slide_design_exists="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select to_regclass('public.slide_designs') is not null;"
)"
if [[ "$slide_design_exists" == "t" ]]; then
  slide_design_count="$(
    docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from slide_designs;"
  )"
else
  slide_design_count="0"
fi

categories_exists="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select to_regclass('public.categories') is not null;"
)"
if [[ "$categories_exists" == "t" ]]; then
  category_count="$(
    docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from categories;"
  )"
else
  category_count="0"
fi

audit_logs_exists="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select to_regclass('public.audit_logs') is not null;"
)"
if [[ "$audit_logs_exists" == "t" ]]; then
  audit_log_count="$(
    docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from audit_logs;"
  )"
else
  audit_log_count="0"
fi

{
  printf 'POSTGRES_USER_COUNT=%s\n' "$user_count"
  printf 'POSTGRES_PHOTO_COUNT=%s\n' "$photo_count"
  printf 'POSTGRES_SLIDE_DESIGN_COUNT=%s\n' "$slide_design_count"
  printf 'POSTGRES_CATEGORY_COUNT=%s\n' "$category_count"
  printf 'POSTGRES_AUDIT_LOG_COUNT=%s\n' "$audit_log_count"
  printf 'POSTGRES_DUMP_FILE=%s\n' "postgres/postgres.dump"
} > "$counts_file"

printf 'PostgreSQL backup written: %s\n' "$dump_file"
