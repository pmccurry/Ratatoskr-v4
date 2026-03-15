# TASK-001 — Repository Scaffold

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Create the application scaffold for the Ratatoskr Trading Platform:
backend folder structure, frontend folder structure, infrastructure configs,
test directories, docs directories, and root project files.

This task creates STRUCTURE and CONFIGURATION only. No application logic,
no business code, no database models, no API endpoints beyond a health check.

**The entire /studio directory already exists** (canonical state files, specs,
agent files, workflow protocol). This task does NOT touch /studio at all.
The /CLAUDE.md root file also already exists. Do NOT modify it.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/STUDIO/STATUS_BOARD.yaml
5. /studio/SPECS/cross_cutting_specs.md

## Constraints

- Do NOT implement any application logic or business code
- Do NOT create database models or migrations
- Do NOT create API endpoints or route handlers (except /api/v1/health)
- Do NOT add modules outside the approved module list
- Do NOT redesign the architecture or rename modules
- Do NOT add dependencies beyond what's needed for baseline scaffold
- Do NOT create, modify, or delete anything inside /studio
- Do NOT modify /CLAUDE.md
- This task is for STRUCTURE and BASELINE CONFIG only

---

## Deliverables

### 1. Backend Structure

Create the complete backend directory tree with empty __init__.py files:

```
backend/
    app/
        __init__.py
        main.py                          (minimal FastAPI app — see section 2)
        common/
            __init__.py
            config.py                    (empty placeholder)
            database.py                  (empty placeholder)
            base_model.py                (empty placeholder)
            errors.py                    (empty placeholder)
            schemas.py                   (empty placeholder)
            utils.py                     (empty placeholder)
        auth/
            __init__.py
        market_data/
            __init__.py
            adapters/__init__.py
            streams/__init__.py
            options/__init__.py
            backfill/__init__.py
            universe/__init__.py
            aggregation/__init__.py
        strategies/
            __init__.py
            indicators/__init__.py
            conditions/__init__.py
            formulas/__init__.py
            custom/__init__.py
        signals/
            __init__.py
        risk/
            __init__.py
            checks/__init__.py
            monitoring/__init__.py
        paper_trading/
            __init__.py
            executors/__init__.py
            forex_pool/__init__.py
            shadow/__init__.py
            fill_simulation/__init__.py
        portfolio/
            __init__.py
        observability/
            __init__.py
            events/__init__.py
            metrics/__init__.py
            alerts/__init__.py
            logging/__init__.py
    migrations/
        versions/.gitkeep
    pyproject.toml                       (see section 3)
```

Every `__init__.py` is an empty file. No logic in any of them.
The `common/` placeholder files (config.py, database.py, etc.) are empty
files — they establish the file structure for future tasks.

### 2. Backend main.py

Minimal FastAPI app with ONLY a health check endpoint:

```python
"""Ratatoskr Trading Platform — API Entrypoint"""
from fastapi import FastAPI

app = FastAPI(
    title="Ratatoskr Trading Platform",
    description="Professional quant/algo trading platform",
    version="0.1.0",
)


@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
```

No other routes. No middleware. No startup events. No imports beyond FastAPI.

### 3. Backend pyproject.toml

```toml
[project]
name = "ratatoskr-trading-platform"
version = "0.1.0"
description = "Professional quant/algo trading platform"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.0",
    "httpx>=0.27.0",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["../tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 4. Frontend Structure

```
frontend/
    src/
        app/
            App.tsx                      (minimal placeholder — see section 5)
            router.tsx                   (empty placeholder)
            providers.tsx                (empty placeholder)
        components/ui/.gitkeep
        features/
            auth/.gitkeep
            dashboard/.gitkeep
            strategies/.gitkeep
            signals/.gitkeep
            orders/.gitkeep
            portfolio/.gitkeep
            risk/.gitkeep
            system/.gitkeep
            settings/.gitkeep
        layouts/.gitkeep
        pages/.gitkeep
        lib/
            api.ts                       (empty placeholder)
            formatters.ts                (empty placeholder)
            constants.ts                 (empty placeholder)
            utils.ts                     (empty placeholder)
        types/.gitkeep
        index.css                        (Tailwind imports only)
        main.tsx                         (React root render)
        vite-env.d.ts
    public/.gitkeep
    index.html
    package.json
    tsconfig.json
    tsconfig.node.json
    vite.config.ts
    tailwind.config.js
    postcss.config.js
    eslint.config.js
    .prettierrc
```

### 5. Frontend File Contents

Refer to /studio/SPECS/frontend_specs.md for exact content of:
- package.json (dependencies and scripts)
- vite.config.ts (proxy, aliases)
- tsconfig.json (strict mode, paths)
- tailwind.config.js (dark theme colors, fonts)
- postcss.config.js
- .prettierrc

**App.tsx:**
```typescript
function App() {
  return (
    <div className="min-h-screen bg-background text-white flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-2">Ratatoskr Trading Platform</h1>
        <p className="text-gray-400">v0.1.0 — scaffold ready</p>
      </div>
    </div>
  );
}
export default App;
```

**main.tsx:**
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

**index.css:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**index.html:**
```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Ratatoskr Trading Platform</title>
  </head>
  <body class="bg-background text-white">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Empty placeholder files (router.tsx, providers.tsx, api.ts, formatters.ts,
constants.ts, utils.ts) contain only a comment:
```typescript
// Placeholder — implementation in a future task
```

