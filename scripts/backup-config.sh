#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

backup_dir="${1:-}"
if [[ -z "$backup_dir" ]]; then
  echo "Usage: scripts/backup-config.sh <backup-dir>" >&2
  exit 2
fi

BACKUP_INCLUDE_ENV="${BACKUP_INCLUDE_ENV:-0}"

config_dir="$backup_dir/config"
metadata_file="$config_dir/metadata.env"
mkdir -p "$config_dir"

cp .env.example "$config_dir/.env.example"
cp justfile "$config_dir/justfile"
cp docker-compose*.yml "$config_dir/"
cp -a deploy "$config_dir/deploy"

contains_env="0"
if [[ "$BACKUP_INCLUDE_ENV" == "1" ]]; then
  if [[ -f .env ]]; then
    cp .env "$config_dir/.env"
    contains_env="1"
  else
    echo "BACKUP_INCLUDE_ENV=1 was set, but .env does not exist; continuing without .env."
  fi
fi

{
  printf 'CONFIG_CONTAINS_ENV=%s\n' "$contains_env"
  printf 'CONFIG_BACKUP_DIR=%s\n' "config"
} > "$metadata_file"

printf 'Config backup written: %s\n' "$config_dir"
