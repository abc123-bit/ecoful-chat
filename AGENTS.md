# Repository Guidelines

## Project Structure & Module Organization
- Frontend (Vue 3) in `src/`: reusable UI in `src/components`, view shells in `src/views`, Pinia stores in `src/stores`, API helpers in `src/services`, static media in `src/assets`. App bootstraps in `src/main.js`; Vite outputs to `dist/`.
- Backend (FastAPI) in `backend/app`: routers in `api/`, settings in `core/`, DB session in `db/`, ORM `models/` and Pydantic `schemas/`.
- Migrations in `backend/migrations`; tests in `backend/tests`; Docker and helper scripts at repository root.

## Build, Test, and Development Commands
- Install frontend deps: `npm install`
- Dev server: `npm run dev` (Vite on http://localhost:3000)
- Build / preview: `npm run build` → `dist/`; `npm run preview`
- Lint / format: `npm run lint` (ESLint `@vue/standard`); `npm run format` (Prettier on `src/`)
- Backend env: `python -m venv venv && pip install -r backend/requirements.txt`
- Run API (from `backend/`): `uvicorn app.main:app --reload --port 8080`
- Mock service: `python backend/start_simple.py`
- Tests: `pytest backend/tests`

## Coding Style & Naming Conventions
- Vue: two-space indent, no semicolons, single quotes. Component files in PascalCase (e.g., `ChatSidebar.vue`). Pinia stores camelCase (e.g., `useChatStore`). Feature utils in `src/utils`.
- Python: PEP 8, four-space indent, snake_case filenames. Add type hints where helpful. Prefer `loguru` over prints.

## Testing Guidelines
- Backend uses pytest + FastAPI `TestClient`. Mirror async patterns shown in `backend/tests/test_knowledge_base.py`.
- Name tests descriptively (e.g., `test_create_knowledge_base`). Use fixtures to isolate temporary data.
- Run `pytest backend/tests` before submitting changes.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `chore:` (scope optional).
- PRs should: summarize the change, list impacted packages (`frontend`, `backend`), link issues, include before/after screenshots for UI tweaks, mention required `.env` vars, and note migrations (run `alembic upgrade head`).

## Configuration Notes
- Copy `.env.example` → `.env` (frontend) and `backend/.env.example` → `backend/.env`.
- Never commit real API keys; share secrets via the team vault.
- Containers: use root `docker-compose.yml` for full stack or `backend/docker-compose.yml` for API-only.

