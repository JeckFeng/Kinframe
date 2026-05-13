# KinFrame

KinFrame is a private family photo PPT playback system. v0.2 completes the PRD closed loop: upload → EXIF parsing → geocoding → AI analysis → slide design generation → full-screen `/showcase` playback with keyboard and mouse navigation. AI is optional — the system always falls back to deterministic fallback designs.

## v0.2 What's New

**Navigation**: Mouse left-click (next photo), right-click (previous photo), scroll wheel (switch categories) alongside existing keyboard arrows.

**Reverse Geocoding**: Photos with GPS coordinates are asynchronously geocoded to location text (city, region, country, district, road). Defaults to OpenStreetMap Nominatim; Amap (高德) also supported. Disabled by default for offline development.

**AI Integration** (optional, off by default): 
- **Ollama** for local vision analysis (caption + category suggestions).
- **DeepSeek** for AI-generated slide designs.
- When AI is disabled or unavailable, the system falls back to deterministic designs.

**Slide Renderer v0.2**: New Background, Mask, and Shape layers. CSS token hardening blocks layout-breaking properties. Validator enforces text length (≤200 chars), fontSize (≤120px), and rect bounds.

**Admin Console** (`/admin/*`):
- **Photo Diagnostics**: View EXIF, AI analysis JSON, geocoding status. Manually override caption and 6 location fields. Reset caption to auto-compute. Regenerate slide design on demand.
- **Category Management**: Create categories, edit display fields, toggle active/inactive, reorder sort. Slug is immutable after creation.
- **Audit Logs**: All admin modifications recorded with before/after values, filterable by admin, action, target type, and date range.
- **Job Management**: View all processing jobs with retry capability, including new `reverse_geocode` and `vision_analyze` job types.

**Data Model**:
- `final_caption` materialized column with `caption_source` tracking (admin/user/ai/none). Admin overrides take priority; reset-caption restores auto-computation.
- `audit_logs` table records all admin actions with before/after/changed_fields JSON.
- Category schema extended with `is_active`, `sort_order`, `legacy_slug`.

## v0.1 Baseline

Included from v0.1:

- Admin login, member account creation, and session-based auth.
- JPEG / PNG / WebP upload (single and batch, max 10).
- Private MinIO storage for originals, thumbnails, and preview WebP.
- PostgreSQL metadata with EXIF extraction (camera, GPS, timestamps).
- Asynchronous photo processing Worker (EXIF → thumbnail → preview → slide design).
- Three default categories: `life` (生活照), `photography` (摄影照), `pet` (宠物照).
- Full-screen `/showcase` page with hidden top menu, hidden left category rail, and bottom info bar.
- Gallery and photo detail pages as auxiliary browsing views.
- Local backup / restore scripts with SHA-256 manifests and restore rehearsal.

## Local Startup

Install Docker and `just`, then run these in separate terminals:

```bash
just infra              # PostgreSQL, Redis, MinIO, Caddy
just backend            # FastAPI with hot reload + auto migrations
just frontend           # Nuxt 3 dev server
just worker             # Photo processor polling loop (optional — backend starts an embedded worker by default)
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:18000/api/health`
- MinIO console: `http://localhost:19001`

Create a development admin:

```bash
just create-admin admin Administrator password123
```

Build Docker dependency images (first time or after dependency changes):

```bash
just backend-image
just frontend-image
```

Frontend Docker commands keep generated Nuxt output and pnpm data in Docker volumes, not in the host source tree:

```bash
just frontend-build
just test-frontend
just check-frontend-permissions
```

This avoids root-owned `.nuxt/`, `.output/`, and `.pnpm-store/` files when the frontend directory is bind-mounted into Docker.

## Testing And Acceptance

Run backend tests:

```bash
just test-backend
```

Run the full v0.2 acceptance suite (requires `just infra`, `just backend`, and `just frontend` running):

```bash
just accept-v0-2
```

The v0.2 acceptance script:

1. Starts Docker infra if needed.
2. Creates admin and member test users, logs in with cookies.
3. Uploads 3 test photos (life, pet, photography).
4. Runs Worker in `--once` mode to process all jobs.
5. Verifies showcase API returns photos with valid slide designs and presigned preview URLs.
6. Verifies admin vs user visibility boundaries (sensitive fields absent from public API).
7. Verifies admin jobs list includes `photo_ingest`, `slide_design_generate`, etc.
8. Verifies admin categories CRUD.
9. Verifies admin audit logs are produced and non-admin access is blocked.
10. Runs backup and restore rehearsal, asserting all table counts match.
11. Verifies mouse navigation code (left-click, right-click, wheel handlers) present in showcase.
12. Verifies admin can modify location/caption and reset caption.

Run one Worker pass for testing:

```bash
WORKER_ARGS=--once just worker
```

## Photo Processing Pipeline

Each uploaded photo goes through:

```
uploaded → processing → exif_parsed → preview_generated → vision_analyzed → geocoded → design_generated → ready
```

