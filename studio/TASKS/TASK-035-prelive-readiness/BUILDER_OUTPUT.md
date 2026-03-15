# Builder Output — TASK-035

## Task
Pre-Live Readiness Checklist & Deployment Hardening

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- `backend/app/common/rate_limiter.py` — In-memory sliding window rate limiter with FastAPI dependencies for login (5/min), refresh (10/min), password change (3/min)
- `backend/app/common/middleware.py` — `RequestSizeLimitMiddleware` rejecting oversized request bodies with 413
- `scripts/readiness_check.py` — Automated pre-live readiness verification script (14 checks)

## Files Modified
- `backend/app/auth/router.py` — Added rate limit dependencies to `/login`, `/refresh`, `/change-password`
- `backend/app/main.py` — Added request size middleware, JSON logging formatter for production
- `backend/app/common/config.py` — Added `max_request_body_size` setting
- `.env.example` — Added `MAX_REQUEST_BODY_SIZE`
- `README.md` — Added Pre-Live Checklist section (automated + manual + security)

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: `POST /auth/login` is rate limited (5/minute per IP) — ✅ Done
2. AC2: Rate-limited requests return 429 with structured error response — ✅ Done (`RATE_LIMIT_EXCEEDED` code)
3. AC3: Request body size limit middleware rejects oversized requests with 413 — ✅ Done (`REQUEST_TOO_LARGE` code)
4. AC4: Production logging outputs JSON format when `LOG_FORMAT=json` — ✅ Done (JSONFormatter with timestamp, level, logger, message, exception)
5. AC5: Sensitive data never appears in log output — ✅ Verified (grep for password/secret/token in log statements — none log actual values)
6. AC6: `scripts/readiness_check.py` exists and runs all checks — ✅ Done (14 checks)
7. AC7: Readiness check verifies: JWT secret, admin password, CORS, database, broker keys, migrations — ✅ Done
8. AC8: Readiness check exits 1 on failure, 0 on success — ✅ Done
9. AC9: README has pre-live checklist with both automated and manual steps — ✅ Done
10. AC10: `.env.example` includes request size variable — ✅ Done
11. AC11: No frontend code modified — ✅ Done
12. AC12: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Rate Limiter Design

**Implementation:** In-memory sliding window counter using `defaultdict(list)` of timestamps. No Redis needed (per DECISION-004).

**Rate limits:**
- `/auth/login` — 5 requests per 60 seconds per client IP
- `/auth/refresh` — 10 requests per 60 seconds per client IP
- `/auth/change-password` — 3 requests per 60 seconds per client IP

**Response on rate limit exceeded:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many login attempts. Try again later."
  }
}
```

**Limitation:** In-memory state resets on restart and doesn't share across multiple workers/processes. Sufficient for single-instance deployment (current architecture).

## Readiness Check Script

14 checks organized into categories:

| Check | Type | What it verifies |
|-------|------|-----------------|
| JWT secret | Security | Not default, >= 32 chars |
| Admin password | Security | Not using default `changeme123456` |
| CORS | Security | Not `*` in production |
| Environment | Config | Set to `production` (warning if not) |
| .gitignore | Security | `.env` is in `.gitignore` |
| Database | Connectivity | Health endpoint returns `database: connected` |
| Migrations | Database | Alembic is at head |
| Alpaca API keys | Broker | `ALPACA_API_KEY` is set (warning if not) |
| Alpaca connection | Broker | Health endpoint shows Alpaca status |
| OANDA credentials | Broker | `OANDA_ACCESS_TOKEN` is set (warning if not) |
| OANDA connection | Broker | Health endpoint shows OANDA status |
| Forex pool mapping | Broker | At least one `OANDA_POOL_ACCOUNT_N` set |
| Kill switch | Risk | Warns (can't check without auth) |
| Sensitive logs | Security | No passwords/tokens in log format strings |

**Exit codes:** 0 = all pass (or warnings only), 1 = any failure

## Production Logging

When `LOG_FORMAT=json`:
```json
{"timestamp": "2025-03-14 10:00:00,000", "level": "INFO", "logger": "app.main", "message": "Settings loaded successfully"}
```

When `LOG_FORMAT=text`: Standard Python logging format (default handler).

`LOG_LEVEL` controls root logger level (INFO, WARNING, ERROR, etc.).

## Security Review Summary

| Item | Status | Notes |
|------|--------|-------|
| JWT secret production guard | ✅ | TASK-025 added; raises RuntimeError in production with default |
| CORS configurable | ✅ | TASK-025 added; defaults to localhost:3000,5173 |
| Admin password | ✅ | Readiness check detects default password |
| .gitignore | ✅ | `.env`, `.env.local`, `.env.production` all ignored |
| Error responses | ✅ | TASK-025 verified; 500 returns INTERNAL_ERROR, no traceback |
| No sensitive data in logs | ✅ | Verified; no password/token/secret values logged |
| Rate limiting | ✅ | Added in this task |
| Request size limits | ✅ | Added in this task |

## Assumptions Made
1. **In-memory rate limiter:** Per DECISION-004 (no Redis), the rate limiter uses in-memory state. Resets on restart. Sufficient for single-instance deployment.
2. **Readiness check uses `requests` library:** Falls back gracefully with warnings if backend isn't running or `requests` isn't installed.
3. **Logging handler replacement:** When `LOG_FORMAT=json`, clears existing handlers and adds the JSON formatter. This ensures all output is structured.

## Ambiguities Encountered
None.

## Dependencies Discovered
None

## Tests Created
None — task excludes test creation

## Risks or Concerns
1. **Rate limiter memory growth:** Over time, the `_requests` dict grows unbounded if many unique IPs hit the endpoints. The cleanup-on-check approach mitigates this (old entries pruned on access), but very long-running instances with diverse traffic may accumulate memory. Consider periodic full cleanup for production.
2. **Multi-worker deployment:** Rate limiter doesn't share state across uvicorn workers. If `--workers` > 1, rate limits are per-worker, not global. Recommend single worker for MVP.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
**Milestone 14 is complete.** The platform has:
- Hardened auth (rate limiting, JWT production guard, account lockout)
- CORS configuration
- Request size limits
- Production logging (JSON format)
- Broker connectivity verified (Alpaca + OANDA)
- Audit trail with event emission
- Trade reconciliation
- Automated readiness check
- Pre-live checklist

Consider marking Milestone 14 as complete in the roadmap.