### 6. Shared Structure

```
shared/
    schemas/.gitkeep
    contracts/.gitkeep
    types/.gitkeep
    constants/.gitkeep
```

### 7. Infrastructure

```
infra/
    docker/
        Dockerfile.backend
        Dockerfile.frontend
    scripts/.gitkeep
    env/
        .env.example
    ci/.gitkeep
```

**Dockerfile.backend:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml .
RUN uv sync --no-dev

COPY backend/ .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile.frontend:**
```dockerfile
FROM node:20-slim AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

**.env.example:** Must contain EVERY configuration variable from
/studio/SPECS/cross_cutting_specs.md section "Configuration Variables Summary."
Copy that entire block verbatim with the section headers and comments.

### 8. Tests Structure

```
tests/
    unit/.gitkeep
    integration/.gitkeep
    e2e/.gitkeep
    conftest.py                          (empty file)
```

### 9. Docs Structure

```
docs/
    README.md
    product/.gitkeep
    architecture/.gitkeep
    data/.gitkeep
    risk/.gitkeep
    api/.gitkeep
    ui/.gitkeep
    ops/.gitkeep
    testing/.gitkeep
```

**docs/README.md:**
```markdown
# Ratatoskr Trading Platform — Documentation

## Structure
- `product/` — product requirements and feature specs
- `architecture/` — system architecture and design docs
- `data/` — data models, contracts, and schemas
- `risk/` — risk engine documentation
- `api/` — API reference and conventions
- `ui/` — frontend architecture and design
- `ops/` — deployment, monitoring, and operations
- `testing/` — test strategy and coverage

## Engineering Specs
All engineering specs are maintained in `/studio/SPECS/`.
```

### 10. Root Files

Create these at the project root (alongside /studio, /backend, /frontend, etc.):

**README.md:**
```markdown
# Ratatoskr Trading Platform

Professional web-based trading platform for quantitative and algorithmic traders.

## Overview

Ratatoskr is a research-first, paper-trading-first platform supporting:
- Multi-broker market data (Alpaca for equities/options, OANDA for forex)
- Config-driven strategy building (no code required)
- Signal generation with risk management
- Paper trading with honest simulation
- Portfolio tracking with full PnL accounting
- Real-time operator dashboards

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Infrastructure:** Docker Compose

## Getting Started

\```bash
# Copy environment config
cp infra/env/.env.example .env

# Start services
docker compose up -d

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Health check: http://localhost:8000/api/v1/health
\```

## Project Structure

\```
backend/         Python FastAPI application
frontend/        React TypeScript SPA
shared/          Cross-boundary schemas and contracts
infra/           Docker, scripts, environment config
tests/           Unit, integration, and e2e tests
docs/            Documentation
studio/          AI development studio (specs, tasks, state files)
\```

## Documentation

- Engineering specs: `studio/SPECS/`
- Project state: `studio/STUDIO/`
- Architecture decisions: `studio/STUDIO/DECISIONS.md`
```

**.gitignore:**
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
dist/
build/
*.egg
.venv/
.mypy_cache/

# Node
node_modules/
frontend/dist/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
postgres_data/

# Testing
.coverage
htmlcov/
.pytest_cache/
```

**docker-compose.yml:**
```yaml
version: "3.8"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ratatoskr
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

---

## Acceptance Criteria

1. All backend module folders exist with correct nesting and empty __init__.py files
2. All backend sub-module folders (adapters, streams, checks, executors, etc.) exist
3. backend/app/main.py has ONLY the health check endpoint, no other code
4. backend/pyproject.toml is valid with correct dependencies matching the approved stack
5. All frontend folders exist (app, components, features, layouts, pages, lib, types)
6. All frontend feature sub-folders exist (auth, dashboard, strategies, signals, orders, portfolio, risk, system, settings)
7. Frontend package.json is valid with correct dependencies matching the approved stack
8. All frontend config files present and valid (vite.config.ts, tsconfig.json, tailwind.config.js, postcss.config.js, .prettierrc, eslint.config.js)
9. Frontend App.tsx renders the minimal placeholder
10. Frontend main.tsx, index.html, and index.css exist with correct content
11. shared/ directory exists with schemas, contracts, types, constants sub-folders
12. infra/ directory exists with docker, scripts, env, ci sub-folders
13. Dockerfile.backend and Dockerfile.frontend exist with correct content
14. .env.example contains ALL configuration variables from the cross_cutting_specs
15. docker-compose.yml defines db, backend, frontend services with correct ports
16. tests/ directory exists with unit, integration, e2e sub-folders and empty conftest.py
17. docs/ directory exists with all sub-folders and README.md
18. Root README.md exists with project overview
19. .gitignore exists covering Python, Node, env, IDE, OS files
20. Nothing inside /studio was created, modified, or deleted
21. /CLAUDE.md was not modified
22. Module folder names match GLOSSARY exactly: auth, market_data, strategies, signals, risk, paper_trading, portfolio, observability, common
23. No application logic, models, services, or routes exist beyond the health check
24. All empty directories have .gitkeep files
25. All placeholder .ts/.tsx files contain only a placeholder comment, no logic

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-001-bootstrap/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
