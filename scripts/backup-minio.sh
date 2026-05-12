#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

backup_dir="${1:-}"
if [[ -z "$backup_dir" ]]; then
  echo "Usage: scripts/backup-minio.sh <backup-dir>" >&2
  exit 2
fi

MINIO_CONTAINER="${MINIO_CONTAINER:-kinframe-minio}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}"
MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}"

minio_dir="$backup_dir/minio"
bucket_dir="$minio_dir/$MINIO_BUCKET"
counts_file="$minio_dir/counts.env"
container_tmp="/tmp/kinframe-minio-backup-$(date +%s)-$$"

mkdir -p "$minio_dir"
if [[ -e "$bucket_dir" ]]; then
  echo "MinIO backup destination already exists: $bucket_dir" >&2
  exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$MINIO_CONTAINER" 2>/dev/null || true)" != "true" ]]; then
  echo "MinIO container is not running: $MINIO_CONTAINER" >&2
  exit 1
fi

cleanup() {
  docker exec "$MINIO_CONTAINER" rm -rf "$container_tmp" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker exec "$MINIO_CONTAINER" sh -c "rm -rf '$container_tmp' && mkdir -p '$container_tmp'"
docker exec "$MINIO_CONTAINER" mc alias set local http://127.0.0.1:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null
docker exec "$MINIO_CONTAINER" mc mirror --overwrite "local/$MINIO_BUCKET" "$container_tmp/$MINIO_BUCKET" >/dev/null
docker cp "$MINIO_CONTAINER:$container_tmp/$MINIO_BUCKET" "$minio_dir/"

object_count="$(find "$bucket_dir" -type f | wc -l | tr -d ' ')"
total_bytes="$(du -sb "$bucket_dir" | awk '{print $1}')"

{
  printf 'MINIO_BUCKET=%s\n' "$MINIO_BUCKET"
  printf 'MINIO_OBJECT_COUNT=%s\n' "$object_count"
  printf 'MINIO_TOTAL_BYTES=%s\n' "$total_bytes"
  printf 'MINIO_BACKUP_DIR=%s\n' "minio/$MINIO_BUCKET"
} > "$counts_file"

printf 'MinIO backup written: %s\n' "$bucket_dir"
