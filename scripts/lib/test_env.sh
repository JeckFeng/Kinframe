#!/usr/bin/env bash

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

ensure_docker_access() {
  require_command docker
  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not accessible. Start Docker and ensure your user can access docker.sock." >&2
    exit 1
  fi
}

wait_for_postgres() {
  for _ in $(seq 1 15); do
    if docker exec kinframe-postgres pg_isready -U kinframe -d kinframe >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  echo "PostgreSQL did not become ready in time." >&2
  exit 1
}

ensure_infra_running() {
  ensure_docker_access
  require_command just

  local needs_start=0
  for svc in kinframe-postgres kinframe-redis kinframe-minio; do
    if [[ "$(docker inspect -f '{{.State.Running}}' "$svc" 2>/dev/null || true)" != "true" ]]; then
      needs_start=1
      break
    fi
  done

  if [[ "$needs_start" -eq 1 ]]; then
    echo "Starting Docker infra..."
    just infra
    echo "Waiting for PostgreSQL..."
    wait_for_postgres
  fi
}

ensure_backend_running() {
  local api_base="$1"

  require_command curl
  if ! curl -fsS -o /dev/null -w '%{http_code}' "$api_base/health" 2>/dev/null | grep -q 200; then
    echo "Backend API is not reachable at $api_base. Start it with just backend." >&2
    exit 1
  fi
}

run_playwright_suite() {
  local root_dir="$1"
  local frontend_base="$2"
  shift 2

  (
    cd "$root_dir/frontend"
    PLAYWRIGHT_BASE_URL="$frontend_base" npx playwright test --config playwright.config.ts "$@"
  )
}