- **exif_parsed**: ExifTool extracted camera make/model, GPS, taken_at.
- **preview_generated**: 2048px WebP preview + 512px WebP thumbnail uploaded to MinIO.
- **vision_analyzed**: AI vision model (Ollama) generates caption and category suggestions (skipped if AI is disabled).
- **geocoded**: GPS coordinates reverse-geocoded to location text via Nominatim or Amap (skipped if geocoding is disabled or no GPS).
- **design_generated**: Slide design created (AI-generated via DeepSeek, or deterministic fallback).
- **ready**: Photo appears in `/showcase` playback.

Failed jobs can be retried from `/admin/jobs`.

## `/showcase` Navigation

| Action | Behavior |
|--------|----------|
| Left Arrow / Left Click | Previous photo |
| Right Arrow / Right Click | Next photo |
| Scroll Wheel Up/Down | Switch category (life ↔ photography ↔ pet) |
| `C` key | Toggle category sidebar |
| `F` key | Toggle fullscreen |
| `?` key | Show/hide keyboard shortcuts overlay |

Right-click context menu is prevented on the showcase to avoid accidental browser menus.

## Configuration

Copy `.env.example` to `.env` for local overrides. Default ports: PostgreSQL `15432`, Redis `16379`, MinIO API `19000`, backend `18000`, frontend `3000`.

### Geocoding

```bash
# Enable reverse geocoding (default: false)
GEOCODING_ENABLED=true

# Provider: nominatim (OpenStreetMap, free, rate-limited) or amap (高德, requires API key)
GEOCODING_PROVIDER=nominatim

# Nominatim endpoint (default: OpenStreetMap public)
NOMINATIM_ENDPOINT=https://nominatim.openstreetmap.org

# Amap API key (required only if GEOCODING_PROVIDER=amap)
AMAP_API_KEY=your_amap_key

# Rate limiting and retry
GEOCODING_TIMEOUT_SECONDS=30
GEOCODING_MAX_RETRIES=2
GEOCODING_RATE_LIMIT_PER_SECOND=1.0
```

When `GEOCODING_ENABLED=false`, photos without GPS are processed normally; photos with GPS skip geocoding but still appear in showcase.

### AI Configuration

AI is **disabled by default**. The system works fully without any AI service.

**Ollama (local vision analysis)**:

```bash
AI_ENABLED=true
OLLAMA_ENDPOINT=http://host.docker.internal:11434
OLLAMA_VISION_MODEL=llava:13b
```

**DeepSeek (AI slide design generation)**:

```bash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=sk-your-key
DEEPSEEK_MODEL=deepseek-chat
AI_REQUEST_TIMEOUT_SECONDS=500
AI_MAX_RETRIES=1
```

**Important**: Never commit real API keys. `.env.example` only contains placeholder values. If a key has been committed to Git history, rotate it immediately.

When AI is disabled or unavailable:
- Caption falls back to `user_message` (upload form) or empty.
- Category falls back to user selection on upload.
- Slide design falls back to deterministic templates based on photo orientation and category.

## Backup And Restore

```bash
just backup                                    # Create backup under data/backups/<timestamp>/
just restore-check                             # Non-destructive rehearsal
RESTORE_CONFIRM=YES just restore data/backups/<dir>  # Restore into running services
```

The backup includes PostgreSQL (users, photos, slide_designs, categories, audit_logs, processing_jobs), MinIO objects, and optionally config. The manifest records all table counts and file SHA-256 hashes. Restore rehearsal spins up isolated PostgreSQL and MinIO containers to verify dump integrity without touching running services.

## Troubleshooting

**Docker image build fails with EOF / timeout**: Proxy or network issue. Ensure `HTTP_PROXY`/`HTTPS_PROXY` are set if behind a proxy (e.g., Clash). The `just backend-image` and `just frontend-image` recipes already forward these env vars.

**Backend can't connect to PostgreSQL**: Ensure `just infra` is running. Check `docker ps | grep kinframe-postgres`. Default port is `15432`.

**Geocoding returns no results or timeouts**: Nominatim has a 1 req/s rate limit. Geocoding is async and will retry up to `GEOCODING_MAX_RETRIES` times. Failed geocoding does not block photo processing.

**AI requests timeout**: DeepSeek/Ollama may take 30-120+ seconds. Increase `AI_REQUEST_TIMEOUT_SECONDS` (default 500s). AI failures fall back to deterministic designs — the photo will still appear in showcase.

**Right-click doesn't show browser context menu**: This is intentional — the showcase page prevents default context menu to avoid accidental interruptions during playback. Use browser menu bar or keyboard shortcuts for browser actions.

**Scroll wheel changes categories too fast**: The showcase debounces wheel events. Rapid scrolling may skip categories — scroll deliberately one notch at a time.

**Frontend build produces root-owned files**: Use `just frontend-build` and `just test-frontend` which run in Docker with proper volume mounts. Never run `pnpm install` inside a root container with a bind mount. See `just check-frontend-permissions`.

**Uploaded photos stuck in "processing"**: Check Worker logs for errors. Run `WORKER_ARGS=--once just worker` to process one batch. Check `/admin/jobs` for failed jobs with error messages. Retry from the UI if needed.

## Architecture

```
backend/  FastAPI + SQLAlchemy + MinIO (Python 3.12, uv)
frontend/ Nuxt 3 + Vue 3 + Tailwind CSS (pnpm)
```

Services run inside Docker containers with `--network host`.
