#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

IMAGE="${FRONTEND_IMAGE:-kinframe-frontend-env:stage5}"
VOLUME_PREFIX="${KINFRAME_FRONTEND_VOLUME_PREFIX:-kinframe_frontend_stage5}"
RUN_UID="${KINFRAME_DOCKER_UID:-$(id -u)}"
RUN_GID="${KINFRAME_DOCKER_GID:-$(id -g)}"

usage() {
  cat <<'USAGE'
Usage: scripts/frontend-docker.sh <command>

Commands:
  dev       Run Nuxt dev server
  build     Run pnpm build
  test      Run pnpm test
  install   Run pnpm install --frozen-lockfile
  shell     Open a shell in the frontend container
  <other>   Run a custom shell command in /app
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

command_name="$1"
shift || true

case "$command_name" in
  dev)
    inner_command='pnpm dev --host 0.0.0.0 --port "$FRONTEND_PORT"'
    run_install="${KINFRAME_FRONTEND_RUN_INSTALL:-1}"
    ;;
  build)
    inner_command='pnpm build'
    run_install="${KINFRAME_FRONTEND_RUN_INSTALL:-1}"
    ;;
  test)
    inner_command='pnpm test'
    run_install="${KINFRAME_FRONTEND_RUN_INSTALL:-1}"
    ;;
  install)
    inner_command='pnpm install --frozen-lockfile'
    run_install=0
    ;;
  shell)
    inner_command='exec bash'
    run_install=0
    ;;
  *)
    inner_command="$command_name"
    if [[ $# -gt 0 ]]; then
      inner_command+=" $*"
    fi
    run_install="${KINFRAME_FRONTEND_RUN_INSTALL:-0}"
    ;;
esac

init_frontend_volumes() {
  docker run --rm \
    -v "${VOLUME_PREFIX}_node_modules:/app/node_modules" \
    -v "${VOLUME_PREFIX}_build:/app/.docker-build" \
    -v "${VOLUME_PREFIX}_pnpm_store:/tmp/kinframe-pnpm-store" \
    "$IMAGE" \
    bash -lc '
      set -euo pipefail
      uid="$1"
      gid="$2"
      for path in /app/node_modules /app/.docker-build /tmp/kinframe-pnpm-store; do
        mkdir -p "$path"
        current="$(stat -c "%u:%g" "$path")"
        if [[ "$current" != "$uid:$gid" ]]; then
          chown -R "$uid:$gid" "$path"
        fi
      done
    ' bash "$RUN_UID" "$RUN_GID"
}

init_frontend_volumes

mkdir -p "$FRONTEND_DIR/node_modules" "$FRONTEND_DIR/.docker-build"

docker run --rm --network host \
  --user "$RUN_UID:$RUN_GID" \
  -e CI=1 \
  -e HOME=/tmp/kinframe-home \
  -e COREPACK_HOME=/tmp/kinframe-corepack \
  -e XDG_CACHE_HOME=/tmp/kinframe-cache \
  -e NPM_CONFIG_CACHE=/tmp/kinframe-npm-cache \
  -e NPM_CONFIG_STORE_DIR=/tmp/kinframe-pnpm-store \
  -e npm_config_store_dir=/tmp/kinframe-pnpm-store \
  -e NUXT_BUILD_DIR=/app/.docker-build/.nuxt \
  -e NITRO_OUTPUT_DIR=/app/.docker-build/.output \
  -e KINFRAME_API_PROXY="${KINFRAME_API_PROXY:-http://127.0.0.1:${BACKEND_PORT:-18000}}" \
  -e FRONTEND_PORT="${FRONTEND_PORT:-3000}" \
  -e KINFRAME_FRONTEND_INNER_COMMAND="$inner_command" \
  -e KINFRAME_FRONTEND_RUN_INSTALL="$run_install" \
  -v "$FRONTEND_DIR:/app" \
  -v "${VOLUME_PREFIX}_node_modules:/app/node_modules" \
  -v "${VOLUME_PREFIX}_build:/app/.docker-build" \
  -v "${VOLUME_PREFIX}_pnpm_store:/tmp/kinframe-pnpm-store" \
  "$IMAGE" \
  bash -lc '
    set -euo pipefail
    mkdir -p "$HOME" "$COREPACK_HOME" "$XDG_CACHE_HOME" "$NPM_CONFIG_CACHE" "$NPM_CONFIG_STORE_DIR"
    if [[ "${KINFRAME_FRONTEND_RUN_INSTALL:-0}" == "1" ]]; then
      pnpm install --frozen-lockfile
    fi
    exec bash -lc "$KINFRAME_FRONTEND_INNER_COMMAND"
  '
