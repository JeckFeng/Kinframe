#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Checking v0.1 stage 0 command entrypoints..."
just --list | grep -q '^    accept-v0-1'
just --list | grep -q '^    backup'
just --list | grep -q '^    restore '
just --list | grep -q '^    restore-check'
just --list | grep -q '^    worker'

echo "Checking v0.1 environment template..."
for key in \
  BACKUP_DIR \
  BACKUP_INCLUDE_ENV \
  WORKER_ENABLED \
  WORKER_POLL_INTERVAL_SECONDS \
  PHOTO_JOB_MAX_ATTEMPTS \
  PHOTO_JOB_RETRY_DELAY_SECONDS \
  THUMBNAIL_SIZE_PX \
  PREVIEW_MAX_SIZE_PX \
  HEIC_STRATEGY
do
  grep -q "^${key}=" .env.example
done

echo "Checking v0.1 planning documents..."
grep -q "阶段 0：当前系统重构与 PRD 基线切换" docs/code_plan_min_v0.1.md
grep -q "/showcase" docs/code_plan_min_v0.1.md
grep -q "AI 驱动的家庭影像 PPT 放映" docs/code_plan_min_v0.1.md

echo "Running v0 acceptance as v0.1 baseline..."
scripts/v0-acceptance.sh

echo "Running v0.1 showcase and admin-jobs acceptance..."
API_BASE="${API_BASE:-http://localhost:${FRONTEND_PORT:-3000}/api}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:${FRONTEND_PORT:-3000}}"

# Create admin user and log in first — showcase requires authentication
stamp="$(date +%Y%m%d%H%M%S)"
admin_user="v01_admin_$stamp"
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
    --display-name "V0.1 Admin $stamp" \
    --password "$password"

admin_cookie="$tmp_dir/admin.cookies"
curl -fsS -c "$admin_cookie" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$admin_user\",\"password\":\"$password\"}" \
  "$API_BASE/auth/login" >/dev/null

echo "  Verifying showcase API returns photos with slide designs..."
showcase_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/showcase")"
printf '%s' "$showcase_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert len(data["categories"]) == 3, f"Expected 3 categories, got {len(data['categories'])}"
assert data["categories"][0]["slug"] == "life"
assert data["categories"][1]["slug"] == "photography"
assert data["categories"][2]["slug"] == "pet"
photo_count = len(data["photos"])
assert photo_count > 0, "Showcase has no photos"
for item in data["photos"]:
    assert item["photo"]["status"] == "ready", f"Photo {item['photo']['id']} not ready"
    assert item["preview_url"], f"Photo {item['photo']['id']} missing preview_url"
    assert item["slide_design"], f"Photo {item['photo']['id']} missing slide_design"
    assert item["slide_design"]["templateId"]
    assert len(item["slide_design"]["layers"]) >= 1
print(f"  OK: {photo_count} photos with valid slide designs")
'

echo "  Verifying showcase page loads..."
curl -fsS -b "$admin_cookie" "$FRONTEND_BASE/showcase" >/dev/null

echo "  Verifying admin jobs API..."
jobs_json="$(curl -fsS -b "$admin_cookie" "$API_BASE/admin/jobs")"
printf '%s' "$jobs_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert len(data) > 0, "Admin jobs list is empty"
assert all("photo_id" in j for j in data)
assert all("photo_category" in j for j in data)
assert all("photo_status" in j for j in data)
print(f"  OK: {len(data)} jobs listed")
'

echo "Running v0.1 backup and restore-check acceptance..."
backup_output="$(scripts/backup.sh)"
printf '%s\n' "$backup_output"
backup_dir="$(printf '%s\n' "$backup_output" | awk -F': ' '/Backup completed:/ {print $2}' | tail -n 1)"
if [[ -z "$backup_dir" || ! -s "$backup_dir/manifest.json" ]]; then
  echo "Backup acceptance did not produce a valid manifest." >&2
  exit 1
fi
python3 -c '
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert "slide_design_count" in manifest["postgres"]
assert manifest["postgres"]["slide_design_count"] >= 1
' "$backup_dir/manifest.json"

scripts/restore-check.sh "$backup_dir"

echo "v0.1 PRD baseline acceptance passed"
