# TASK-035 — Pre-Live Readiness Checklist & Deployment Hardening

## Goal

Implement the remaining deployment hardening measures and create an automated readiness check script that verifies the system is properly configured before real trading begins. After this task, an operator can run one command to verify the platform is production-ready.

## Depends On

TASK-034 (audit trail verified)

## Scope

**In scope:**
- Rate limiting on auth endpoints (brute force protection)
- Request body size limits
- Production logging configuration
- Automated readiness check script
- Pre-live checklist documentation
- Final security review (CORS, JWT, secrets, .env, .gitignore)

**Out of scope:**
- Cloud deployment (k8s, AWS, etc.)
- SSL/TLS termination (handled by reverse proxy in production)
- Monitoring infrastructure (Prometheus, Grafana, etc.)
- CI/CD pipeline setup
- Frontend changes

---

## Deliverables

### D1 — Rate limiting on auth endpoints

Add rate limiting middleware to prevent brute force attacks on login and token endpoints.

**Endpoints to rate limit:**
- `POST /api/v1/auth/login` — 5 requests per minute per IP
- `POST /api/v1/auth/refresh` — 10 requests per minute per IP
- `POST /api/v1/auth/change-password` — 3 requests per minute per user

**Implementation:** Use a simple in-memory rate limiter (no Redis — per DECISION-004). FastAPI middleware or dependency injection.

```python
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time()
        window_start = now - self.window_seconds
        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True

# FastAPI dependency
login_limiter = RateLimiter(max_requests=5, window_seconds=60)

async def check_login_rate(request: Request):
    client_ip = request.client.host
    if not login_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail={
            "error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many login attempts. Try again later."}
        })
```

Wire into auth router:
```python
@router.post("/login", dependencies=[Depends(check_login_rate)])
async def login(...)
```

**Add to `.env.example`:**
```env
# === Rate Limiting ===
AUTH_LOGIN_RATE_LIMIT=5          # max requests per window
AUTH_LOGIN_RATE_WINDOW_SEC=60    # window in seconds
```

### D2 — Request body size limits

Add middleware to reject oversized request bodies.

```python
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = 1_048_576):  # 1MB default
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={"error": {"code": "REQUEST_TOO_LARGE", "message": "Request body exceeds maximum size"}}
            )
        return await call_next(request)
```

Add to `main.py`:
```python
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=settings.max_request_body_size)
```

**Add to `.env.example`:**
```env
MAX_REQUEST_BODY_SIZE=1048576    # 1MB in bytes
```

### D3 — Production logging configuration

Ensure logging is properly configured for production use.

**Check and fix if needed:**

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# In production: JSON logs for structured parsing
# In development: human-readable format
if settings.environment == "production":
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(getattr(logging, settings.log_level.upper()))
```

**Verify:**
- `LOG_LEVEL` controls all module log levels
- `LOG_FORMAT=json` produces JSON lines (parseable by log aggregators)
- `LOG_FORMAT=text` produces human-readable output (for local dev)
- Sensitive data (passwords, tokens, API keys) never appears in logs
- Stack traces only appear for unhandled exceptions, not for domain errors

### D4 — Automated readiness check script (`scripts/readiness_check.py`)

A script that verifies the system is properly configured before going live.

```python
#!/usr/bin/env python3
"""
Pre-live readiness check.

Run: uv run python scripts/readiness_check.py

Checks all critical configuration and connectivity requirements.
Exits 0 if all checks pass, 1 if any fail.
"""

checks = [
    # Security
    ("JWT secret changed from default", check_jwt_secret),
    ("Admin password changed from default", check_admin_password),
    ("CORS not allow-all", check_cors),
    ("Environment set to production", check_environment),
    (".env not committed to git", check_env_gitignore),

    # Database
    ("Database reachable", check_database_connection),
    ("All migrations applied", check_migrations_current),

    # Broker connectivity
    ("Alpaca API keys configured", check_alpaca_keys),
    ("Alpaca connection healthy", check_alpaca_connection),
    ("OANDA credentials configured", check_oanda_keys),
    ("OANDA connection healthy", check_oanda_connection),

    # Forex pool
    ("Forex pool accounts mapped", check_forex_pool_mapping),

    # Risk
    ("Kill switch is deactivated", check_kill_switch),
    ("Risk config loaded", check_risk_config),

    # Background tasks
    ("Strategy runner active", check_strategy_runner),
    ("Market data streaming", check_market_data_health),
    ("Event writer active", check_event_writer),
]

