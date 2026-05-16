#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/lib/test_env.sh"

API_BASE="${API_BASE:-http://localhost:${BACKEND_PORT:-18000}/api}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:${FRONTEND_PORT:-3000}}"
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}"
REDIS_URL="${REDIS_URL:-redis://localhost:16379/0}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:19000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}"
MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"

tmp_dir="$(mktemp -d)"
worker_container="kinframe-delete-accept-worker"
minio_stopped=0

cleanup() {
  docker rm -f "$worker_container" >/dev/null 2>&1 || true
  if [[ "$minio_stopped" == "1" ]]; then
    docker start kinframe-minio >/dev/null 2>&1 || true
  fi
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

pass() {
  echo "PASS: $*"
}

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

json_get() {
  local field="$1"
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$field"
}

create_test_png() {
  local output_path="$1"
  local label="$2"
  python3 - "$output_path" "$label" <<'PY'
import struct
import sys
import zlib

output_path = sys.argv[1]
label = sys.argv[2]
width, height = 32, 24
seed = sum(ord(ch) for ch in label)
rows = []
for y in range(height):
    row = bytearray([0])
    for x in range(width):
        row.extend([
            (seed + x * 17 + y * 5) % 256,
            (seed * 3 + x * 7 + y * 11) % 256,
            (255 - seed + x * 13 + y * 19) % 256,
        ])
    rows.append(bytes(row))
raw = zlib.compress(b"".join(rows))

def chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )

ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
text = f"Comment\0{label}".encode("utf-8")
png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", ihdr)
    + chunk(b"tEXt", text)
    + chunk(b"IDAT", raw)
    + chunk(b"IEND", b"")
)
with open(output_path, "wb") as fh:
    fh.write(png)
PY
}

ensure_e2e_admin() {
  local status
  status="$(
    curl -sS -o /dev/null -w '%{http_code}' \
      -H 'Content-Type: application/json' \
      -d '{"username":"e2e_admin","password":"e2epass123"}' \
      "$API_BASE/auth/login" || true
  )"
  if [[ "$status" == "200" ]]; then
    pass "E2E admin already exists"
    return
  fi

  docker run --rm --network host \
    -e APP_ENV="${APP_ENV:-development}" \
    -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
    -e DATABASE_URL="$DATABASE_URL" \
    -v "$ROOT_DIR/backend:/app" \
    -v /app/.venv \
    kinframe-backend-env:stage5 \
    uv run python scripts/create_admin.py \
      --username "e2e_admin" \
      --display-name "E2E Admin" \
      --password "e2epass123" >/dev/null
  pass "E2E admin created"
}

login_with_cookie() {
  local username="$1"
  local password="$2"
  local cookie_path="$3"
  curl -fsS -c "$cookie_path" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
    "$API_BASE/auth/login" >/dev/null
}

create_member_user() {
  local admin_cookie="$1"
  local username="$2"
  local display_name="$3"
  local password="$4"
  curl -fsS -b "$admin_cookie" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$username\",\"display_name\":\"$display_name\",\"password\":\"$password\",\"role\":\"member\",\"is_active\":true}" \
    "$API_BASE/admin/users" >/dev/null
}

upload_photo() {
  local cookie_path="$1"
  local category="$2"
  local message="$3"
  local label="$4"
  local png_path="$tmp_dir/$label.png"
  create_test_png "$png_path" "$label"
  curl -fsS -b "$cookie_path" \
    -F "category=$category" \
    -F "user_message=$message" \
    -F "file=@$png_path;type=image/png" \
    "$API_BASE/photos/upload"
}

run_worker_once() {
  docker run --rm --network host \
    -e APP_ENV="${APP_ENV:-development}" \
    -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
    -e DATABASE_URL="$DATABASE_URL" \
    -e REDIS_URL="$REDIS_URL" \
    -e MINIO_ENDPOINT="$MINIO_ENDPOINT" \
    -e MINIO_ACCESS_KEY="$MINIO_ACCESS_KEY" \
    -e MINIO_SECRET_KEY="$MINIO_SECRET_KEY" \
    -e MINIO_BUCKET="$MINIO_BUCKET" \
    -e AI_ENABLED=false \
    -e GEOCODING_ENABLED=false \
    -v "$ROOT_DIR/backend:/app" \
    -v /app/.venv \
    kinframe-backend-env:stage5 \
    bash -lc 'uv run alembic upgrade head >/dev/null && uv run python -m app.workers.photo_processor --once' >/dev/null
}

