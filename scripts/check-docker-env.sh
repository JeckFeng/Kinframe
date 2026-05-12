#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_IMAGE="${BACKEND_IMAGE:-kinframe-backend-env:stage5}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-kinframe-frontend-env:stage5}"

info() {
    printf '[check] %s\n' "$1"
}

require_container_running() {
    local name="$1"
    local state
    state="$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || true)"
    if [[ "$state" != "true" ]]; then
        printf '[error] container is not running: %s\n' "$name" >&2
        return 1
    fi
}

info "validating compose configuration"
docker compose -f docker-compose.infra.yml config >/dev/null

info "checking infrastructure containers"
require_container_running kinframe-postgres
require_container_running kinframe-redis
require_container_running kinframe-minio
docker exec kinframe-postgres pg_isready -U kinframe -d kinframe >/dev/null
docker exec kinframe-redis redis-cli ping | grep -q '^PONG$'
docker exec kinframe-minio sh -c 'test -d /data'

info "building backend dependency image"
docker build --network host \
    --build-arg HTTP_PROXY="${HTTP_PROXY:-}" \
    --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" \
    --build-arg ALL_PROXY="${ALL_PROXY:-}" \
    --build-arg NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}" \
    -t "$BACKEND_IMAGE" ./backend

info "checking backend tools and Python packages"
docker run --rm "$BACKEND_IMAGE" bash -lc '
set -euo pipefail
python --version
uv --version
exiftool -ver
curl --version >/dev/null
uv run python - <<'"'"'PY'"'"'
import alembic
import argon2
import fastapi
import httpx
import minio
from PIL import Image
import psycopg
import pydantic
import pydantic_settings
import pytest
import redis
import sqlalchemy
import uvicorn
print("backend imports ok")
PY
'

info "building frontend dependency image"
docker build --network host \
    --build-arg HTTP_PROXY="${HTTP_PROXY:-}" \
    --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" \
    --build-arg ALL_PROXY="${ALL_PROXY:-}" \
    --build-arg NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}" \
    -t "$FRONTEND_IMAGE" ./frontend

info "checking frontend tools and packages"
docker run --rm "$FRONTEND_IMAGE" bash -lc '
set -euo pipefail
node --version
corepack --version
pnpm --version
pnpm exec nuxi --version
node -e "import(\"vue\").then(() => console.log(\"vue import ok\"))"
'

info "docker environment checks passed"
