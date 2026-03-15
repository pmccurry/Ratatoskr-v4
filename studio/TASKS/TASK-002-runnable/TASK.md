# TASK-002 — Runnable Foundation

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Make the scaffold from TASK-001 actually run. After this task:
- `docker compose up` starts Postgres, backend, and frontend
- The backend connects to Postgres and responds to health checks
- The frontend dev server renders the placeholder page
- The common module provides config loading, database sessions, base models, and error handling
- Alembic is initialized and can run migrations
- The backend has a working module router structure (empty routers registered)

This task implements the **common module** and **infrastructure plumbing** only.
No business logic, no domain models, no domain API endpoints.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/cross_cutting_specs.md
5. /studio/SPECS/auth_module_spec.md (for config pattern only — do NOT implement auth)

## Constraints

- Do NOT implement any domain business logic
- Do NOT create domain models (no Strategy, Signal, Position, etc.)
- Do NOT create domain API endpoints (no /api/v1/strategies, etc.)
- Do NOT implement authentication or authorization
- Do NOT create domain service or repository classes
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Module routers are registered but contain NO endpoints except health check
- This task is for PLUMBING and INFRASTRUCTURE only

---

## Deliverables

### 1. Backend — Common Config (backend/app/common/config.py)

Implement the Pydantic Settings class that loads all configuration from
environment variables. Refer to cross_cutting_specs.md "Configuration System"
section and the full configuration variable catalog.

Requirements:
- Use `pydantic-settings` BaseSettings
- Load from .env file with `env_file=".env"`
- Define ALL configuration variables from the .env.example as typed fields with defaults
- Group logically (database, auth, broker, market data, etc.) using comments or sections
- Required fields (DATABASE_URL, AUTH_JWT_SECRET_KEY) must not have defaults
  and must cause startup failure if missing
- Create a singleton `get_settings()` function that caches the settings instance
- Create a FastAPI dependency `get_settings_dep()` for injection

```python
# Pattern:
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    
    # Auth
    auth_jwt_secret_key: str
    # ... all other settings with types and defaults
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 2. Backend — Database Module (backend/app/common/database.py)

Implement async database session management.

Requirements:
- Create async SQLAlchemy engine from settings.database_url
- Configure connection pool (pool_size, max_overflow, pool_timeout from settings)
- Create async session factory
- Create `get_db()` async generator dependency for FastAPI
  (yields session, commits on success, rolls back on error, closes on exit)
- Expose engine and session factory for use by Alembic and tests

```python
# Pattern:
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 3. Backend — Base Model (backend/app/common/base_model.py)

Create the SQLAlchemy declarative base with common fields.

Requirements:
- Use SQLAlchemy 2.x declarative style with mapped_column
- Every model inherits common fields: id (UUID, primary key, default uuid4),
  created_at (datetime, UTC, default now), updated_at (datetime, UTC, auto-update)
- Timestamps must be timezone-aware UTC
- Use `sqlalchemy.orm.DeclarativeBase`

```python
# Pattern:
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from uuid import uuid4, UUID
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class BaseModel(Base):
    __abstract__ = True
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### 4. Backend — Error Handling (backend/app/common/errors.py)

Implement the domain error base class and global exception handlers.

Requirements:
- DomainError base class with code, message, details
- Error code to HTTP status mapping function
- FastAPI exception handlers for DomainError and unhandled Exception
- Unhandled exceptions return generic 500 error (never expose internals)
- Standard error response format: `{"error": {"code": "...", "message": "...", "details": {...}}}`

```python
# Pattern:
class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)
```

### 5. Backend — Shared Schemas (backend/app/common/schemas.py)

Implement shared Pydantic response models.

Requirements:
- ErrorResponse schema matching the error format
- PaginationParams schema (page, page_size with defaults and limits)
- PaginatedResponse generic wrapper
- HealthResponse schema

```python
# Pattern:
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}

class ErrorResponse(BaseModel):
    error: ErrorDetail

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta
```

### 6. Backend — Utilities (backend/app/common/utils.py)

Implement shared utility functions.

Requirements:
- `utcnow()` function that returns timezone-aware UTC datetime
- Any other small utilities needed by the common module

### 7. Backend — Updated main.py (backend/app/main.py)

Update the FastAPI app entrypoint to:
- Load settings on startup (fail fast if required settings missing)
- Register global exception handlers (DomainError + unhandled)
- Register all module routers (empty for now, see section 8)
- Add startup and shutdown events for database connection
- Keep the /api/v1/health endpoint, enhance it to check database connectivity
- Add CORS middleware (allow all origins for dev — tighten later)

```python
# Health check should verify DB connection:
@app.get("/api/v1/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": "0.1.0",
        "database": db_status,
    }
