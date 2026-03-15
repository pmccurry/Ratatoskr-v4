# TASK-029 — E2E API Flow Tests

## Goal

Write end-to-end tests that exercise complete API workflows through real HTTP requests against the running FastAPI application. These tests verify auth, response envelopes, pagination, error handling, and multi-step business flows from the API consumer's perspective.

## Depends On

TASK-028

## Scope

**In scope:**
- `tests/e2e/conftest.py` — AsyncClient setup via httpx, auth helper, test database
- `tests/e2e/test_auth_flow.py` — Login, token refresh, protected routes, logout
- `tests/e2e/test_strategy_create_and_evaluate.py` — Full strategy lifecycle via API
- `tests/e2e/test_signal_to_fill_pipeline.py` — Signal creation through to position
- `tests/e2e/test_manual_close_flow.py` — Position close via API
- `tests/e2e/test_risk_rejection_flow.py` — Risk checks blocking signals via API
- `tests/e2e/test_api_conventions.py` — Response envelope, pagination, errors, camelCase

**Out of scope:**
- Browser tests (Playwright — separate task)
- Frontend tests
- Application code changes
- Broker-connected tests

---

## Deliverables

### D1 — E2E conftest (`tests/e2e/conftest.py`)

Set up a real application instance with a test database and HTTP client:

```python
"""
E2E test conftest — real FastAPI app with test database.

Uses httpx.AsyncClient with the FastAPI app directly (no live server needed).
"""
import pytest
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Override DATABASE_URL before importing the app
os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test"
)

from backend.app.main import app
from backend.app.common.base_model import Base

@pytest.fixture(scope="session")
async def setup_database():
    """Create all tables once per session, drop after."""
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(setup_database) -> AsyncClient:
    """HTTP client hitting the real FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.fixture
async def auth_client(client) -> AsyncClient:
    """Authenticated HTTP client (logs in as admin, attaches token)."""
    # Seed admin if needed, then login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@ratatoskr.local",
        "password": "changeme123456"
    })
    if login_resp.status_code == 401:
        # Admin not seeded — create via direct DB insert or seed script
        # Fall back: create user via app internals
        pass
    token = login_resp.json()["data"]["accessToken"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
```

Key design decisions:
- Uses `httpx.AsyncClient` with `ASGITransport` — no live server process needed
- Tests hit the real FastAPI app with all middleware, auth, and error handlers active
- `auth_client` fixture handles login and attaches the JWT token
- Database override happens before app import so the app connects to the test DB

Also create `backend/tests/e2e/__init__.py`.

### D2 — `tests/e2e/test_auth_flow.py`

Test the complete authentication lifecycle through HTTP.

```python
class TestLogin:
    async def test_login_returns_tokens(self, client):
        """POST /auth/login with valid credentials → 200 with accessToken and refreshToken"""

    async def test_login_wrong_password(self, client):
        """POST /auth/login with wrong password → 401 with AUTH_INVALID_CREDENTIALS error"""

    async def test_login_nonexistent_user(self, client):
        """POST /auth/login with unknown email → 401"""

    async def test_login_response_is_camelcase(self, client):
        """Response fields are camelCase (accessToken, not access_token)"""

class TestProtectedRoutes:
    async def test_no_token_returns_401(self, client):
        """GET /strategies without token → 401"""

    async def test_valid_token_returns_200(self, auth_client):
        """GET /strategies with valid token → 200"""

    async def test_expired_token_returns_401(self, client):
        """GET /strategies with expired/invalid JWT → 401"""

    async def test_get_me(self, auth_client):
        """GET /auth/me → 200 with current user profile"""

class TestTokenRefresh:
    async def test_refresh_returns_new_tokens(self, client):
        """POST /auth/refresh with valid refresh token → new accessToken + refreshToken"""

    async def test_refresh_invalid_token_returns_401(self, client):
        """POST /auth/refresh with garbage token → 401"""

class TestLogout:
    async def test_logout_revokes_refresh_token(self, client):
        """POST /auth/logout → 200, subsequent refresh with same token fails"""
```

### D3 — `tests/e2e/test_strategy_create_and_evaluate.py`

