#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

expected_owner="$(id -u):$(id -g)"

scripts/frontend-docker.sh build

bad_paths=()
for path in frontend/.nuxt frontend/.output frontend/.pnpm-store frontend/.docker-build; do
  if [[ -e "$path" ]]; then
    owner="$(stat -c "%u:%g" "$path")"
    if [[ "$owner" != "$expected_owner" ]]; then
      bad_paths+=("$owner $path")
    fi
  fi
done

for path in frontend/backend frontend/frontend; do
  if [[ -e "$path" ]]; then
    bad_paths+=("unexpected $path")
  fi
done

if (( ${#bad_paths[@]} > 0 )); then
  printf 'Frontend Docker permission check failed:\n' >&2
  printf '  %s\n' "${bad_paths[@]}" >&2
  exit 1
fi

echo "Frontend Docker permission check passed"
