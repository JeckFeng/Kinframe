# KinFrame

KinFrame is a private family image showcase. The v0.1 line is being redirected from a traditional gallery MVP toward the latest PRD: an AI-driven, full-screen PPT-style family photo presentation site. The current baseline keeps login, member management, upload, private MinIO storage, EXIF extraction, previews, thumbnails, Worker processing, backup/restore, gallery browsing, and photo detail pages, while making `/showcase` the primary experience.

## v0.1 PRD Baseline Scope

Included:

- Admin login and member account creation.
- Member login and JPEG/PNG/WebP upload.
- Original photo and thumbnail storage in a private MinIO bucket.
- PostgreSQL photo metadata, including category, message, dimensions, upload time, taken time fallback, camera fields, and GPS fields.
- Full-screen `/showcase` entry point after login.
- Hidden showcase top menu and left category rail.
- Default PRD categories: `life`/生活照, `photography`/摄影照, and `pet`/宠物照, with old `travel` data kept compatible.
- Gallery routes for all photos and category browsing as auxiliary pages.
- Photo detail view with original URL, metadata, and editable category/message.
- Basic permission checks for unauthenticated users, members, and admins.

The v0.1 line adds local backup/restore scripts, an asynchronous photo processing worker, preview images, and batch upload. New uploads save the original image first, then Worker processing extracts metadata and generates thumbnails/previews.

Not included yet: real Ollama vision analysis, DeepSeek captions/design JSON, full Slide Renderer, `slide_designs` persistence, Cloudflare Tunnel, HEIC/HEIF conversion on this Docker image, timeline/yearly memory views, map albums, and face recognition.

## v0.1 Backup And Restore

Create a local backup after `just infra` is running:

```bash
just backup
```

Backups are written under `data/backups/YYYYMMDD-HHMMSS/`. Each backup contains PostgreSQL metadata, the private MinIO bucket, selected configuration files, and a `manifest.json` with file sizes and SHA-256 checksums. The local `.env` file is not included by default; set `BACKUP_INCLUDE_ENV=1 just backup` only when you intentionally want secrets copied into the backup.

Run a non-destructive restore rehearsal in isolated temporary containers:

```bash
just restore-check
just restore-check data/backups/20260511-120000
```

Restore into the running local PostgreSQL and MinIO services only when you intend to overwrite data:

```bash
RESTORE_CONFIRM=YES just restore data/backups/20260511-120000
```

Configuration files are saved under the backup `config/` directory but are not copied back automatically during restore.

## Local Startup

Install Docker and `just`, then run these in separate terminals:

```bash
just infra
just backend
just frontend
just worker
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:18000/api/health`
- MinIO console: `http://localhost:19001`
- Caddy placeholder: `http://localhost:18080`

Create a development admin when needed:

```bash
just create-admin admin Administrator password123
```

Build Docker dependency images manually:

```bash
just backend-image
just frontend-image
```

Run one Worker pass for testing:

```bash
WORKER_ARGS=--once just worker
```

## Testing And Acceptance

Run backend tests:

```bash
just test-backend
```

Run the v0 end-to-end acceptance script after `just infra`, `just backend`, and `just frontend` are running:

```bash
just accept-v0
```

The acceptance script creates temporary users, uploads JPEGs without EXIF, runs Worker passes, verifies original/thumbnail/preview MinIO objects and PostgreSQL records, checks `/showcase`, gallery/detail APIs, PRD category compatibility, and presigned URLs, validates batch upload behavior, and validates core permission denials.

Run the v0.1 baseline and backup acceptance:

```bash
just accept-v0-1
```

## Configuration

Copy `.env.example` to `.env` for local overrides. Keep `.env`, `data/`, `frontend/node_modules/`, `frontend/.nuxt/`, `frontend/.output/`, `backend/.venv/`, and cache directories out of version control.

The default ports avoid common local conflicts: PostgreSQL `15432`, Redis `16379`, MinIO API `19000`, backend `18000`, frontend `3000`.

## Common Issues

- If Docker dependency downloads are slow while Clash is enabled, build with `just backend-image` or `just frontend-image`. These recipes use `--network host` and pass `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` so Docker can reach a host proxy such as `127.0.0.1:7897`.
- If port `3000` or `18000` is occupied, set `FRONTEND_PORT` or `BACKEND_PORT` before running `just frontend` or `just backend`.
- If MinIO presigned image URLs do not open in the browser, make sure the backend uses `MINIO_ENDPOINT=localhost:19000` for local development.
