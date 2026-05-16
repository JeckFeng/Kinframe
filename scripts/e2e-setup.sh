#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/lib/test_env.sh"

API_BASE="${API_BASE:-http://localhost:${BACKEND_PORT:-18000}/api}"

echo "=== KinFrame E2E Test Data Setup ==="

# ── 1. Check infrastructure ───────────────────────────────────────
echo "--- Checking infrastructure ---"
require_command python3
ensure_infra_running
ensure_backend_running "$API_BASE"
echo "  Infrastructure: OK"
echo "  Backend API: OK"

# ── 2. Create admin user ─────────────────────────────────────────
echo "--- Creating test users ---"

stamp="$(date +%Y%m%d%H%M%S)"
admin_user="e2e_admin"
admin_password="e2epass123"

# Check if admin already exists
if curl -fsS -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$admin_user\",\"password\":\"$admin_password\"}" \
  "$API_BASE/auth/login" 2>/dev/null | grep -q 200; then
  echo "  Admin already exists: $admin_user"
else
  docker run --rm --network host \
    -e APP_ENV="${APP_ENV:-development}" \
    -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
    -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
    -v "$ROOT_DIR/backend:/app" \
    -v /app/.venv \
    kinframe-backend-env:stage5 \
    uv run python scripts/create_admin.py \
      --username "$admin_user" \
      --display-name "E2E Admin" \
      --password "$admin_password" 2>/dev/null
  echo "  Admin created: $admin_user"
fi

# Login and save cookies
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
admin_cookie="$tmp_dir/admin.cookies"

curl -fsS -c "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$admin_user\",\"password\":\"$admin_password\"}" \
  "$API_BASE/auth/login" >/dev/null
echo "  Admin logged in"

# ── 3. Upload test photos ────────────────────────────────────────
echo "--- Uploading test photos ---"

upload_photo() {
  local label="$1" category="$2" message="$3"
  # Generate a unique tiny PNG per upload
  python3 -c "
import struct, zlib, sys
label = sys.argv[1]
seed = sum(ord(c) for c in label)
def create_png(w, h, offset):
    raw = b''
    for y in range(h):
        raw += bytes([(y * 3 + offset) % 256, (offset) % 256, (255 - y * 3 - offset) % 256] * w)
    def ihdr(): return struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    raw_data = zlib.compress(raw)
    def chunk(typ, data): return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr()) + chunk(b'IDAT', raw_data) + chunk(b'IEND', b'')
with open('/tmp/e2e_test.png', 'wb') as f:
    f.write(create_png(64, 48, seed))
" "$label"
  curl -fsS -b "$admin_cookie" \
    -F "file=@/tmp/e2e_test.png;type=image/png" \
    -F "category=$category" \
    -F "user_message=$message" \
    "$API_BASE/photos/upload" >/dev/null
  echo "  Uploaded: $label (category=$category)"
}

# Only upload if no ready photos exist
photo_count=$(curl -fsS -b "$admin_cookie" "$API_BASE/showcase" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['photos']))" 2>/dev/null || echo "0")
if [[ "$photo_count" -lt 3 ]]; then
  upload_photo "life_test" "life" "A family moment in the garden"
  upload_photo "pet_test" "pet" "My cat sleeping"
  upload_photo "photography_test" "photography" ""
  upload_photo "life_test2" "life" "Birthday celebration"
  echo "  OK: test photos uploaded"
else
  echo "  OK: $photo_count photos already exist, skipping upload"
fi

# ── 4. Run worker processing ─────────────────────────────────────
echo "--- Running worker ---"

# Check if we have unprocessed photos
pending_count=$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/jobs" 2>/dev/null | python3 -c "
import json,sys
data=json.load(sys.stdin)
pending=[j for j in data if j.get('status')=='pending']
print(len(pending))
" 2>/dev/null || echo "0")

if [[ "$pending_count" -gt 0 ]]; then
  for i in $(seq 1 6); do
    docker run --rm --network host \
      -e APP_ENV="${APP_ENV:-development}" \
      -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
      -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
      -e MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:19000}" \
      -e MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}" \
      -e MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}" \
      -e MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}" \
      -e AI_ENABLED="${AI_ENABLED:-false}" \
      -e GEOCODING_ENABLED="${GEOCODING_ENABLED:-false}" \
      -v "$ROOT_DIR/backend:/app" \
      -v /app/.venv \
      kinframe-backend-env:stage5 \
      bash -lc 'uv run alembic upgrade head && uv run python -m app.workers.photo_processor --once' 2>&1 || true
  done
  echo "  Worker processing complete"
else
  echo "  OK: no pending jobs, skipping worker"
fi

# ── 5. Verify ready photos exist ─────────────────────────────────
echo "--- Verification ---"
ready_count=$(curl -fsS -b "$admin_cookie" "$API_BASE/showcase" | python3 -c "
import json,sys
data=json.load(sys.stdin)
ready=[p for p in data['photos'] if p['photo']['status']=='ready']
print(len(ready))
")
echo "  Ready photos: $ready_count"
if [[ "$ready_count" -lt 1 ]]; then
  echo "  WARNING: No ready photos found. E2E tests may fail."
fi

echo "=== E2E Setup Complete ==="
echo "  Admin: $admin_user / $admin_password"
echo "  Cookie file: $admin_cookie"