start_background_worker() {
  docker rm -f "$worker_container" >/dev/null 2>&1 || true
  docker run -d --name "$worker_container" --network host \
    -e APP_ENV="${APP_ENV:-development}" \
    -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
    -e DATABASE_URL="$DATABASE_URL" \
    -e REDIS_URL="$REDIS_URL" \
    -e MINIO_ENDPOINT="$MINIO_ENDPOINT" \
    -e MINIO_ACCESS_KEY="$MINIO_ACCESS_KEY" \
    -e MINIO_SECRET_KEY="$MINIO_SECRET_KEY" \
    -e MINIO_BUCKET="$MINIO_BUCKET" \
    -e AI_ENABLED=false \
    -e GEOCODING_ENABLED=false \
    -v "$ROOT_DIR/backend:/app" \
    -v /app/.venv \
    kinframe-backend-env:stage5 \
    bash -lc 'uv run alembic upgrade head >/dev/null && uv run python -m app.workers.photo_processor --poll-interval 1' >/dev/null
}

stop_background_worker() {
  docker rm -f "$worker_container" >/dev/null 2>&1 || true
}

wait_until_ready() {
  local photo_id="$1"
  local cookie_path="$2"
  local status_json photo_status

  for _ in $(seq 1 20); do
    run_worker_once
    status_json="$(curl -fsS -b "$cookie_path" "$API_BASE/photos/$photo_id/processing-status")"
    photo_status="$(printf '%s' "$status_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["photo_status"])')"
    if [[ "$photo_status" == "ready" ]]; then
      return 0
    fi
    if [[ "$photo_status" == "failed" ]]; then
      echo "$status_json" >&2
      fail "Photo $photo_id failed before becoming ready"
    fi
  done

  fail "Photo $photo_id did not become ready in time"
}

showcase_contains_photo() {
  local cookie_path="$1"
  local photo_id="$2"
  local expected="$3"
  local json_payload
  json_payload="$(curl -fsS -b "$cookie_path" "$API_BASE/showcase")"
  printf '%s' "$json_payload" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
photo_id = sys.argv[1]
expected = sys.argv[2] == "true"
ids = {item["photo"]["id"] for item in payload["photos"]}
if (photo_id in ids) != expected:
    raise SystemExit(1)
' "$photo_id" "$expected"
}

photos_list_contains_photo() {
  local cookie_path="$1"
  local photo_id="$2"
  local expected="$3"
  local json_payload
  json_payload="$(curl -fsS -b "$cookie_path" "$API_BASE/photos")"
  printf '%s' "$json_payload" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
photo_id = sys.argv[1]
expected = sys.argv[2] == "true"
ids = {item["id"] for item in payload}
if (photo_id in ids) != expected:
    raise SystemExit(1)
' "$photo_id" "$expected"
}

wait_for_purge_job_status() {
  local admin_cookie="$1"
  local job_id="$2"
  local expected_status="$3"
  local jobs_json

  for _ in $(seq 1 10); do
    run_worker_once || true
    jobs_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/jobs?job_type=photo_purge")"
    if printf '%s' "$jobs_json" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
job_id = sys.argv[1]
expected = sys.argv[2]
for item in payload:
    if item["id"] == job_id:
        raise SystemExit(0 if item["status"] == expected else 1)
raise SystemExit(1)
' "$job_id" "$expected_status"; then
      return 0
    fi
  done

  fail "Photo purge job $job_id did not reach status $expected_status"
}

echo "=== KinFrame v0.5 Delete Acceptance ==="
require_command python3
ensure_infra_running
ensure_backend_running "$API_BASE"
curl -fsS "$FRONTEND_BASE/login" >/dev/null

echo "--- Preparing accounts ---"
ensure_e2e_admin
admin_cookie="$tmp_dir/admin.cookies"
login_with_cookie "e2e_admin" "e2epass123" "$admin_cookie"

stamp="$(date +%Y%m%d%H%M%S)"
member_hide="delete_hide_$stamp"
member_delete="delete_purge_$stamp"
member_fail="delete_fail_$stamp"
password="password123"

create_member_user "$admin_cookie" "$member_hide" "Delete Hide $stamp" "$password"
create_member_user "$admin_cookie" "$member_delete" "Delete Purge $stamp" "$password"
create_member_user "$admin_cookie" "$member_fail" "Delete Fail $stamp" "$password"

member_hide_cookie="$tmp_dir/member_hide.cookies"
member_delete_cookie="$tmp_dir/member_delete.cookies"
member_fail_cookie="$tmp_dir/member_fail.cookies"
login_with_cookie "$member_hide" "$password" "$member_hide_cookie"
login_with_cookie "$member_delete" "$password" "$member_delete_cookie"
login_with_cookie "$member_fail" "$password" "$member_fail_cookie"

echo "--- Scenario A: hide/unhide acceptance ---"
hide_message="v0.5 delete hide $stamp"
hide_upload="$(upload_photo "$member_hide_cookie" "life" "$hide_message" "hide-$stamp")"
hide_photo_id="$(printf '%s' "$hide_upload" | json_get id)"
wait_until_ready "$hide_photo_id" "$member_hide_cookie"
showcase_contains_photo "$member_hide_cookie" "$hide_photo_id" true
photos_list_contains_photo "$member_hide_cookie" "$hide_photo_id" true

