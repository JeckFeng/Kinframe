#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_BASE="${API_BASE:-http://localhost:${FRONTEND_PORT:-3000}/api}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:${FRONTEND_PORT:-3000}}"
BACKEND_BASE="${BACKEND_BASE:-http://localhost:${BACKEND_PORT:-18000}/api}"
MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}"
POSTGRES_USER="${POSTGRES_USER:-kinframe}"
POSTGRES_DB="${POSTGRES_DB:-kinframe}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

json_get() {
  local field="$1"
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$field"
}

json_assert_photo() {
  local photo_id="$1"
  local expected_message="$2"
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
photo_id = sys.argv[1]
expected_message = sys.argv[2]
assert payload["id"] == photo_id
assert payload["category"] == "travel"
assert payload["user_message"] == expected_message
assert payload["include_in_showcase"] is True
assert payload["time_source"] == "uploaded_at"
assert payload["width"] and payload["height"]
assert payload["taken_at"]
assert "camera_make" in payload
assert "camera_model" in payload
' "$photo_id" "$expected_message"
}

expect_status() {
  local expected="$1"
  shift
  local status
  status="$(curl -sS -o /dev/null -w '%{http_code}' "$@")"
  if [[ "$status" != "$expected" ]]; then
    echo "Expected HTTP $expected but got $status: curl $*" >&2
    exit 1
  fi
}

run_worker_once() {
  docker run --rm --network host \
    -e APP_ENV="${APP_ENV:-development}" \
    -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
    -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
    -e REDIS_URL="${REDIS_URL:-redis://localhost:16379/0}" \
    -e MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:19000}" \
    -e MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}" \
    -e MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}" \
    -e MINIO_BUCKET="$MINIO_BUCKET" \
    -e WORKER_ENABLED="${WORKER_ENABLED:-1}" \
    -e WORKER_POLL_INTERVAL_SECONDS="${WORKER_POLL_INTERVAL_SECONDS:-5}" \
    -e PHOTO_JOB_MAX_ATTEMPTS="${PHOTO_JOB_MAX_ATTEMPTS:-3}" \
    -e PHOTO_JOB_RETRY_DELAY_SECONDS="${PHOTO_JOB_RETRY_DELAY_SECONDS:-30}" \
    -e THUMBNAIL_SIZE_PX="${THUMBNAIL_SIZE_PX:-512}" \
    -e PREVIEW_MAX_SIZE_PX="${PREVIEW_MAX_SIZE_PX:-2048}" \
    -v "$ROOT_DIR/backend:/app" \
    -v /app/.venv \
    kinframe-backend-env:stage5 \
    uv run python -m app.workers.photo_processor --once
}

echo "Checking frontend and backend health..."
curl -fsS "$FRONTEND_BASE/login" >/dev/null
curl -fsS "$BACKEND_BASE/health" >/dev/null
curl -fsS "$API_BASE/health" >/dev/null

echo "Applying database migrations..."
docker run --rm --network host \
  -e APP_ENV="${APP_ENV:-development}" \
  -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
  -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
  -v "$ROOT_DIR/backend:/app" \
  -v /app/.venv \
  kinframe-backend-env:stage5 \
  uv run alembic upgrade head

stamp="$(date +%Y%m%d%H%M%S)"
admin_user="v0_admin_$stamp"
member_user="v0_member_$stamp"
viewer_user="v0_viewer_$stamp"
password="password123"
message="v0 acceptance upload $stamp"

echo "Creating acceptance admin..."
docker run --rm --network host \
  -e APP_ENV="${APP_ENV:-development}" \
  -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
  -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
  -v "$ROOT_DIR/backend:/app" \
  -v /app/.venv \
  kinframe-backend-env:stage5 \
  uv run python scripts/create_admin.py \
    --username "$admin_user" \
    --display-name "V0 Admin $stamp" \
    --password "$password"

admin_cookie="$tmp_dir/admin.cookies"
member_cookie="$tmp_dir/member.cookies"
viewer_cookie="$tmp_dir/viewer.cookies"

curl -fsS -c "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$admin_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null

echo "Creating member accounts through admin API..."
curl -fsS -b "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$member_user\",\"display_name\":\"V0 Member $stamp\",\"password\":\"$password\",\"role\":\"member\",\"is_active\":true}" \
  "$API_BASE/admin/users" >/dev/null
curl -fsS -b "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$viewer_user\",\"display_name\":\"V0 Viewer $stamp\",\"password\":\"$password\",\"role\":\"member\",\"is_active\":true}" \
  "$API_BASE/admin/users" >/dev/null

curl -fsS -c "$member_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$member_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null
curl -fsS -c "$viewer_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$viewer_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null

