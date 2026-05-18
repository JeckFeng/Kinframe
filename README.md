# KinFrame

KinFrame is a private family photo PPT playback system. v0.4 adds auto-play with configurable intervals and a map album page showing geocoded photos on a China map. v0.3 upgraded the visual quality to a photography-portfolio-grade immersive experience with 8 slide templates, Fill/Shadow structured models, Texture/Vignette atmosphere layers, design presets, Scoped CSS, and comprehensive test coverage including Playwright E2E. All photo rendering now relies on deterministic fallback designs plus optional manual admin edits.

## v0.4 What's New

**Auto-play System**: Press Space to start/stop automatic photo playback within the current category. Configure playback interval (3s / 5s / 8s) from the top menu bar. Play/Pause icon shows current state. A subtle progress indicator appears during playback, auto-hiding after 2 seconds of mouse inactivity. Any manual navigation (arrow keys, mouse clicks, scroll wheel, touch swipe) automatically stops auto-play — manual control always takes precedence.

**Map Album** (`/map`): View geocoded photos on a full-viewport China map powered by Leaflet. Photos appear as circular thumbnail markers at their GPS coordinates. Click any marker to see the photo thumbnail, caption, location, and date in a popup; click "查看照片" to navigate to the full photo detail page. Filter markers by category (全部 / 生活 / 摄影 / 萌宠). Reach the map page from the showcase top menu (MapPin icon) or press `M`.

**Navigation**: Press `M` on showcase to navigate to the map album. The top menu bar now includes a MapPin icon link. Space bar toggles auto-play.

## v0.3 What's New

**Visual System Upgrade**: 8 slide templates (up from 3) with cinematic, magazine, gallery, and portrait styles. Structured Fill model (solid, linearGradient, radialGradient, imageBlur, noise) and Shadow model (soft, dramatic, glow, inner). Design presets system with `presetRef` for reusable visual configurations. Texture and Vignette atmosphere layers for depth and mood.

**Viewing Experience**: Image preloading for <300ms perceived switch latency. Slide transition animations (fade, slide, zoom). Empty category states with upload prompts. Mobile responsive design with touch swipe gestures (50px threshold), 44px minimum touch targets, and 16:9 aspect ratio scaling with letterboxing.

**User Features**: Photo owners can edit their own photo messages inline. Admins can reset any photo back to a deterministic fallback design and manually manage design versions. All admin modifications are audit-logged with before/after values.

**Engineering Quality**: Frontend and backend share a single JSON Schema source of truth for slide design validation. Playwright E2E tests cover 10+ core user scenarios. v0.3 acceptance script provides 10-step end-to-end verification.

## v0.2 What's New

**Navigation**: Mouse left-click (next photo), right-click (previous photo), scroll wheel (switch categories) alongside existing keyboard arrows.

**Reverse Geocoding**: Photos with GPS coordinates are asynchronously geocoded to location text (city, region, country, district, road). Defaults to OpenStreetMap Nominatim; Amap (高德) also supported. Disabled by default for offline development.

**Slide Renderer v0.2**: New Background, Mask, and Shape layers. CSS token hardening blocks layout-breaking properties. Validator enforces text length (≤200 chars), fontSize (≤120px), and rect bounds.

**Admin Console** (`/admin/*`):
- **Photo Diagnostics**: View EXIF and geocoding status. Manually override caption and 6 location fields. Reset caption to auto-compute. Regenerate deterministic fallback slide design on demand.
- **Category Management**: Create categories, edit display fields, toggle active/inactive, reorder sort. Slug is immutable after creation.
- **Audit Logs**: All admin modifications recorded with before/after values, filterable by admin, action, target type, and date range.
- **Job Management**: View all processing jobs with retry capability, including `photo_ingest`, `reverse_geocode`, `fallback_regenerate`, and `photo_purge`.

**Data Model**:
- `final_caption` materialized column with `caption_source` tracking (admin/user/none). Admin overrides take priority; reset-caption restores auto-computation.
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
just worker             # Photo processor polling loop
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

Run frontend unit tests:

