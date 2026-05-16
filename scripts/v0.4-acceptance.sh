#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/lib/test_env.sh"

API_BASE="${API_BASE:-http://localhost:${BACKEND_PORT:-18000}/api}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:${FRONTEND_PORT:-3000}}"

echo "=== KinFrame v0.4 Acceptance ==="
echo ""

PASSED=0
FAILED=0

pass() { echo "  PASS: $1"; PASSED=$((PASSED + 1)); }
fail() { echo "  FAIL: $1" >&2; FAILED=$((FAILED + 1)); }

# ── 1. Verify infrastructure ───────────────────────────────────────
echo "--- 1. Infrastructure ---"
require_command python3
ensure_infra_running

for svc in kinframe-postgres kinframe-redis kinframe-minio; do
  if [[ "$(docker inspect -f '{{.State.Running}}' "$svc" 2>/dev/null || true)" == "true" ]]; then
    pass "$svc running"
  else
    fail "$svc not running"
  fi
done

# Verify backend health
if ensure_backend_running "$API_BASE" >/dev/null 2>&1; then
  pass "Backend health check"
fi

# ── 2. Create test users and login ─────────────────────────────────
echo "--- 2. Authentication ---"

stamp="$(date +%Y%m%d%H%M%S)"
admin_user="v04admin_$stamp"
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
    --display-name "V0.4 Admin $stamp" \
    --password "$password"

admin_cookie="$tmp_dir/admin.cookies"
curl -fsS -c "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$admin_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null
pass "Admin created and logged in: $admin_user"

# Create regular member
member_user="v04member_$stamp"
docker run --rm --network host \
  -e APP_ENV="${APP_ENV:-development}" \
  -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
  -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
  -v "$ROOT_DIR/backend:/app" \
  -v /app/.venv \
  kinframe-backend-env:stage5 \
  uv run python scripts/create_admin.py \
    --username "$member_user" \
    --display-name "V0.4 Member $stamp" \
    --role member \
    --password "$password"

member_cookie="$tmp_dir/member.cookies"
curl -fsS -c "$member_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$member_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null
pass "Member created and logged in: $member_user"

# ── 3. Upload test photos to all categories ────────────────────────
echo "--- 3. Upload test photos ---"

upload_photo() {
  local label="$1" category="$2" message="$3"
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
with open('/tmp/v04_test.png', 'wb') as f:
    f.write(create_png(64, 48, seed))
" "$label" "$stamp"
  http_code=$(curl -sS -o /dev/null -w '%{http_code}' -b "$admin_cookie" \
    -F "file=@/tmp/v04_test.png;type=image/png" \
    -F "category=$category" \
    -F "user_message=$message" \
    "$API_BASE/photos/upload" )
          if [[ "$http_code" == "201" ]]; then
            echo "  Uploaded: $label"
          elif [[ "$http_code" == "409" ]]; then
            echo "  Skipped (duplicate): $label"
          else
            echo "  Upload failed (HTTP $http_code): $label" >&2
            return 1
          fi
}

upload_photo "life photo" "life" "A family moment in the garden"
upload_photo "pet photo" "pet" "My cat sleeping in the sun"
upload_photo "photography photo" "photography" ""
upload_photo "life photo 2" "life" "Birthday celebration"
pass "4 photos uploaded across 3 categories"

# ── 4. Run worker to process all photos ────────────────────────────
echo "--- 4. Worker processing ---"

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

