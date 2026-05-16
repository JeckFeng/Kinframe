# Global Rules
Within the current project's workspace, all your actions must strictly adhere to the following rules.
@/home/xian00/.codex/RTK.md
Please carefully read the contents of the “@/home/xian00/.codex/RTK.md” file.
Strictly follow the instructions in RTK.md.
Always prefix shell commands with `rtk`.

# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains the technical plan in `kinframe-technical-development-plan.md`. New implementation work should follow the planned `kinframe/` layout:

- `frontend/`: Nuxt 3, Vue, TypeScript UI for gallery, upload, and chatbot flows.
- `backend/`: FastAPI service. Keep application code in `backend/app/` with `api/`, `core/`, `models/`, `schemas/`, `services/`, `agents/`, `workers/`, and `utils/`.
- `backend/tests/`: backend tests.
- `deploy/`: Caddy, Cloudflare Tunnel, and MinIO setup files.
- `scripts/`: backup, restore, environment checks, and local dev helpers.
- `data/`: local persisted PostgreSQL, MinIO, Redis, and backup data. Do not commit this directory.

## Build, Test, and Development Commands

Use the commands described in the plan once the corresponding files exist:

```bash
docker compose -f docker-compose.infra.yml up -d
cd backend && uv sync
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && corepack enable && pnpm install && pnpm dev
docker compose -f docker-compose.prod.yml up -d --build
```

If a `justfile` is added, prefer `just infra`, `just backend`, `just frontend`, `just prod`, `just backup`, and `just restore`.

## Coding Style & Naming Conventions

Use TypeScript for frontend code and Python for backend code. Keep Vue components in PascalCase, composables named `useSomething.ts`, and API routes/services named by domain, such as `photos` or `auth`. Python modules should use `snake_case`; classes should use `PascalCase`; Pydantic schemas should be explicit request/response models. Keep business rules in deterministic services, not in LLM prompts or agent code.

## Testing Guidelines

No committed test runner configuration exists yet. Add backend tests under `backend/tests/` and name files `test_*.py`. Cover authentication, upload validation, EXIF fallback behavior, object storage access, and agent failure degradation. When frontend tests are introduced, colocate component tests or place them under `frontend/tests/`, and add matching `pnpm` scripts.

## Commit & Pull Request Guidelines

This directory is not currently a Git repository, so no commit history conventions are available. Use clear, imperative commit messages such as `Add photo upload API` or `Document backup workflow`. Pull requests should include a short purpose statement, implementation notes, test results, linked issues if any, and screenshots for visible UI changes.

## Security & Configuration Tips

Never commit `.env`, `data/`, generated backups, `frontend/node_modules/`, `backend/.venv/`, or cache directories. Keep MinIO buckets private and serve photos through authenticated backend URLs or short-lived presigned URLs. Treat Ollama and DeepSeek outputs as suggestions only; users must be able to correct captions and categories.