Test the full strategy lifecycle via API: create → configure → enable → list → detail → disable → delete.

```python
class TestStrategyLifecycleAPI:
    async def test_create_draft_strategy(self, auth_client):
        """POST /strategies with valid config → 201 with strategy in 'draft' status"""

    async def test_create_strategy_response_envelope(self, auth_client):
        """Response is wrapped in { "data": { ... } } envelope"""

    async def test_create_strategy_fields_camelcase(self, auth_client):
        """Response uses camelCase: strategyId, configVersion, createdAt"""

    async def test_get_strategy_detail(self, auth_client):
        """GET /strategies/:id → 200 with full strategy config"""

    async def test_list_strategies(self, auth_client):
        """GET /strategies → 200 with data array and pagination"""

    async def test_enable_strategy(self, auth_client):
        """POST /strategies/:id/enable → 200, status changes to 'enabled'"""

    async def test_pause_strategy(self, auth_client):
        """POST /strategies/:id/pause → 200, status changes to 'paused'"""

    async def test_disable_strategy(self, auth_client):
        """POST /strategies/:id/disable → 200, status changes to 'disabled'"""

    async def test_delete_draft_strategy(self, auth_client):
        """DELETE /strategies/:id (draft) → 200"""

    async def test_delete_enabled_strategy_fails(self, auth_client):
        """DELETE /strategies/:id (enabled) → 422 or 409"""

    async def test_get_indicator_catalog(self, auth_client):
        """GET /strategies/indicators → 200 with indicator list including params"""

    async def test_create_invalid_strategy(self, auth_client):
        """POST /strategies with missing required fields → 400/422 with error envelope"""
```

### D4 — `tests/e2e/test_signal_to_fill_pipeline.py`

Test the multi-step pipeline: create strategy → (simulate signal creation) → verify signal appears → verify risk decision → verify order → verify fill → verify position.

Since the strategy runner generates signals automatically, and we can't easily trigger a real evaluation in E2E tests, this test works by:
1. Creating and enabling a strategy via API
2. Directly creating a signal via the signal service (or a test-only endpoint if one exists)
3. Verifying the downstream effects via API queries

If no internal signal creation is possible from the API, the test verifies the read-side endpoints with pre-seeded data.

```python
class TestSignalEndpoints:
    async def test_list_signals_empty(self, auth_client):
        """GET /signals → 200 with empty data array"""

    async def test_list_signals_with_filters(self, auth_client):
        """GET /signals?status=pending&symbol=AAPL → filtered results"""

    async def test_signal_detail(self, auth_client):
        """GET /signals/:id → 200 with full signal payload"""

    async def test_cancel_signal(self, auth_client):
        """POST /signals/:id/cancel → 200, signal status changes to 'canceled'"""

class TestOrderAndFillEndpoints:
    async def test_list_orders_empty(self, auth_client):
        """GET /paper-trading/orders → 200 with empty data array"""

    async def test_list_fills_empty(self, auth_client):
        """GET /paper-trading/fills → 200 with empty data array"""

    async def test_trading_stats(self, auth_client):
        """GET /paper-trading/stats → 200 with stats object"""

class TestPortfolioEndpoints:
    async def test_portfolio_summary(self, auth_client):
        """GET /portfolio/summary → 200 with equity, cash, positions summary"""

    async def test_positions_list(self, auth_client):
        """GET /portfolio/positions → 200 with data array"""

    async def test_equity_curve(self, auth_client):
        """GET /portfolio/equity-curve → 200 with chart data"""

    async def test_portfolio_metrics(self, auth_client):
        """GET /portfolio/metrics → 200 with performance metrics"""
```

### D5 — `tests/e2e/test_manual_close_flow.py`

Test the manual position close flow via API.

