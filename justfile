set dotenv-load := true
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

infra:
    POSTGRES_PORT="${POSTGRES_PORT:-15432}" REDIS_PORT="${REDIS_PORT:-16379}" MINIO_API_PORT="${MINIO_API_PORT:-19000}" MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-19001}" CADDY_HTTP_PORT="${CADDY_HTTP_PORT:-18080}" docker compose -f docker-compose.infra.yml up -d

infra-down:
    docker compose -f docker-compose.infra.yml down

backend-image:
    docker build --network host --build-arg HTTP_PROXY="${HTTP_PROXY:-}" --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" --build-arg ALL_PROXY="${ALL_PROXY:-}" --build-arg NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}" -t kinframe-backend-env:stage5 ./backend

frontend-image:
    docker build --network host --build-arg HTTP_PROXY="${HTTP_PROXY:-}" --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" --build-arg ALL_PROXY="${ALL_PROXY:-}" --build-arg NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}" -t kinframe-frontend-env:stage5 ./frontend

backend:
    #!/usr/bin/env bash
    set -euo pipefail
    docker run --rm --network host \
      -e APP_ENV="${APP_ENV:-development}" \
      -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
      -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
      -e REDIS_URL="${REDIS_URL:-redis://localhost:16379/0}" \
      -e MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:19000}" \
      -e MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}" \
      -e MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}" \
      -e MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}" \
      -e BACKEND_PORT="${BACKEND_PORT:-18000}" \
      -e BACKUP_DIR="${BACKUP_DIR:-data/backups}" \
      -e BACKUP_INCLUDE_ENV="${BACKUP_INCLUDE_ENV:-0}" \
      -e WORKER_ENABLED="${WORKER_ENABLED:-1}" \
      -e WORKER_POLL_INTERVAL_SECONDS="${WORKER_POLL_INTERVAL_SECONDS:-5}" \
      -e PHOTO_JOB_MAX_ATTEMPTS="${PHOTO_JOB_MAX_ATTEMPTS:-3}" \
      -e PHOTO_JOB_RETRY_DELAY_SECONDS="${PHOTO_JOB_RETRY_DELAY_SECONDS:-30}" \
      -e THUMBNAIL_SIZE_PX="${THUMBNAIL_SIZE_PX:-512}" \
      -e PREVIEW_MAX_SIZE_PX="${PREVIEW_MAX_SIZE_PX:-2048}" \
      -e HEIC_STRATEGY="${HEIC_STRATEGY:-reject}" \
      -e GEOCODING_ENABLED="${GEOCODING_ENABLED:-false}" \
      -e GEOCODING_PROVIDER="${GEOCODING_PROVIDER:-nominatim}" \
      -e NOMINATIM_ENDPOINT="${NOMINATIM_ENDPOINT:-https://nominatim.openstreetmap.org}" \
      -e AMAP_API_KEY="${AMAP_API_KEY:-}" \
      -e GEOCODING_TIMEOUT_SECONDS="${GEOCODING_TIMEOUT_SECONDS:-30}" \
      -e GEOCODING_MAX_RETRIES="${GEOCODING_MAX_RETRIES:-2}" \
      -e GEOCODING_RATE_LIMIT_PER_SECOND="${GEOCODING_RATE_LIMIT_PER_SECOND:-1.0}" \
      -v "$PWD/backend:/app" \
      -v /app/.venv \
      kinframe-backend-env:stage5 \
      bash -lc 'uv run alembic upgrade head && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"'

frontend:
    #!/usr/bin/env bash
    set -euo pipefail
    scripts/frontend-docker.sh dev

frontend-build:
    scripts/frontend-docker.sh build

test-frontend:
    scripts/frontend-docker.sh test

frontend-shell:
    scripts/frontend-docker.sh shell

check-frontend-permissions:
    scripts/check-frontend-docker-permissions.sh

create-admin username="admin" display_name="Administrator" password="password123":
    docker run --rm --network host -e APP_ENV="${APP_ENV:-development}" -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" -v "$PWD/backend:/app" -v /app/.venv kinframe-backend-env:stage5 uv run python scripts/create_admin.py --username "{{username}}" --display-name "{{display_name}}" --password "{{password}}" --role admin

create-user username="member" display_name="Member" password="password123":
    docker run --rm --network host -e APP_ENV="${APP_ENV:-development}" -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" -v "$PWD/backend:/app" -v /app/.venv kinframe-backend-env:stage5 uv run python scripts/create_admin.py --username "{{username}}" --display-name "{{display_name}}" --password "{{password}}" --role member

