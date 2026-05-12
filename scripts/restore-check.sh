#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

POSTGRES_USER="${POSTGRES_USER:-kinframe}"
POSTGRES_DB="${POSTGRES_DB:-kinframe}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}"
MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}"

backup_dir="${1:-}"
if [[ -z "$backup_dir" ]]; then
  backup_output="$(scripts/backup.sh)"
  printf '%s\n' "$backup_output"
  backup_dir="$(printf '%s\n' "$backup_output" | awk -F': ' '/Backup completed:/ {print $2}' | tail -n 1)"
  if [[ -z "$backup_dir" ]]; then
    echo "Could not determine generated backup directory." >&2
    exit 1
  fi
fi

manifest="$backup_dir/manifest.json"
postgres_dump="$backup_dir/postgres/postgres.dump"
bucket_dir="$backup_dir/minio/$MINIO_BUCKET"

if [[ ! -s "$manifest" ]]; then
  echo "Backup manifest is missing: $manifest" >&2
  exit 1
fi
if [[ ! -s "$postgres_dump" ]]; then
  echo "PostgreSQL dump is missing: $postgres_dump" >&2
  exit 1
fi
if [[ ! -d "$bucket_dir" ]]; then
  echo "MinIO bucket backup directory is missing: $bucket_dir" >&2
  exit 1
fi

stamp="$(date +%Y%m%d%H%M%S)-$$"
pg_name="kinframe-restore-check-postgres-$stamp"
minio_name="kinframe-restore-check-minio-$stamp"

cleanup() {
  docker rm -f "$pg_name" "$minio_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

expected_users="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["postgres"]["user_count"])' "$manifest")"
expected_photos="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["postgres"]["photo_count"])' "$manifest")"
expected_slide_designs="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["postgres"].get("slide_design_count", 0))' "$manifest")"
expected_objects="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["minio"]["object_count"])' "$manifest")"

echo "Starting isolated PostgreSQL restore check..."
docker run -d --name "$pg_name" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  postgres:16 >/dev/null

for _ in $(seq 1 30); do
  if docker exec "$pg_name" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$pg_name" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null
docker cp "$postgres_dump" "$pg_name:/tmp/postgres.dump"
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$pg_name" \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges /tmp/postgres.dump

restored_users="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$pg_name" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from users;"
)"
restored_photos="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$pg_name" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from photos;"
)"
restored_slide_designs_exists="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$pg_name" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select to_regclass('public.slide_designs') is not null;"
)"
if [[ "$restored_slide_designs_exists" == "t" ]]; then
  restored_slide_designs="$(
    docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$pg_name" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from slide_designs;"
  )"
else
  restored_slide_designs="0"
fi

if [[ "$restored_users" != "$expected_users" || "$restored_photos" != "$expected_photos" || "$restored_slide_designs" != "$expected_slide_designs" ]]; then
  echo "PostgreSQL restore-check count mismatch." >&2
  echo "Expected users/photos/slide_designs: $expected_users/$expected_photos/$expected_slide_designs" >&2
  echo "Restored users/photos/slide_designs: $restored_users/$restored_photos/$restored_slide_designs" >&2
  exit 1
fi

echo "Starting isolated MinIO restore check..."
docker run -d --name "$minio_name" \
  -e MINIO_ROOT_USER="$MINIO_ACCESS_KEY" \
  -e MINIO_ROOT_PASSWORD="$MINIO_SECRET_KEY" \
  minio/minio:latest server /data --console-address ":9001" >/dev/null

for _ in $(seq 1 30); do
  if docker exec "$minio_name" mc alias set local http://127.0.0.1:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$minio_name" mc alias set local http://127.0.0.1:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null
docker exec "$minio_name" mc mb --ignore-existing "local/$MINIO_BUCKET" >/dev/null
docker exec "$minio_name" mkdir -p "/tmp/restore/$MINIO_BUCKET"
docker cp "$bucket_dir/." "$minio_name:/tmp/restore/$MINIO_BUCKET/"
docker exec "$minio_name" mc mirror --overwrite "/tmp/restore/$MINIO_BUCKET" "local/$MINIO_BUCKET" >/dev/null

restored_objects="$(
  docker exec "$minio_name" sh -c "mc find 'local/$MINIO_BUCKET' | wc -l | tr -d ' '"
)"

if [[ "$restored_objects" != "$expected_objects" ]]; then
  echo "MinIO restore-check object count mismatch." >&2
  echo "Expected objects: $expected_objects" >&2
  echo "Restored objects: $restored_objects" >&2
  exit 1
fi

echo "Restore check passed: users=$restored_users photos=$restored_photos slide_designs=$restored_slide_designs objects=$restored_objects"