```python
class TestManualClose:
    async def test_close_position(self, auth_client):
        """POST /positions/:id/close → 200, position status becomes 'closed'
        
        Setup: create a strategy, seed a position via DB fixture or prior fill.
        Then close via API and verify the position state changed."""

    async def test_close_partial_position(self, auth_client):
        """POST /positions/:id/close-partial with qty → 200, position qty reduced"""

    async def test_close_nonexistent_position(self, auth_client):
        """POST /positions/fake-uuid/close → 404 with PORTFOLIO_POSITION_NOT_FOUND"""

    async def test_close_already_closed_position(self, auth_client):
        """POST /positions/:id/close (already closed) → 422 with PORTFOLIO_NO_OPEN_POSITION"""

    async def test_close_all_for_strategy(self, auth_client):
        """POST /strategies/:id/close-all → 200, all positions for that strategy closed"""

    async def test_emergency_close_all(self, auth_client):
        """POST /positions/close-all → 200, all positions globally closed"""
```

### D6 — `tests/e2e/test_risk_rejection_flow.py`

Test risk endpoints and kill switch behavior via API.

```python
class TestRiskEndpoints:
    async def test_risk_overview(self, auth_client):
        """GET /risk/overview → 200 with current risk state"""

    async def test_risk_config(self, auth_client):
        """GET /risk/config → 200 with current limits"""

    async def test_update_risk_config(self, auth_client):
        """PUT /risk/config with new limits → 200"""

    async def test_risk_decisions_list(self, auth_client):
        """GET /risk/decisions → 200 with data array and pagination"""

    async def test_exposure_breakdown(self, auth_client):
        """GET /risk/exposure → 200 with per-symbol breakdown"""

    async def test_drawdown_state(self, auth_client):
        """GET /risk/drawdown → 200 with current drawdown info"""

class TestKillSwitchAPI:
    async def test_kill_switch_status(self, auth_client):
        """GET /risk/kill-switch/status → 200 with current state"""

    async def test_activate_kill_switch(self, auth_client):
        """POST /risk/kill-switch/activate → 200, status becomes active"""

    async def test_deactivate_kill_switch(self, auth_client):
        """POST /risk/kill-switch/deactivate → 200, status becomes inactive"""

    async def test_kill_switch_round_trip(self, auth_client):
        """Activate → verify active → deactivate → verify inactive"""

class TestRiskConfigAudit:
    async def test_config_audit_trail(self, auth_client):
        """PUT /risk/config → GET /risk/config/audit → shows change entry"""
```

### D7 — `tests/e2e/test_api_conventions.py`

Test that API conventions from cross_cutting_specs.md are consistently applied.