worker:
    #!/usr/bin/env bash
    set -euo pipefail
    docker run --rm --network host \
      -e APP_ENV="${APP_ENV:-development}" \
      -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
      -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
      -e REDIS_URL="${REDIS_URL:-redis://localhost:16379/0}" \
      -e MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:19000}" \
      -e MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}" \
      -e MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}" \
      -e MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}" \
      -e BACKUP_DIR="${BACKUP_DIR:-data/backups}" \
      -e BACKUP_INCLUDE_ENV="${BACKUP_INCLUDE_ENV:-0}" \
      -e WORKER_ENABLED="${WORKER_ENABLED:-1}" \
      -e WORKER_POLL_INTERVAL_SECONDS="${WORKER_POLL_INTERVAL_SECONDS:-5}" \
      -e PHOTO_JOB_MAX_ATTEMPTS="${PHOTO_JOB_MAX_ATTEMPTS:-3}" \
      -e PHOTO_JOB_RETRY_DELAY_SECONDS="${PHOTO_JOB_RETRY_DELAY_SECONDS:-30}" \
      -e THUMBNAIL_SIZE_PX="${THUMBNAIL_SIZE_PX:-512}" \
      -e PREVIEW_MAX_SIZE_PX="${PREVIEW_MAX_SIZE_PX:-2048}" \
      -e HEIC_STRATEGY="${HEIC_STRATEGY:-reject}" \
      -e GEOCODING_ENABLED="${GEOCODING_ENABLED:-false}" \
      -e GEOCODING_PROVIDER="${GEOCODING_PROVIDER:-nominatim}" \
      -e NOMINATIM_ENDPOINT="${NOMINATIM_ENDPOINT:-https://nominatim.openstreetmap.org}" \
      -e AMAP_API_KEY="${AMAP_API_KEY:-}" \
      -e GEOCODING_TIMEOUT_SECONDS="${GEOCODING_TIMEOUT_SECONDS:-30}" \
      -e GEOCODING_MAX_RETRIES="${GEOCODING_MAX_RETRIES:-2}" \
      -e GEOCODING_RATE_LIMIT_PER_SECOND="${GEOCODING_RATE_LIMIT_PER_SECOND:-1.0}" \
      -e WORKER_ARGS="${WORKER_ARGS:-}" \
      -v "$PWD/backend:/app" \
      -v /app/.venv \
      kinframe-backend-env:stage5 \
      bash -lc 'uv run alembic upgrade head && uv run python -m app.workers.photo_processor ${WORKER_ARGS:-}'

backfill-postprocessing:
    #!/usr/bin/env bash
    set -euo pipefail
    docker run --rm --network host \
      -e APP_ENV="${APP_ENV:-development}" \
      -e APP_SECRET_KEY="${APP_SECRET_KEY:-change-me}" \
      -e DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://kinframe:change-me@localhost:15432/kinframe}" \
      -e REDIS_URL="${REDIS_URL:-redis://localhost:16379/0}" \
      -e MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:19000}" \
      -e MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-kinframe}" \
      -e MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-change-me}" \
      -e MINIO_BUCKET="${MINIO_BUCKET:-kinframe-photos}" \
      -e GEOCODING_ENABLED="${GEOCODING_ENABLED:-false}" \
      -e GEOCODING_PROVIDER="${GEOCODING_PROVIDER:-nominatim}" \
      -e NOMINATIM_ENDPOINT="${NOMINATIM_ENDPOINT:-https://nominatim.openstreetmap.org}" \
      -e AMAP_API_KEY="${AMAP_API_KEY:-}" \
      -e GEOCODING_TIMEOUT_SECONDS="${GEOCODING_TIMEOUT_SECONDS:-30}" \
      -e GEOCODING_MAX_RETRIES="${GEOCODING_MAX_RETRIES:-2}" \
      -e GEOCODING_RATE_LIMIT_PER_SECOND="${GEOCODING_RATE_LIMIT_PER_SECOND:-1.0}" \
      -v "$PWD/backend:/app" \
      -v /app/.venv \
      kinframe-backend-env:stage5 \
      bash -lc 'uv run alembic upgrade head && uv run python scripts/backfill_photo_postprocessing.py'

dev:
    just infra
    @echo "Start backend and frontend in separate terminals:"
    @echo "  just backend"
    @echo "  just frontend"

test-backend:
    cd backend && uv run pytest

accept-v0:
    scripts/v0-acceptance.sh

accept-v0-1:
    scripts/v0.1-acceptance.sh

accept-v0-2:
    scripts/v0.2-acceptance.sh

accept-v0-3:
    scripts/v0.3-acceptance.sh

accept-v0-4:
    scripts/v0.4-acceptance.sh

accept-v0-5-delete:
    scripts/v0.5-delete-acceptance.sh

test-e2e:
    scripts/e2e-setup.sh
    cd frontend && npx playwright test --config playwright.config.ts

backup:
    scripts/backup.sh

restore backup_dir:
    RESTORE_CONFIRM="${RESTORE_CONFIRM:-}" scripts/restore.sh "{{backup_dir}}"

restore-check backup_dir="":
    scripts/restore-check.sh "{{backup_dir}}"