def main():
    print("=" * 60)
    print("  Ratatoskr Pre-Live Readiness Check")
    print("=" * 60)
    
    passed = 0
    failed = 0
    warnings = 0
    
    for name, check_fn in checks:
        try:
            result = check_fn()
            if result == "pass":
                print(f"  ✅  {name}")
                passed += 1
            elif result == "warn":
                print(f"  ⚠️  {name}")
                warnings += 1
            else:
                print(f"  ❌  {name}: {result}")
                failed += 1
        except Exception as e:
            print(f"  ❌  {name}: {e}")
            failed += 1
    
    print()
    print(f"Results: {passed} passed, {warnings} warnings, {failed} failed")
    
    if failed > 0:
        print("❌ NOT READY — fix failed checks before going live")
        sys.exit(1)
    elif warnings > 0:
        print("⚠️  READY WITH WARNINGS — review warnings before going live")
        sys.exit(0)
    else:
        print("✅ ALL CLEAR — system is ready for live trading")
        sys.exit(0)
```

Each check function connects to the running backend via API or reads from `.env` / database directly.

**Check implementations (examples):**

```python
def check_jwt_secret():
    secret = os.environ.get("AUTH_JWT_SECRET_KEY", "")
    if "dev-only" in secret or "change-me" in secret:
        return "still using default dev secret"
    if len(secret) < 32:
        return "secret too short (min 32 chars)"
    return "pass"

def check_admin_password():
    """Verify admin password isn't the default seed password."""
    # Hit the login endpoint with default password
    resp = requests.post(f"{API_URL}/auth/login", json={
        "email": "admin@ratatoskr.local",
        "password": "changeme123456"
    })
    if resp.status_code == 200:
        return "admin still using default password"
    return "pass"

def check_database_connection():
    resp = requests.get(f"{API_URL}/health")
    if resp.status_code == 200:
        return "pass"
    return f"health check returned {resp.status_code}"

def check_alpaca_keys():
    key = os.environ.get("ALPACA_API_KEY", "")
    if not key:
        return "ALPACA_API_KEY not set"
    return "pass"
```

Make executable: `chmod +x scripts/readiness_check.py`

### D5 — Pre-live checklist documentation

Add to README.md:

```markdown
## Pre-Live Checklist

Before enabling strategies with real broker execution:

### Automated Check
```bash
uv run python scripts/readiness_check.py
```

### Manual Review
- [ ] Review risk limits in Settings → Risk Configuration
- [ ] Set max drawdown and daily loss limits appropriate for your account
- [ ] Review position size limits per symbol and per strategy
- [ ] Start with one simple strategy and monitor before adding more
- [ ] Verify the kill switch works (activate → verify trading stops → deactivate)
- [ ] Check that the audit trail captures all trade events (GET /signals/:id/trace)
- [ ] Run reconciliation check (GET /paper-trading/reconciliation)
- [ ] Review all enabled strategies and their conditions

### Security
- [ ] Change admin password from default
- [ ] Generate a strong JWT secret: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `CORS_ALLOWED_ORIGINS` to your frontend domain
- [ ] Ensure `.env` is NOT committed to git
```

### D6 — Final security review

Run through and verify:

1. **JWT secret:** TASK-025 added the production guard. Verify it works.
2. **CORS:** TASK-025 added configurable origins. Verify `["*"]` is not used in production.
3. **Admin password:** Seed script uses `changeme123456`. Verify the readiness check catches this.
4. **.gitignore:** Verify `.env` is ignored.
5. **Error responses:** Verify 500 errors never expose stack traces (TASK-025 verified).
6. **No sensitive data in logs:** Grep for password, token, secret in log statements.

Document any issues found and fix them.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `POST /auth/login` is rate limited (5/minute per IP) |
| AC2 | Rate-limited requests return 429 with structured error response |
| AC3 | Request body size limit middleware rejects oversized requests with 413 |
| AC4 | Production logging outputs JSON format when `LOG_FORMAT=json` |
| AC5 | Sensitive data (passwords, tokens, keys) never appears in log output |
| AC6 | `scripts/readiness_check.py` exists and runs all checks |
| AC7 | Readiness check verifies: JWT secret, admin password, CORS, database, broker keys, migrations |
| AC8 | Readiness check exits 1 on failure, 0 on success |
| AC9 | README has pre-live checklist with both automated and manual steps |
| AC10 | `.env.example` includes rate limit and request size variables |
| AC11 | No frontend code modified |
| AC12 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/common/rate_limiter.py` | In-memory rate limiter class |
| `backend/app/common/middleware.py` (or add to existing) | Request size limit middleware |
| `scripts/readiness_check.py` | Automated pre-live readiness verification |

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/auth/router.py` | Add rate limit dependency to login/refresh/change-password |
| `backend/app/main.py` | Add request size middleware, verify logging config |
| `backend/app/common/config.py` | Add rate limit and request size settings |
| `.env.example` | Add rate limit and request size variables |
| `README.md` | Add pre-live checklist section |

## References

- auth_module_spec.md §Account Lockout (brute force protection)
- cross_cutting_specs.md §2 — Error Handling (429 status code)
- cross_cutting_specs.md §3 — Configuration System
- observability_module_spec.md §Application Logging
- DECISION-004 — No Redis (in-memory rate limiter)
