#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_BASE="${API_BASE:-http://localhost:${FRONTEND_PORT:-3000}/api}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:${FRONTEND_PORT:-3000}}"

echo "=== KinFrame v0.2 Acceptance ==="
echo ""

# ── 1. Check infrastructure ───────────────────────────────────────
echo "--- 1. Infrastructure ---"

if [[ "$(docker inspect -f '{{.State.Running}}' kinframe-postgres 2>/dev/null || true)" != "true" ]]; then
  echo "Starting Docker infra..."
  just infra
  echo "Waiting for PostgreSQL..."
  for _ in $(seq 1 15); do
    if docker exec kinframe-postgres pg_isready -U kinframe -d kinframe >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi
echo "  PostgreSQL: running"

# ── 2. Create test user and login ────────────────────────────────
echo "--- 2. Authentication ---"

stamp="$(date +%Y%m%d%H%M%S)"
admin_user="v02admin_$stamp"
password="password123"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

docker run --rm --network host \
  -e APP_ENV="${APP_ENV:-development}" \
  -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
  -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
  -v "$ROOT_DIR/backend:/app" \
  -v /app/.venv \
  kinframe-backend-env:stage5 \
  uv run python scripts/create_admin.py \
    --username "$admin_user" \
    --display-name "V0.2 Admin $stamp" \
    --password "$password"

admin_cookie="$tmp_dir/admin.cookies"
curl -fsS -c "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$admin_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null
echo "  Admin logged in: $admin_user"

# Create a regular member too
member_user="v02member_$stamp"
docker run --rm --network host \
  -e APP_ENV="${APP_ENV:-development}" \
  -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
  -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
  -v "$ROOT_DIR/backend:/app" \
  -v /app/.venv \
  kinframe-backend-env:stage5 \
  uv run python scripts/create_admin.py \
    --username "$member_user" \
    --display-name "V0.2 Member $stamp" \
	    --role member \
    --password "$password"

member_cookie="$tmp_dir/member.cookies"
curl -fsS -c "$member_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$member_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null
echo "  Member logged in: $member_user"

# ── 3. Upload test photos ─────────────────────────────────────────
echo "--- 3. Upload test photos ---"

upload_photo() {
  local label="$1" category="$2" message="$3"
  # Generate a unique tiny PNG per upload (seed=label+stamp for run-to-run uniqueness)
  python3 -c "
import struct, zlib, sys
label = sys.argv[1]
stamp = sys.argv[2]
seed = sum(ord(c) for c in label + stamp)
def create_png(w, h, offset):
    raw = b''
    for y in range(h):
        raw += bytes([(y * 3 + offset) % 256, (offset) % 256, (255 - y * 3 - offset) % 256] * w)
    def ihdr(): return struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    raw_data = zlib.compress(raw)
    def chunk(typ, data): return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr()) + chunk(b'IDAT', raw_data) + chunk(b'IEND', b'')
with open('/tmp/v02_test.png', 'wb') as f:
    f.write(create_png(64, 48, seed))
" "$label" "$stamp"
  curl -fsS -b "$admin_cookie" \
    -F "file=@/tmp/v02_test.png;type=image/png" \
    -F "category=$category" \
    -F "user_message=$message" \
    "$API_BASE/photos/upload" >/dev/null
  echo "  Uploaded: $label"
}

upload_photo "life photo" "life" "A family moment"
upload_photo "pet photo" "pet" "My cat"
upload_photo "photography photo" "photography" ""

echo "  OK: 3 photos uploaded"

# ── 4. Worker processing ──────────────────────────────────────────
echo "--- 4. Worker processing ---"

# Run worker in --once mode multiple times to process all jobs
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

# ── 5. Verify slide design and showcase ───────────────────────────
echo "--- 5. Slide design & showcase ---"

showcase_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/showcase")"
printf '%s' "$showcase_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)

# Check categories
cats = data["categories"]
assert len(cats) >= 3, f"Expected >=3 categories, got {len(cats)}"
active_slugs = {c["slug"] for c in cats if c["is_active"]}
assert "life" in active_slugs
assert "photography" in active_slugs
assert "pet" in active_slugs
print(f"  Categories OK: {len(cats)} total")

# Check photos
photos = data["photos"]
assert len(photos) >= 3, f"Expected >=3 photos, got {len(photos)}"
ready_count = sum(1 for p in photos if p["photo"]["status"] == "ready")
assert ready_count >= 1, f"No ready photos found (got {ready_count})"
print(f"  Photos: {len(photos)} total, {ready_count} ready")