echo "Generating and uploading JPEG without EXIF..."
docker run --rm -i \
  -e KINFRAME_ACCEPT_TS="$stamp" \
  -v "$tmp_dir:/work" \
  kinframe-backend-env:stage5 \
  uv run python - <<'PY'
import os
from PIL import Image

stamp = int(os.environ["KINFRAME_ACCEPT_TS"][-6:])
color = (stamp % 255, (stamp // 3) % 255, (stamp // 7) % 255)
image = Image.new("RGB", (64, 48), color=color)
image.save("/work/acceptance.jpg", format="JPEG", quality=90)
PY

upload_json="$(
  curl -fsS -b "$member_cookie" \
    -F "category=travel" \
    -F "user_message=$message" \
    -F "file=@$tmp_dir/acceptance.jpg;type=image/jpeg" \
    "$API_BASE/photos/upload"
)"
photo_id="$(printf '%s' "$upload_json" | json_get id)"
original_key="$(printf '%s' "$upload_json" | json_get object_key_original)"
thumbnail_key="$(printf '%s' "$upload_json" | json_get object_key_thumbnail)"
preview_key="$(printf '%s' "$upload_json" | json_get object_key_preview)"

echo "Processing uploaded photo with worker..."
photo_ready="0"
for _ in $(seq 1 20); do
  run_worker_once
  processing_json="$(curl -fsS -b "$member_cookie" "$API_BASE/photos/$photo_id/processing-status")"
  photo_status="$(printf '%s' "$processing_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["photo_status"])')"
  if [[ "$photo_status" == "ready" ]]; then
    photo_ready="1"
    break
  fi
  if [[ "$photo_status" == "failed" ]]; then
    printf '%s' "$processing_json" >&2
    exit 1
  fi
done
if [[ "$photo_ready" != "1" ]]; then
  echo "Uploaded photo did not become ready after worker attempts: $photo_id" >&2
  exit 1
fi

printf '%s' "$processing_json" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["photo_status"] == "ready"
assert payload["job_type"] == "photo_ingest"
assert payload["job_status"] == "succeeded"
assert payload["attempts"] == 1
'

echo "Checking MinIO objects..."
docker exec kinframe-minio mc alias set local http://127.0.0.1:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null
docker exec kinframe-minio mc stat "local/$MINIO_BUCKET/$original_key" >/dev/null
docker exec kinframe-minio mc stat "local/$MINIO_BUCKET/$thumbnail_key" >/dev/null
docker exec kinframe-minio mc stat "local/$MINIO_BUCKET/$preview_key" >/dev/null

echo "Checking PostgreSQL records..."
photo_count="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" kinframe-postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from photos where id = '$photo_id';"
)"
user_count="$(
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" kinframe-postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from users where username in ('$admin_user', '$member_user', '$viewer_user');"
)"
[[ "$photo_count" == "1" ]]
[[ "$user_count" == "3" ]]

echo "Checking gallery, thumbnails, detail metadata, and presigned URLs..."
list_json="$(curl -fsS -b "$member_cookie" "$API_BASE/photos")"
printf '%s' "$list_json" | python3 -c '
import json
import sys

photos = json.load(sys.stdin)
photo_id = sys.argv[1]
assert any(photo["id"] == photo_id for photo in photos)
' "$photo_id"
curl -fsS -b "$member_cookie" "$API_BASE/photos?category=life" >/dev/null
curl -fsS -b "$member_cookie" "$API_BASE/photos?category=travel" >/dev/null
photography_json="$(curl -fsS -b "$member_cookie" "$API_BASE/photos?category=photography")"
printf '%s' "$photography_json" | python3 -c '
import json
import sys

photos = json.load(sys.stdin)
photo_id = sys.argv[1]
assert any(photo["id"] == photo_id for photo in photos)
' "$photo_id"
curl -fsS -b "$member_cookie" "$API_BASE/photos?category=pet" >/dev/null
curl -fsS -b "$member_cookie" "$API_BASE/photos/categories" | python3 -c '
import json
import sys

categories = json.load(sys.stdin)
assert [category["slug"] for category in categories] == ["life", "photography", "pet"]
assert [category["name"] for category in categories] == ["生活照", "摄影照", "宠物照"]
'

detail_json="$(curl -fsS -b "$member_cookie" "$API_BASE/photos/$photo_id")"
printf '%s' "$detail_json" | json_assert_photo "$photo_id" "$message"

echo "Checking slide design storage..."
curl -fsS -b "$member_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"version\":2,\"source\":\"fallback\",\"status\":\"active\",\"design_json\":{\"photoId\":\"$photo_id\",\"templateId\":\"warm_memory\",\"templateParams\":{},\"layers\":[{\"id\":\"photo\",\"type\":\"image\",\"zIndex\":10,\"rect\":{\"x\":0,\"y\":0,\"width\":1,\"height\":1}}],\"styleTokens\":{\"--kf-accent-color\":\"#8a9a5b\"},\"renderPolicy\":{\"allowHtml\":false,\"allowJavaScript\":false}}}" \
  "$API_BASE/photos/$photo_id/slide-designs" >/dev/null