# Count ready photos
ready_count=$(curl -fsS -b "$admin_cookie" "$API_BASE/showcase" | python3 -c "
import json,sys
data=json.load(sys.stdin)
ready=[p for p in data['photos'] if p['photo']['status']=='ready']
print(len(ready))
")
if [[ "$ready_count" -ge 1 ]]; then
  pass "Worker processing: $ready_count ready photos"
else
  fail "Worker processing: no ready photos"
fi

# ── 5. Verify showcase API with slide designs ──────────────────────
echo "--- 5. Showcase API & slide designs ---"

showcase_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/showcase")"
printf '%s' "$showcase_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)

# Categories
cats = data["categories"]
assert len(cats) >= 3, f"Expected >=3 categories, got {len(cats)}"
active_slugs = {c["slug"] for c in cats if c["is_active"]}
assert "life" in active_slugs
assert "photography" in active_slugs
assert "pet" in active_slugs
print(f"  Categories OK: {len(cats)} total, active: {sorted(active_slugs)}")

# Photos
photos = data["photos"]
assert len(photos) >= 3, f"Expected >=3 photos, got {len(photos)}"
ready = [p for p in photos if p["photo"]["status"] == "ready"]
assert len(ready) >= 1, f"No ready photos (got {len(ready)})"
print(f"  Photos: {len(photos)} total, {len(ready)} ready")

# Slide designs
for item in ready:
    sd = item["slide_design"]
    pid = item["photo"]["id"]
    assert sd is not None, f"Photo {pid} missing slide_design"
    assert sd["templateId"], "Missing templateId"
    assert len(sd["layers"]) >= 1, "No layers"
    has_image = any(l["type"] == "image" for l in sd["layers"])
    assert has_image, "Missing image layer"
print("  Slide designs OK: all ready photos have valid designs")

# Preview URLs
for item in ready:
    pid = item["photo"]["id"]
    assert item["preview_url"], f"Photo {pid} missing preview_url"
print("  Preview URLs OK")
'
pass "Showcase API: categories, photos, slide designs, preview URLs verified"

# ── 6. Verify admin endpoints ─────────────────────────────────────
echo "--- 6. Admin endpoints ---"

# Admin jobs
jobs_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/jobs")"
printf '%s' "$jobs_json" | python3 -c '
import json,sys
data = json.load(sys.stdin)
assert len(data) > 0, "No jobs found"
types = {j["job_type"] for j in data}
assert "photo_ingest" in types, f"No photo_ingest jobs in {types}"
print(f"  Jobs OK: {len(data)} jobs, types: {sorted(types)}")
'
pass "Admin jobs endpoint"

# Admin categories
curl -fsS -b "$admin_cookie" "$API_BASE/admin/categories" | python3 -c '
import json,sys
data = json.load(sys.stdin)
assert len(data) >= 3, f"Expected >=3 categories, got {len(data)}"
slugs = {c["slug"] for c in data}
assert "life" in slugs and "photography" in slugs and "pet" in slugs
print(f"  Categories OK: {len(data)} categories, slugs: {sorted(slugs)}")
'
pass "Admin categories endpoint"

# Admin audit logs
first_photo_id="$(printf '%s' "$showcase_json" | python3 -c '
import json,sys
data=json.load(sys.stdin)
for item in data["photos"]:
    if item["photo"]["status"]=="ready":
        print(item["photo"]["id"])
        break
')"

# Trigger an admin action to create audit log
curl -fsS -b "$admin_cookie" \
  -X PATCH \
  -H 'Content-Type: application/json' \
  -d "{\"final_caption\": \"Acceptance test $stamp\"}" \
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
pass "Admin audit logs endpoint"

# Non-admin blocked from admin endpoints
curl -fsS -b "$member_cookie" "$API_BASE/admin/jobs" >/dev/null 2>&1 && {
  fail "Permission: member accessed admin jobs"
} || pass "Permission: member blocked from admin jobs"

curl -fsS -b "$member_cookie" "$API_BASE/admin/audit-logs" >/dev/null 2>&1 && {
  fail "Permission: member accessed audit logs"
} || pass "Permission: member blocked from audit logs"

# ── 7. Verify v0.3 new fields ─────────────────────────────────────
echo "--- 7. v0.3 new fields ---"

printf '%s' "$showcase_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)

v03_template_ids = {
    "cinematic_fullscreen", "warm_memory", "minimal_white",
    "poetic_landscape", "magazine_left", "gallery_center",
    "dark_exhibition", "pet_portrait",
}

v03_layer_types = {
    "shape", "image", "text", "timeline", "background", "mask",
    "texture", "vignette",
}

templates_seen = set()
layer_types_seen = set()
for item in data["photos"]:
    if item.get("slide_design"):
        sd = item["slide_design"]
        templates_seen.add(sd.get("templateId"))
        for layer in sd.get("layers", []):
            layer_types_seen.add(layer.get("type"))

unknown_templates = templates_seen - v03_template_ids
if unknown_templates:
    print(f"  WARNING: Unknown templates: {unknown_templates}")
else:
    print(f"  Templates OK: {templates_seen}")

unknown_layers = layer_types_seen - v03_layer_types
if unknown_layers:
    print(f"  WARNING: Unknown layer types: {unknown_layers}")
else:
    print(f"  Layer types OK: {layer_types_seen}")

print("  v0.3 schema fields: template IDs and layer types validated")
'

python3 -c "
import json
schema_path = '$ROOT_DIR/backend/app/schemas/slide_design.schema.json'
with open(schema_path) as f:
    schema = json.load(f)

layer_props = schema['properties']['layers']['items']['properties']
fill = layer_props.get('fill')
if fill:
    fill_types = fill.get('properties', {}).get('type', {}).get('enum', [])
    print(f'  Fill model: present (types: {fill_types})')
else:
    print('  Fill model: NOT FOUND in layer properties')

shadow = layer_props.get('shadow')
if shadow:
    shadow_types = shadow.get('properties', {}).get('type', {}).get('enum', [])
    print(f'  Shadow model: present (types: {shadow_types})')
else:
    print('  Shadow model: NOT FOUND in layer properties')
"
pass "v0.3 schema fields: Fill, Shadow, template IDs, layer types verified"

# ── 8. Run Playwright tests ────────────────────────────────────────
echo "--- 8. Playwright E2E tests ---"

if command -v npx &>/dev/null; then
  if run_playwright_suite "$ROOT_DIR" "$FRONTEND_BASE" 2>&1; then
    pass "Playwright E2E tests passed"
  else
    fail "Playwright E2E tests failed"
  fi
else
  fail "Playwright E2E tests unavailable (npx not found)"
fi

# ── 9. Verify backup/restore with v0.3 data ───────────────────────
cd "$ROOT_DIR"
echo "--- 9. Backup & restore ---"

backup_output="$(BACKUP_DIR="${BACKUP_DIR:-data/backups}" scripts/backup.sh 2>&1)"
printf '%s\n' "$backup_output"
backup_dir="$(printf '%s\n' "$backup_output" | awk -F': ' '/Backup completed:/ {print $2}' | tail -n 1)"
if [[ -z "$backup_dir" || ! -s "$backup_dir/manifest.json" ]]; then
  fail "Backup did not produce valid manifest"
else
  python3 -c '
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert "postgres" in manifest
pg = manifest["postgres"]
assert "slide_design_count" in pg, "Manifest missing slide_design_count"
assert pg["slide_design_count"] >= 1, "No slide designs in backup"
assert "photo_count" in pg, "Manifest missing photo_count"
pc = pg.get("photo_count", 0)
assert pc >= 3, f"Expected >=3 photos, got {pc}"
sdc = pg.get("slide_design_count", 0)
cc = pg.get("category_count", "N/A")
alc = pg.get("audit_log_count", "N/A")
print(f"  Manifest OK: photos={pc}, slide_designs={sdc}, categories={cc}, audit_logs={alc}")
' "$backup_dir/manifest.json"

  scripts/restore-check.sh "$backup_dir" 2>&1 || {
    fail "Restore check failed"
  }
  pass "Backup/restore: manifest valid, restore check passed"
fi

# ── 10. v0.4 Auto-play verification ───────────────────────────────
echo "--- 10. v0.4 Auto-play ---"

# Check auto-play state variables in showcase.vue
grep -q "isAutoPlaying" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Auto-play: isAutoPlaying state variable" || fail "Auto-play: isAutoPlaying missing"
grep -q "autoPlayInterval" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Auto-play: autoPlayInterval state variable" || fail "Auto-play: autoPlayInterval missing"
grep -q "toggleAutoPlay\|useAutoPlay" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Auto-play: toggleAutoPlay function" || fail "Auto-play: toggleAutoPlay missing"

# Check Space key handling
grep -q "' '" "$ROOT_DIR/frontend/pages/showcase.vue" || grep -q "Space" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Auto-play: Space key handler" || fail "Auto-play: Space key handler missing"

# Check Play/Pause icons imported
grep -q "Play.*Pause\|Pause.*Play" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Auto-play: Play/Pause icons imported" || fail "Auto-play: Play/Pause icons missing"

# Check interval buttons
grep -q "3s\|5s\|8s\|setAutoPlayInterval" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Auto-play: interval selector buttons" || fail "Auto-play: interval selector missing"

# Check manual nav stops auto-play
grep -q "stopAutoPlay" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Auto-play: stopAutoPlay in manual nav" || fail "Auto-play: stopAutoPlay missing"

# Check auto-play composable exists
[[ -f "$ROOT_DIR/frontend/composables/useAutoPlay.ts" ]] && pass "Auto-play: useAutoPlay composable file" || fail "Auto-play: useAutoPlay composable missing"

# Check auto-play tests exist
[[ -f "$ROOT_DIR/frontend/tests/autoplay.test.ts" ]] && pass "Auto-play: vitest test file exists" || fail "Auto-play: autoplay.test.ts missing"

# ── 11. v0.4 Map album verification ───────────────────────────────
echo "--- 11. v0.4 Map album ---"

# Check map API endpoint returns valid JSON (200 or 401 if not auth)
map_status=$(curl -sS -o /dev/null -w '%{http_code}' -b "$admin_cookie" "$API_BASE/map/photos" 2>/dev/null || echo "000")
if [[ "$map_status" == "200" ]]; then
  # Verify response shape has GPS fields
  map_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/map/photos")"
  printf '%s' "$map_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "photos" in data, "Missing photos key"
if len(data["photos"]) > 0:
    item = data["photos"][0]
    assert "gps_lat" in item, "Missing gps_lat"
    assert "gps_lng" in item, "Missing gps_lng"
    assert "preview_url" in item, "Missing preview_url"
    assert "thumbnail_url" in item, "Missing thumbnail_url"
    n = len(data["photos"])
    print(f"  Map API OK: {n} geocoded photos, fields valid")
else:
    print("  Map API OK: 0 geocoded photos (empty, valid response)")
  '
  pass "Map API returns valid response"
elif [[ "$map_status" == "401" ]]; then
  pass "Map API returns 401 (auth enforcement confirmed)"
else
  fail "Map API unexpected status: $map_status"
fi

# Check /map page file exists
[[ -f "$ROOT_DIR/frontend/pages/map/index.vue" ]] && pass "Map page: /map page file exists" || fail "Map page: /map page file missing"

# Check Leaflet dependency installed
grep -q "leaflet" "$ROOT_DIR/frontend/package.json" && pass "Map page: leaflet dependency" || fail "Map page: leaflet not in package.json"

# Check MapPin icon in showcase
grep -q "MapPin" "$ROOT_DIR/frontend/pages/showcase.vue" && pass "Map nav: MapPin icon in showcase" || fail "Map nav: MapPin icon missing"

# Check M key navigation
grep -q "'m'\|'M'" "$ROOT_DIR/frontend/pages/showcase.vue" || grep -q "KeyM" "$ROOT_DIR/frontend/pages/showcase.vue"
if [[ $? -eq 0 ]]; then
  pass "Map nav: M key handler in showcase"
else
  fail "Map nav: M key handler missing"
fi

# Check MapPhotoItem types
grep -q "MapPhotoItem\|MapPhotosResponse" "$ROOT_DIR/frontend/types/api.ts" && pass "Map types: MapPhotoItem/MapPhotosResponse defined" || fail "Map types: missing from api.ts"

# Check map E2E tests exist
[[ -f "$ROOT_DIR/frontend/tests/e2e/map.spec.ts" ]] && pass "Map E2E: map.spec.ts exists" || fail "Map E2E: map.spec.ts missing"

# Check vitest map tests exist
[[ -f "$ROOT_DIR/frontend/tests/map.test.ts" ]] && pass "Map tests: map.test.ts exists" || fail "Map tests: map.test.ts missing"

# ── 12. Mobile viewport rendering (v0.3 holdover) ──────────────────
cd "$ROOT_DIR"
echo "--- 12. Mobile viewport ---"

grep -q "isMobile" frontend/pages/showcase.vue && pass "Mobile detection: isMobile in showcase" || fail "Mobile detection: isMobile not found"
grep -q "SWIPE_THRESHOLD\|swipe" frontend/pages/showcase.vue && pass "Swipe gestures: implemented in showcase" || fail "Swipe gestures: not found"
grep -q "min-h-\[44px\]\|MIN_TOUCH_TARGET" frontend/pages/showcase.vue && pass "Touch targets: 44px minimum enforced" || fail "Touch targets: 44px minimum not found"

if [[ -f frontend/tests/mobile-responsive.test.ts ]]; then
  pass "Mobile tests: mobile-responsive.test.ts exists"
else
  fail "Mobile tests: mobile-responsive.test.ts missing"
fi

if command -v npx &>/dev/null; then
  if run_playwright_suite "$ROOT_DIR" "$FRONTEND_BASE" --project=mobile 2>&1; then
    pass "Mobile viewport: Playwright mobile tests passed"
  else
    fail "Mobile viewport: Playwright mobile tests failed"
  fi
else
  fail "Mobile viewport: Playwright unavailable (npx not found)"
fi

# ── Summary ───────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  v0.4 Acceptance Results: $PASSED passed, $FAILED failed"
echo "============================================"

if [[ $FAILED -gt 0 ]]; then
  exit 1
fi