# Check slide designs
for item in photos:
    if item["photo"]["status"] != "ready":
        continue
    sd = item["slide_design"]
    assert sd is not None, f"Photo {item['photo']['id']} missing slide_design"
    assert sd["templateId"], "Missing templateId"
    assert len(sd["layers"]) >= 1, f"Slide design has no layers"
    has_image = any(l["type"] == "image" for l in sd["layers"])
    assert has_image, "Slide design missing image layer"
print("  Slide designs OK: all ready photos have valid designs")

# Check preview URLs
for item in photos:
    if item["photo"]["status"] == "ready":
        assert item["preview_url"], f"Photo {item['photo']['id']} missing preview_url"
print("  Preview URLs OK")
'

# ── 6. Verify photo detail page (user vs admin visibility) ───────
echo "--- 6. Photo detail & permissions ---"

# Get first ready photo
first_photo_id="$(printf '%s' "$showcase_json" | python3 -c '
import json,sys
data=json.load(sys.stdin)
for item in data["photos"]:
    if item["photo"]["status"]=="ready":
        print(item["photo"]["id"])
        break
')"

# Admin sees full details
admin_detail="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/photos/$first_photo_id")"
printf '%s' "$admin_detail" | python3 -c '
import json,sys
d = json.load(sys.stdin)
assert d["id"], "Missing id"
assert "caption_source" in d, "Admin detail missing caption_source"
assert "category_source" in d, "Admin detail missing category_source"
assert "geocoding_status" in d, "Admin detail missing geocoding_status"
print("  Admin photo detail OK: includes diagnostic fields")
'

# Regular user sees only public fields
member_detail="$(curl -fsS -b "$member_cookie" "$API_BASE/photos/$first_photo_id")"
printf '%s' "$member_detail" | python3 -c '
import json,sys
d = json.load(sys.stdin)
assert d["id"], "Missing id"
assert "ai_analysis_json" not in d, "Regular user should NOT see ai_analysis_json"
assert "exif_json" not in d, "Regular user should NOT see exif_json"
assert "geocoding_error" not in d, "Regular user should NOT see geocoding_error"
print("  User photo detail OK: sensitive fields absent")
'

# Non-admin blocked from admin APIs
curl -fsS -b "$member_cookie" "$API_BASE/admin/photos/$first_photo_id" >/dev/null 2>&1 && {
  echo "  FAIL: regular user accessed admin photo API" >&2; exit 1
} || echo "  Permission boundary OK: 403 on admin APIs"

# ── 7. Verify admin jobs ──────────────────────────────────────────
echo "--- 7. Admin jobs ---"

jobs_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/jobs")"
printf '%s' "$jobs_json" | python3 -c '
import json,sys
data = json.load(sys.stdin)
assert len(data) > 0, "No jobs found"
types = {j["job_type"] for j in data}
assert "photo_ingest" in types, f"No photo_ingest jobs in {types}"
print(f"  Jobs OK: {len(data)} jobs, types: {sorted(types)}")
'

# ── 8. Verify admin categories ────────────────────────────────────
echo "--- 8. Admin categories ---"

curl -fsS -b "$admin_cookie" "$API_BASE/admin/categories" | python3 -c '
import json,sys
data = json.load(sys.stdin)
assert len(data) >= 3, f"Expected >=3 categories, got {len(data)}"
slugs = {c["slug"] for c in data}
assert "life" in slugs
assert "photography" in slugs
assert "pet" in slugs
print(f"  Categories OK: {len(data)} categories, slugs: {sorted(slugs)}")
'

# ── 9. Verify admin audit logs ────────────────────────────────────
echo "--- 9. Admin audit logs ---"

# Create an admin action to generate an audit entry, then immediately verify it
curl -fsS -b "$admin_cookie" \
  -X PATCH \
  -H 'Content-Type: application/json' \
  -d "{\"final_caption\": \"Audit test $stamp\"}" \
  "$API_BASE/admin/photos/$first_photo_id" >/dev/null 2>&1 || true

