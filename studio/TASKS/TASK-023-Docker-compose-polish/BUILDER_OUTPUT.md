# Builder Output — TASK-023

## Task
Docker Compose and Startup Polish

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- `Dockerfile.backend` (repo root, multi-stage uv-based Python image)
- `frontend/Dockerfile` (multi-stage npm build + nginx serve)
- `frontend/nginx.conf` (SPA fallback + API proxy)
- `.env.example` (complete variable catalog from cross_cutting_specs.md)
- `scripts/seed_admin.py` (standalone sync admin seeder)
- `scripts/start-dev.sh` (local dev startup script)

## Files Modified
- `docker-compose.yml` — full rewrite: 3 services (db, backend, frontend) with health checks, depends_on conditions, named volume, env_file
- `README.md` — replaced "Getting Started" section with "Quickstart" covering both Docker Compose and local dev workflows

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: `Dockerfile.backend` uses uv (not pip), multi-stage build, runs uvicorn on port 8000 — ✅ Done
2. AC2: `Dockerfile.frontend` builds React app and serves via nginx with SPA fallback — ✅ Done
3. AC3: `nginx.conf` has SPA `try_files` fallback and `/api/` proxy to backend — ✅ Done
4. AC4: `docker-compose.yml` defines db, backend, frontend services with correct depends_on and health checks — ✅ Done
5. AC5: `docker-compose.yml` db service uses `postgres:16-alpine` with named volume — ✅ Done
6. AC6: `.env.example` contains ALL variables from cross_cutting_specs.md config catalog — ✅ Done (all variables from §Configuration Variables Summary lines 953-1091 included)
7. AC7: `.env.example` DATABASE_URL uses `db` service name, not `localhost` — ✅ Done
8. AC8: `.env.example` includes `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` — ✅ Done
9. AC9: `scripts/seed_admin.py` creates admin user if none exists, skips if already seeded — ✅ Done
10. AC10: `scripts/seed_admin.py` uses bcrypt for password hashing (matching auth module pattern) — ✅ Done (uses bcrypt directly, same as `backend/app/auth/password.py`)
11. AC11: `scripts/start-dev.sh` starts db, waits for health, runs migrations, seeds, starts backend+frontend — ✅ Done
12. AC12: `scripts/start-dev.sh` has clean shutdown trap (kills background processes, stops db) — ✅ Done
13. AC13: `scripts/start-dev.sh` overrides DATABASE_URL to use localhost instead of Docker service name — ✅ Done (uses bash string substitution `${DATABASE_URL//db:5432/localhost:5432}`)
14. AC14: `README.md` has quickstart for both Docker Compose and local dev with login credentials — ✅ Done
15. AC15: No backend application code modified (only infra/config/scripts) — ✅ Done
16. AC16: No frontend application code modified (only Dockerfile, nginx.conf) — ✅ Done
17. AC17: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Dockerfile.backend build context:** The `uv.lock` is at `backend/uv.lock` (confirmed by file inspection). The builder stage copies `backend/pyproject.toml` and `backend/uv.lock` into the builder, then runs `uv sync --frozen --no-dev` from the backend directory. The runtime stage uses `uvicorn backend.app.main:app` (module path from repo root WORKDIR `/app`).
2. **Seed script uses raw SQL:** The task packet recommended using raw SQL if model imports fail from script location. Since the seed script runs from repo root (not from within the backend package), and the existing `backend/app/auth/seed.py` uses async imports that assume running inside the app, the standalone script uses raw SQL INSERT with synchronous SQLAlchemy. This avoids import path complexity.
3. **ADMIN_SEED_EMAIL added to .env.example:** The cross_cutting_specs.md config catalog does not list `ADMIN_SEED_EMAIL` as a variable, but the task packet explicitly requires it (D5). Added it alongside `ADMIN_SEED_PASSWORD`.
4. **start-dev.sh runs alembic from backend/ directory:** Since `alembic.ini` is in `backend/`, the script `cd`s into `backend/` to run migrations, then returns to repo root.
5. **start-dev.sh runs uvicorn from backend/ directory:** The existing `main.py` uses `from app.` imports (not `from backend.app.`), so uvicorn must run from within `backend/` as `app.main:app`.
6. **Docker Compose backend command uses `backend.app.main:app`:** In Docker, the WORKDIR is `/app` (repo root), so the module path is `backend.app.main:app`. The dev volume mount `./backend:/app/backend` enables hot reload.
7. **No `.dockerignore` created:** Task packet doesn't mention it. The build will include node_modules/venv but the multi-stage builds handle this (frontend Dockerfile context is `./frontend`, and the backend builder only copies what's needed).

## Ambiguities Encountered
1. **Dockerfile.backend WORKDIR vs uvicorn module path:** The existing Dockerfile at `infra/docker/Dockerfile.backend` used `app.main:app` with WORKDIR `/app` and copied only `backend/` contents. The task packet specifies the entrypoint as `backend.app.main:app` from WORKDIR `/app`, meaning the entire backend directory structure must be preserved. Chose the task packet's approach — WORKDIR `/app`, code at `/app/backend/`, uvicorn target `backend.app.main:app`.
2. **Existing Dockerfiles at `infra/docker/`:** The old Dockerfiles still exist at `infra/docker/Dockerfile.backend` and `infra/docker/Dockerfile.frontend`. The task says to create new ones at repo root and `frontend/` respectively. The old files are not deleted since the task doesn't list them for deletion, but they are now unused (docker-compose.yml points to the new locations).

## Dependencies Discovered
None

## Tests Created
None — not required by this task

## Risks or Concerns
1. **Old Dockerfiles remain at `infra/docker/`:** `infra/docker/Dockerfile.backend` and `infra/docker/Dockerfile.frontend` are now unused but still in the repo. They could cause confusion. Consider deleting them in a follow-up cleanup task.
2. **python-dotenv not in dependencies:** The seed script has a soft dependency on `python-dotenv` for loading `.env` files when run outside Docker. It gracefully falls back to environment variables if not installed. For `start-dev.sh`, the `.env` is loaded by pydantic-settings in the backend, and the seed script reads `DATABASE_URL` from the environment (set by the shell script).
3. **Backend module path divergence:** In Docker, uvicorn uses `backend.app.main:app` (from `/app`). In local dev, `start-dev.sh` runs from `backend/` using `app.main:app`. Both are correct for their contexts but represent different module paths.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
Milestone 13 — Testing and Validation: Begin writing the comprehensive test suite (unit tests for critical backend modules, starting with auth and risk engine).