```bash
just test-frontend
```

Run Playwright E2E tests (requires Docker infra plus a reachable backend API; Playwright will start the frontend dev server automatically):

```bash
just test-e2e
```

The `just test-e2e` recipe seeds test data against `http://localhost:18000/api`, then runs Playwright in headless mode. Playwright starts the Nuxt dev server automatically, so you do not need a separate `just frontend` terminal for E2E runs. Failed tests produce screenshots for debugging.

Run the full v0.4 acceptance suite (requires Docker infra and a reachable backend API; Playwright will start the frontend when needed):

```bash
just accept-v0-4
```

Run the v0.3 acceptance suite:

```bash
just accept-v0-3
```

Run the v0.2 acceptance suite:

```bash
just accept-v0-2
```

### Playwright Setup

Playwright must be installed on the host machine (not inside Docker):

```bash
npx playwright install chromium
```

The E2E tests run against the local frontend dev server (`localhost:3000`) and proxy API traffic to the backend (`localhost:18000` by default). Tests are configured in `frontend/playwright.config.ts` with desktop (1280x720) and mobile (390x844) Chromium profiles.

Acceptance and E2E prerequisites:

- Docker daemon must be reachable by the current user.
- Backend API must be reachable at `http://localhost:18000/api` unless `API_BASE` overrides it.
- Frontend dev server does not need to be started manually for Playwright; the runner will launch it.
- If your backend is not on `localhost:18000`, set `KINFRAME_API_PROXY` for Nuxt and `API_BASE` for the scripts.

The v0.4 acceptance script:

1. Starts Docker infra if needed, verifies PostgreSQL/Redis/MinIO running.
2. Creates admin and member test users, logs in with cookies.
3. Uploads 4 test photos across 3 categories (life, pet, photography).
4. Runs Worker in `--once` mode to process all jobs.
5. Verifies showcase API returns ready photos with valid slide designs.
6. Verifies admin endpoints: jobs, categories, audit logs; verifies permission boundaries.
7. Verifies v0.3 new schema fields: Fill model, Shadow model, 8 template IDs, 8 layer types.
8. Runs Playwright E2E tests (headless).
9. Runs backup and restore rehearsal, verifying data fields in manifest.
10. Verifies auto-play: state variables, Space key handler, Play/Pause icons, interval selector, stopAutoPlay in manual nav, composable file, vitest tests.
11. Verifies map album: map API endpoint, /map page file, Leaflet dependency, MapPin icon, M key navigation, MapPhotoItem types, E2E tests, vitest tests.
12. Verifies mobile responsive code and runs mobile-viewport Playwright tests.

Run one Worker pass for testing:

```bash
WORKER_ARGS=--once just worker
```

## Photo Processing Pipeline

Each uploaded photo goes through:

```
uploaded → processing → preview_generated → geocoded → ready
```

- **preview_generated**: 2048px WebP preview + 512px WebP thumbnail uploaded to MinIO.
- **geocoded**: GPS coordinates reverse-geocoded to location text via Nominatim or Amap (skipped if geocoding is disabled or no GPS).
- **design_generated**: Deterministic fallback slide design created during ingest. Admins can later save manual design drafts or promote manual versions.
- **ready**: Photo appears in `/showcase` playback.

Failed jobs can be retried from `/admin/jobs`.

## `/showcase` Navigation

| Action | Behavior |
|--------|----------|
| Left Arrow / Left Click | Previous photo |
| Right Arrow / Right Click | Next photo |
| Scroll Wheel Up/Down | Switch category (life ↔ photography ↔ pet) |
| **Space** | **Toggle auto-play on/off** |
| `C` key | Toggle category sidebar |
| `M` key | Navigate to map album (`/map`) |
| `F` key | Toggle fullscreen |
| `?` key | Show/hide keyboard shortcuts overlay |

Right-click context menu is prevented on the showcase to avoid accidental browser menus. Auto-play advances photos at the configured interval (3s / 5s / 8s) within the current category; any manual navigation stops it. The interval selector and Play/Pause button are in the top menu bar.

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