curl -fsS -b "$member_hide_cookie" \
  -H 'Content-Type: application/json' \
  -X PATCH \
  -d '{"include_in_showcase":false}' \
  "$API_BASE/photos/$hide_photo_id" >/dev/null
showcase_contains_photo "$member_hide_cookie" "$hide_photo_id" false
photos_list_contains_photo "$member_hide_cookie" "$hide_photo_id" true

curl -fsS -b "$member_hide_cookie" \
  -H 'Content-Type: application/json' \
  -X PATCH \
  -d '{"include_in_showcase":true}' \
  "$API_BASE/photos/$hide_photo_id" >/dev/null
showcase_contains_photo "$member_hide_cookie" "$hide_photo_id" true
pass "Scenario A hide/unhide API path"

echo "--- Scenario B: permanent delete acceptance ---"
delete_message="v0.5 delete purge $stamp"
delete_upload="$(upload_photo "$member_delete_cookie" "life" "$delete_message" "purge-$stamp")"
delete_photo_id="$(printf '%s' "$delete_upload" | json_get id)"
wait_until_ready "$delete_photo_id" "$member_delete_cookie"
showcase_contains_photo "$admin_cookie" "$delete_photo_id" true

delete_response="$(curl -fsS -b "$admin_cookie" -X POST "$API_BASE/admin/photos/$delete_photo_id/delete")"
delete_job_id="$(printf '%s' "$delete_response" | json_get job_id)"
wait_for_purge_job_status "$admin_cookie" "$delete_job_id" "succeeded"
showcase_contains_photo "$admin_cookie" "$delete_photo_id" false
photos_list_contains_photo "$admin_cookie" "$delete_photo_id" false

detail_status="$(curl -sS -o /dev/null -w '%{http_code}' -b "$admin_cookie" "$API_BASE/photos/$delete_photo_id")"
[[ "$detail_status" == "404" ]] || fail "Deleted photo detail should return 404"
thumb_status="$(curl -sS -o /dev/null -w '%{http_code}' -b "$admin_cookie" "$API_BASE/photos/$delete_photo_id/thumbnail-url")"
[[ "$thumb_status" == "404" ]] || fail "Deleted photo thumbnail URL should return 404"

admin_photos_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/photos")"
printf '%s' "$admin_photos_json" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
photo_id = sys.argv[1]
ids = {item["id"] for item in payload["items"]}
if photo_id in ids:
    raise SystemExit(1)
' "$delete_photo_id"
pass "Scenario B permanent delete API path"

echo "--- Playwright UI regression ---"
start_background_worker
run_playwright_suite "$ROOT_DIR" "$FRONTEND_BASE" \
  --project=desktop \
  --grep "photo owner hide/unhide updates showcase while keeping photo in gallery|admin permanent delete removes photo from showcase, gallery, and stale detail fetches"
stop_background_worker
pass "Playwright delete flows"

echo "--- Scenario C: purge failure visibility ---"
fail_message="v0.5 delete failure $stamp"
fail_upload="$(upload_photo "$member_fail_cookie" "life" "$fail_message" "fail-$stamp")"
fail_photo_id="$(printf '%s' "$fail_upload" | json_get id)"
wait_until_ready "$fail_photo_id" "$member_fail_cookie"

docker stop kinframe-minio >/dev/null
minio_stopped=1
fail_delete_response="$(curl -fsS -b "$admin_cookie" -X POST "$API_BASE/admin/photos/$fail_photo_id/delete")"
fail_delete_job_id="$(printf '%s' "$fail_delete_response" | json_get job_id)"
run_worker_once || true

jobs_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/jobs?job_type=photo_purge")"
printf '%s' "$jobs_json" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
job_id = sys.argv[1]
for item in payload:
    if item["id"] == job_id:
        assert item["status"] == "failed"
        assert item["error_message"]
        raise SystemExit(0)
raise SystemExit(1)
' "$fail_delete_job_id"

audits_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/audit-logs?action=photo.delete_failed&target_id=$fail_photo_id")"
printf '%s' "$audits_json" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["total"] >= 1
entry = payload["items"][0]
assert entry["action"] == "photo.delete_failed"
assert entry["detail"]["error_message"]
' 

photo_status_after_failure="$(curl -sS -o /dev/null -w '%{http_code}' -b "$member_fail_cookie" "$API_BASE/photos/$fail_photo_id")"
[[ "$photo_status_after_failure" == "200" ]] || fail "Failed purge should not remove the photo"

docker start kinframe-minio >/dev/null
minio_stopped=0
sleep 2
pass "Scenario C purge failure visibility"

echo "=== KinFrame v0.5 Delete Acceptance PASSED ==="
