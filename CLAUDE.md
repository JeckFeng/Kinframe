# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

```bash
just infra              # Start PostgreSQL, Redis, MinIO, Caddy
just backend            # FastAPI with hot reload + auto migrations
just frontend           # Nuxt 3 dev server
just worker             # Photo processor polling loop
WORKER_ARGS=--once just worker   # Run one worker pass and exit
just test-backend       # Run pytest in backend/
just accept-v0-1        # E2E acceptance script
just create-admin admin Administrator password123
just backup             # Create local backup under data/backups/
RESTORE_CONFIRM=YES just restore data/backups/<dir>  # Restore from backup
```

All services run in Docker containers with `--network host`. Ports: backend 18000, frontend 3000, PostgreSQL 15432, Redis 16379, MinIO API 19000, MinIO Console 19001, Caddy 18080.

## Architecture

### Backend: FastAPI + SQLAlchemy + MinIO (`backend/`)

Python 3.12, managed with `uv`. The Docker image is `kinframe-backend-env:stage5`.

**Request flow**: FastAPI router → dependency injection (`app/api/deps.py`) → service layer (`app/services/`) → SQLAlchemy models (`app/models/`). Business logic lives in services, not in route handlers.

- `app/main.py` — app factory, registers routers from `app/api/`
- `app/api/deps.py` — FastAPI dependency injection: `DbSession`, `AppSettings`, `get_current_user` (session cookie → user), `get_current_admin`, `get_object_storage`
- `app/core/config.py` — Pydantic `Settings` loaded from `.env`; all config via env vars
- `app/core/security.py` — Argon2 password hashing, HMAC-signed session tokens (base64url-encoded JSON payload with expiry)
- `app/core/database.py` — SQLAlchemy engine + `SessionLocal` + `Base` + `get_db` generator
- `app/services/storage.py` — `ObjectStorage` Protocol implemented by `MinioObjectStorage`; upload/download/presigned URLs (900s default)
- `app/services/images.py` — Pillow-based thumbnail (512px WebP, quality 82) and preview (2048px WebP, quality 88) generation; HEIC support via optional `pillow_heif`
- `app/services/exif.py` — external `exiftool` subprocess for EXIF extraction with timestamp/GPS/camera parsing
- `app/services/photo_jobs.py` — job queue: `create_photo_with_processing_job`, `claim_next_pending_job` (SELECT FOR UPDATE SKIP LOCKED), `mark_job_succeeded`/`failed`, `process_next_photo_job`
- `app/workers/photo_processor.py` — CLI entry: `--once` for one-shot, polling loop by default
- `app/models/` — SQLAlchemy ORM: `User` (admin/member roles), `Photo` (with status machine: processing→ready/failed), `PhotoProcessingJob`, `Category`, `SlideDesign`
- `migrations/` — Alembic, auto-applied on `just backend` startup

**Upload flow**: multipart POST → sha256 dedup → store original in MinIO → create Photo + PhotoProcessingJob in one transaction → return 201 with status "processing". Worker picks up the job, extracts EXIF, generates thumbnail + preview, builds fallback slide design, marks photo ready.

**Auth**: cookie-based sessions. `POST /api/auth/login` sets `kinframe_session` cookie (HttpOnly, SameSite Lax). `useApi` composable forwards cookies server-side and auto-redirects to `/login` on 401 client-side.

### Frontend: Nuxt 3 + Vue 3 + Tailwind CSS (`frontend/`)

Package manager: `pnpm@9.15.4`. The Docker image is `kinframe-frontend-env:stage5`.

- `nuxt.config.ts` — Nitro proxies `/api/**` to `KINFRAME_API_PROXY` (default `http://127.0.0.1:18000`)
- `composables/useAuth.ts` — `currentUser` stored in Nuxt `useState`, shared across pages; `loadMe()` fetches `/api/auth/me`
- `composables/useApi.ts` — `apiFetch<T>()` wraps `$fetch` with base URL, cookie forwarding (SSR), and 401→`/login` redirect
- `pages/showcase.vue` — primary UX: full-screen slideshow with category rail (life/photography/pet), arrow key navigation, `C` toggles category sidebar
- `pages/upload.vue` — single + batch upload (max 10 files)
- `pages/gallery/` — auxiliary browsing views
- `pages/photo/[id].vue` — detail page with editable category/message
- `types/api.ts` — shared TypeScript types matching backend Pydantic schemas

### Infrastructure

- `docker-compose.infra.yml` — PostgreSQL 16, Redis 7, MinIO, Caddy; persistent data in `data/` (not committed)
- `deploy/caddy/` — Caddyfile for reverse proxy
- `scripts/` — backup/restore (PostgreSQL pg_dump, MinIO mc mirror, SHA-256 manifests), acceptance test scripts
- `justfile` — task runner wrapping all Docker and test commands

## Key Conventions

- Photo categories: `life` (生活照), `photography` (摄影照), `pet` (宠物照); legacy `travel` data mapped to photography in showcase
- Photo object keys: `originals/{year}/{month}/{photo_id}{ext}`, `thumbnails/{year}/{month}/{photo_id}_512.webp`, `previews/{year}/{month}/{photo_id}.webp`
- Photo status machine: `processing` → `ready` | `failed`; only `ready` photos appear in showcase
- MinIO bucket is private; images served via short-lived presigned URLs
- Session tokens: `base64url(payload).base64url(HMAC-SHA256)` with expiry check
- Proxy builds: `just backend-image` and `just frontend-image` use `--network host` with `HTTP_PROXY`/`HTTPS_PROXY` for Docker behind a proxy like Clash
