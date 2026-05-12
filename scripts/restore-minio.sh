#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

backup_dir="${1:-}"
if [[ -z "$backup_dir" ]]; then
  echo "Usage: RESTORE_CONFIRM=YES scripts/restore-minio.sh <backup-dir>" >&2
  exit 2
fi

if [[ "${RESTORE_CONFIRM:-}" != "YES" ]]; then
  echo "Refusing to restore MinIO without RESTORE_CONFIRM=YES." >&2
  echo "This operation overwrites objects with matching names in the target MinIO bucket." >&2
  exit 2
fi

MINIO_CONTAINER="${MINIO_CONTAINER:-kinframe-minio}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}"
MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}"
bucket_dir="$backup_dir/minio/$MINIO_BUCKET"
container_tmp="/tmp/kinframe-minio-restore-$(date +%s)-$$"

if [[ ! -d "$bucket_dir" ]]; then
  echo "MinIO bucket backup directory is missing: $bucket_dir" >&2
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

docker exec "$MINIO_CONTAINER" sh -c "rm -rf '$container_tmp' && mkdir -p '$container_tmp/$MINIO_BUCKET'"
docker cp "$bucket_dir/." "$MINIO_CONTAINER:$container_tmp/$MINIO_BUCKET/"
docker exec "$MINIO_CONTAINER" mc alias set local http://127.0.0.1:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null
docker exec "$MINIO_CONTAINER" mc mb --ignore-existing "local/$MINIO_BUCKET" >/dev/null

mirror_args=(--overwrite)
if [[ "${RESTORE_REMOVE_EXTRA:-0}" == "1" ]]; then
  mirror_args+=(--remove)
fi

docker exec "$MINIO_CONTAINER" mc mirror "${mirror_args[@]}" "$container_tmp/$MINIO_BUCKET" "local/$MINIO_BUCKET" >/dev/null

printf 'MinIO restored from: %s\n' "$bucket_dir"