```

### 8. Backend — Module Router Stubs

Create an empty router file in each module that will eventually have API endpoints.
Register all routers in main.py under the /api/v1 prefix.

Create these files (each contains an empty APIRouter, no endpoints):

```
backend/app/auth/router.py
backend/app/market_data/router.py
backend/app/strategies/router.py
backend/app/signals/router.py
backend/app/risk/router.py
backend/app/paper_trading/router.py
backend/app/portfolio/router.py
backend/app/observability/router.py
```

Each file:
```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/module-name",    # e.g., "/auth", "/market-data", "/strategies"
    tags=["Module Name"],
)

# Endpoints will be added in future tasks
```

main.py registers them:
```python
from backend.app.auth.router import router as auth_router
# ... etc

app.include_router(auth_router, prefix="/api/v1")
# ... etc
```

URL prefixes for each module (matching cross_cutting_specs API conventions):
- auth: `/auth`
- market_data: `/market-data`
- strategies: `/strategies`
- signals: `/signals`
- risk: `/risk`
- paper_trading: `/paper-trading`
- portfolio: `/portfolio`
- observability: `/observability`

### 9. Backend — Alembic Setup

Initialize Alembic for database migrations.

Requirements:
- Run `alembic init` in the backend directory (or create equivalent config manually)
- Configure alembic.ini to read DATABASE_URL from environment (not hardcoded)
- Configure env.py to use the async engine from common/database.py
- Configure env.py to import Base from common/base_model.py (for autogenerate)
- Verify the migrations directory structure exists: backend/migrations/versions/
- Do NOT create any initial migration yet (no domain models exist)

```
backend/
    alembic.ini
    migrations/
        env.py
        script.py.mako
        versions/
            .gitkeep
```

### 10. Frontend — Install Dependencies

Run `npm install` in the frontend directory to generate package-lock.json.
This is required for Docker builds and for the dev server to work.

### 11. Backend — Install Dependencies

Run `uv lock` in the backend directory to generate uv.lock.
This is required for Docker builds.

### 12. Docker Compose — Verify Startup

After all the above, verify:
- `docker compose up db` starts Postgres and it becomes healthy
- The backend can connect to Postgres (health check returns `"database": "connected"`)
- The frontend dev server starts and renders the placeholder

Note: for local development, it may be easier to run backend and frontend
outside Docker while Postgres runs in Docker. Either approach is fine
for this task — the goal is that it CAN run, not that Docker is the
only way to run it.

### 13. Root — .env File

Create a `.env` file (NOT .env.example, the actual .env) by copying
from infra/env/.env.example with the database URL set to the Docker
Compose Postgres instance:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ratatoskr
AUTH_JWT_SECRET_KEY=dev-secret-change-in-production-min-32-chars!!
```

All other values can use defaults from .env.example.

This file is gitignored and is for local development only.

---

## Acceptance Criteria

1. `backend/app/common/config.py` implements Settings with ALL env variables, required fields validated
2. `backend/app/common/database.py` implements async engine, session factory, and get_db dependency
3. `backend/app/common/base_model.py` implements SQLAlchemy base with id (UUID), created_at, updated_at
4. `backend/app/common/errors.py` implements DomainError, error-to-status mapping, and exception handlers
5. `backend/app/common/schemas.py` implements ErrorResponse, PaginationParams, PaginatedResponse
6. `backend/app/common/utils.py` implements utcnow() returning timezone-aware UTC
7. `backend/app/main.py` loads settings, registers exception handlers, registers all module routers, has enhanced health check with DB connectivity
8. All 8 module router stubs exist with empty APIRouter and correct prefix/tags
9. All module routers are registered in main.py under /api/v1
10. Alembic is initialized with alembic.ini and migrations/env.py configured for async and autogenerate
11. Alembic env.py imports Base from common/base_model.py
12. Alembic reads DATABASE_URL from environment (not hardcoded)
13. frontend/package-lock.json exists (npm install was run)
14. backend/uv.lock exists (uv lock was run)
15. .env file exists at project root with DATABASE_URL and AUTH_JWT_SECRET_KEY set
16. Health check endpoint at /api/v1/health returns database connection status
17. No domain models, domain services, domain endpoints, or business logic exist
18. No authentication or authorization implemented
19. Nothing inside /studio was modified (except BUILDER_OUTPUT.md)
20. All new Python files follow snake_case naming
21. Common module files contain ONLY the infrastructure code described — no domain logic

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-002-runnable/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