```python
class TestResponseEnvelope:
    async def test_single_entity_wrapped_in_data(self, auth_client):
        """GET /strategies/:id → { "data": { ... } }"""

    async def test_list_wrapped_in_data_with_pagination(self, auth_client):
        """GET /strategies → { "data": [...], "pagination": { page, pageSize, totalItems, totalPages } }"""

    async def test_error_wrapped_in_error(self, auth_client):
        """GET /strategies/nonexistent → { "error": { "code", "message", "details" } }"""

    async def test_no_bare_array(self, auth_client):
        """List responses are never bare arrays — always under "data" key"""

class TestPagination:
    async def test_default_page_and_size(self, auth_client):
        """GET /strategies → pagination defaults to page=1, pageSize=20"""

    async def test_custom_page_size(self, auth_client):
        """GET /strategies?pageSize=5 → pageSize=5 in pagination metadata"""

    async def test_page_beyond_data(self, auth_client):
        """GET /strategies?page=999 → empty data array, correct totalItems"""

class TestErrorResponses:
    async def test_404_has_error_code(self, auth_client):
        """GET /strategies/nonexistent-uuid → 404 with code=NOT_FOUND or STRATEGY_NOT_FOUND"""

    async def test_401_has_error_code(self, client):
        """GET /strategies without auth → 401 with AUTH_ error code"""

    async def test_422_has_error_details(self, auth_client):
        """POST /strategies with invalid body → 422 with field-level errors"""

    async def test_500_never_exposes_traceback(self, auth_client):
        """Internal error → 500 with INTERNAL_ERROR code, no traceback in response"""

class TestCamelCaseConvention:
    async def test_response_fields_are_camelcase(self, auth_client):
        """Strategy response has 'configVersion', 'createdAt' — not snake_case"""

    async def test_request_accepts_camelcase(self, auth_client):
        """POST /strategies with camelCase body → 201"""

class TestHealthEndpoint:
    async def test_health_no_auth_required(self, client):
        """GET /health → 200 without any auth token"""

    async def test_health_returns_status(self, client):
        """GET /health → { "status": "healthy" }"""
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | E2E conftest provides `client` (unauthenticated) and `auth_client` (authenticated) fixtures |
| AC2 | `auth_client` fixture logs in via HTTP and attaches JWT token to all requests |
| AC3 | Auth flow tests cover login (success + failure), protected routes, token refresh, and logout |
| AC4 | Strategy lifecycle tests cover create, enable, pause, disable, delete, and invalid operations |
| AC5 | Signal/order/portfolio endpoint tests verify all read endpoints return 200 with correct envelope |
| AC6 | Manual close tests cover full close, partial close, nonexistent position, and already-closed |
| AC7 | Risk endpoint tests cover overview, config CRUD, exposure, drawdown, and kill switch round-trip |
| AC8 | Convention tests verify response envelope (data/error), pagination metadata, camelCase fields |
| AC9 | Error response tests verify 401, 404, 422 all return structured error JSON with code field |
| AC10 | Health endpoint test verifies no auth required and returns status |
| AC11 | All tests use `httpx.AsyncClient` with `ASGITransport` (no live server process) |
| AC12 | All tests are independent — no test depends on another test's side effects |
| AC13 | No application code modified |
| AC14 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

| File | Purpose |
|------|---------|
| `backend/tests/e2e/__init__.py` | Package marker |
| `backend/tests/e2e/conftest.py` | App client, auth fixtures, test DB setup |
| `backend/tests/e2e/test_auth_flow.py` | Authentication lifecycle tests |
| `backend/tests/e2e/test_strategy_create_and_evaluate.py` | Strategy CRUD and lifecycle via API |
| `backend/tests/e2e/test_signal_to_fill_pipeline.py` | Signal, order, fill, portfolio read endpoints |
| `backend/tests/e2e/test_manual_close_flow.py` | Position close operations |
| `backend/tests/e2e/test_risk_rejection_flow.py` | Risk endpoints and kill switch |
| `backend/tests/e2e/test_api_conventions.py` | Envelope, pagination, errors, camelCase |

## Files NOT to Touch

Everything outside `backend/tests/`.

## Builder Notes

- **ASGITransport approach:** Use `httpx.AsyncClient(transport=ASGITransport(app=app))` to hit the real FastAPI app without starting a server process. This means middleware, auth, error handlers, and serialization all run as they would in production.
- **Admin user seeding:** The `auth_client` fixture needs an admin user to exist. Either import and run the seed script, or create the user via direct DB access in the fixture. The seed script pattern from `scripts/seed_admin.py` can be adapted.
- **Test independence:** Each test should create its own test data if needed (e.g., create a strategy before testing enable). Don't rely on data from other tests. The conftest `setup_database` creates tables once per session, but each test should create its own entities.
- **Pre-existing data:** Some endpoints return valid responses even with no data (empty lists, zero stats). Test these "empty state" responses as valid behavior.
- **Partial pipeline tests (D4):** The signal-to-fill pipeline is normally triggered by the strategy runner, not by API calls. E2E tests for D4 focus on verifying the read-side endpoints work correctly. If you can find a way to inject signals programmatically (e.g., importing the signal service), do so — but don't modify application code to add test-only endpoints.
- **Position fixtures for close tests (D5):** Manual close tests need an existing position. Create one via DB fixtures in the test setup, or by running enough of the pipeline to produce one.
- **httpx must be in dev dependencies.** Check `pyproject.toml` and add if missing.

## References

- cross_cutting_specs.md §5 — API Conventions (envelope, pagination, filtering, sorting, camelCase)
- cross_cutting_specs.md §6 — Testing Strategy (E2E test files, critical paths)
- cross_cutting_specs.md §2 — Error Handling (error response format, status codes)
- auth_module_spec.md §5 — Authentication Flow (login, refresh, logout)
- auth_module_spec.md §8 — API Endpoints
- strategy_module_spec.md §API Endpoints
- signals_module_spec.md §API Endpoints
- risk_engine_module_spec.md §API Endpoints
- paper_trading_module_spec.md §API Endpoints
- portfolio_module_spec.md §API Endpoints