curl -fsS -b "$member_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"version\":3,\"source\":\"fallback\",\"status\":\"active\",\"design_json\":{\"photoId\":\"$photo_id\",\"templateId\":\"minimal_white\",\"templateParams\":{},\"layers\":[{\"id\":\"photo\",\"type\":\"image\",\"zIndex\":10,\"rect\":{\"x\":0,\"y\":0,\"width\":1,\"height\":1}}],\"styleTokens\":{\"--kf-accent-color\":\"#d8b26e\"},\"renderPolicy\":{\"allowHtml\":false,\"allowJavaScript\":false}}}" \
  "$API_BASE/photos/$photo_id/slide-designs" >/dev/null
curl -fsS -b "$member_cookie" "$API_BASE/photos/$photo_id/slide-design" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["photo_id"] == sys.argv[1]
assert payload["version"] == 3
assert payload["status"] == "active"
assert payload["design_json"]["templateId"] == "minimal_white"
' "$photo_id"

thumbnail_url="$(curl -fsS -b "$member_cookie" "$API_BASE/photos/$photo_id/thumbnail-url" | json_get url)"
preview_url="$(curl -fsS -b "$member_cookie" "$API_BASE/photos/$photo_id/preview-url" | json_get url)"
original_url="$(curl -fsS -b "$member_cookie" "$API_BASE/photos/$photo_id/original-url" | json_get url)"
curl -fsS "$thumbnail_url" >/dev/null
curl -fsS "$preview_url" >/dev/null
curl -fsS "$original_url" >/dev/null
curl -fsS "$FRONTEND_BASE/gallery" >/dev/null
curl -fsS -b "$member_cookie" "$FRONTEND_BASE/showcase" >/dev/null
curl -fsS "$FRONTEND_BASE/photo/$photo_id" >/dev/null

echo "Checking permissions..."
expect_status 401 "$API_BASE/photos"
expect_status 401 "$API_BASE/photos/$photo_id/thumbnail-url"
expect_status 401 "$API_BASE/photos/$photo_id/preview-url"
expect_status 403 -b "$member_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"blocked_$stamp\",\"display_name\":\"Blocked\",\"password\":\"$password\",\"role\":\"member\"}" \
  "$API_BASE/admin/users"
expect_status 403 -X DELETE -b "$viewer_cookie" "$API_BASE/photos/$photo_id"

echo "Checking batch upload and HEIC behavior..."
docker run --rm -i \
  -e KINFRAME_ACCEPT_TS="$stamp" \
  -v "$tmp_dir:/work" \
  kinframe-backend-env:stage5 \
  uv run python - <<'PY'
import os
from PIL import Image

stamp = int(os.environ["KINFRAME_ACCEPT_TS"][-6:])
for index, name in enumerate(("batch-one.jpg", "batch-two.jpg"), start=1):
    color = ((stamp + index) % 255, (stamp // 5 + index) % 255, (stamp // 11 + index) % 255)
    image = Image.new("RGB", (64 + index, 48), color=color)
    image.save(f"/work/{name}", format="JPEG", quality=90)
PY

batch_json="$(
  curl -fsS -b "$member_cookie" \
    -F "category=life" \
    -F "user_message=batch-$message" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-two.jpg;type=image/jpeg" \
    "$API_BASE/photos/batch-upload"
)"
printf '%s' "$batch_json" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["success_count"] == 2
assert payload["failure_count"] == 0
assert len(payload["results"]) == 2
assert all(item["success"] and item["photo"]["status"] == "processing" for item in payload["results"])
'

partial_json="$(
  curl -fsS -b "$member_cookie" \
    -F "category=life" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/acceptance.jpg;type=image/gif" \
    -F "files=@$tmp_dir/acceptance.jpg;filename=unsupported.heic;type=image/heic" \
    "$API_BASE/photos/batch-upload"
)"
printf '%s' "$partial_json" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["success_count"] == 0
assert payload["failure_count"] == 3
errors = [item["error"] for item in payload["results"]]
assert "Duplicate photo" in errors
assert "Unsupported image MIME type" in errors
assert "HEIC/HEIF conversion is not available" in errors
'

limit_status="$(
  curl -sS -o /dev/null -w '%{http_code}' -b "$member_cookie" \
    -F "category=life" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    -F "files=@$tmp_dir/batch-one.jpg;type=image/jpeg" \
    "$API_BASE/photos/batch-upload"
)"
[[ "$limit_status" == "422" ]]

echo "v0 acceptance passed for photo $photo_id"