audit_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/audit-logs?limit=5")"
printf '%s' "$audit_json" | python3 -c '
import json,sys
data = json.load(sys.stdin)
assert "items" in data, "Missing items"
assert "total" in data, "Missing total"
assert data["total"] >= 1, "No audit log entries"
entry = data["items"][0]
assert entry["action"], "Missing action"
assert entry["target_type"], "Missing target_type"
total = data["total"]
print(f"  Audit logs OK: {total} entries")
'

# Non-admin blocked from audit logs
curl -fsS -b "$member_cookie" "$API_BASE/admin/audit-logs" >/dev/null 2>&1 && {
  echo "  FAIL: regular user accessed audit logs" >&2; exit 1
} || echo "  Permission boundary OK: audit logs require admin"

# ── 10. Verify backup/restore ─────────────────────────────────────
echo "--- 10. Backup & restore ---"

backup_output="$(BACKUP_DIR="${BACKUP_DIR:-data/backups}" scripts/backup.sh)"
printf '%s\n' "$backup_output"
backup_dir="$(printf '%s\n' "$backup_output" | awk -F': ' '/Backup completed:/ {print $2}' | tail -n 1)"
if [[ -z "$backup_dir" || ! -s "$backup_dir/manifest.json" ]]; then
  echo "Backup did not produce a valid manifest." >&2
  exit 1
fi

# Verify manifest includes new v0.2 data
python3 -c '
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert "postgres" in manifest
pg = manifest["postgres"]
assert "slide_design_count" in pg, "Manifest missing slide_design_count"
assert pg["slide_design_count"] >= 1, "No slide designs in backup"
if "category_count" in pg:
    assert pg["category_count"] >= 3, f"Expected >=3 categories, got {pg["category_count"]}"
print(f"  Manifest OK: photos={pg["photo_count"]}, slide_designs={pg["slide_design_count"]}, categories={pg.get("category_count", "N/A")}, audit_logs={pg.get("audit_log_count", "N/A")}")
' "$backup_dir/manifest.json"

scripts/restore-check.sh "$backup_dir"
echo "  Backup/restore OK"

# ── 11. Verify mouse navigation code ──────────────────────────────
echo "--- 11. Mouse navigation ---"

grep -q "onMouseClick" frontend/pages/showcase.vue && echo "  Left-click handler: present" || { echo "  FAIL: missing left-click handler" >&2; exit 1; }
grep -q "onContextMenu" frontend/pages/showcase.vue && echo "  Right-click handler: present" || { echo "  FAIL: missing right-click handler" >&2; exit 1; }
grep -q "onWheel" frontend/pages/showcase.vue && echo "  Wheel handler: present" || { echo "  FAIL: missing wheel handler" >&2; exit 1; }
grep -q "event.preventDefault()" frontend/pages/showcase.vue && echo "  Default context menu prevented" || { echo "  FAIL: contextmenu not prevented" >&2; exit 1; }

# ── 12. Verify admin can modify and reset ─────────────────────────
echo "--- 12. Admin modification ---"

# Admin updates location and final_caption
curl -fsS -b "$admin_cookie" \
  -X PATCH \
  -H 'Content-Type: application/json' \
  -d '{"location_city": "Beijing", "location_country": "China", "final_caption": "Admin test caption"}' \
  "$API_BASE/admin/photos/$first_photo_id" >/dev/null

# Verify the update took effect
updated_detail="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/photos/$first_photo_id")"
printf '%s' "$updated_detail" | python3 -c '
import json,sys
d = json.load(sys.stdin)
lc = d["location_city"]
assert lc == "Beijing", f"Expected Beijing, got {lc}"
fc = d["final_caption"]
assert fc == "Admin test caption", f"Expected admin caption, got {fc}"
cs = d["caption_source"]
assert cs == "admin", f"Expected admin source, got {cs}"
print("  Admin update OK: location and caption modified")
'

# Reset caption
curl -fsS -b "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -X POST "$API_BASE/admin/photos/$first_photo_id/reset-caption" >/dev/null

# Verify caption was reset
reset_detail="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/photos/$first_photo_id")"
printf '%s' "$reset_detail" | python3 -c '
import json,sys
d = json.load(sys.stdin)
cs = d["caption_source"]
assert cs != "admin", f"Caption should be reset, got {cs}"
fc = d["final_caption"]
print(f"  Caption reset OK: source={cs}, caption={fc}")
'

# ── Summary ───────────────────────────────────────────────────────
echo ""
echo "====================================="
echo "  v0.2 Acceptance: ALL CHECKS PASSED"
echo "====================================="
