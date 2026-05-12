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
