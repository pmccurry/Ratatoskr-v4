# AUTH_MODULE — Full Engineering Spec

## Purpose

Define the complete engineering specification for the auth module.
This spec must contain enough detail that a builder agent can implement
the entire module without asking engineering design questions.

## Module Ownership

The auth module owns:

- User registration and management
- Password hashing and verification
- Authentication (login, logout, token management)
- Authorization (role-based access control)
- JWT access token creation and validation
- Refresh token lifecycle
- Account lockout on failed attempts
- Auth-related audit events
- FastAPI auth dependencies used by all other modules

The auth module does NOT own:

- Business logic in any other module
- User-scoped data filtering logic (owned by each module's service layer,
  enforced via user parameter from auth dependencies)

---

## 1. User Model

```
User:
  - id: UUID
  - email: str (unique, used for login)
  - username: str (unique, display name)
  - password_hash: str (bcrypt)
  - role: str (admin | user)
  - status: str (active | suspended | pending)
  - failed_login_count: int (default 0, reset on successful login)
  - locked_until: datetime, nullable
  - last_login_at: datetime, nullable
  - created_at: datetime
  - updated_at: datetime

Indexes:
  UNIQUE (email)
  UNIQUE (username)
  INDEX (role, status)
```

### Roles

**Admin:** Full access. Sees all strategies across all users, system health,
risk config, telemetry, user management. The platform operator.

**User:** Sees only their own strategies, positions, signals, and performance.
Cannot access system telemetry, risk config, or other users' data.

---

## 2. Role-Based Access Control

### Access Matrix

```
Resource                          Admin    User
──────────────────────────────────────────────────
Own strategies (CRUD)             ✓        ✓
Own positions                     ✓        ✓
Own signals                       ✓        ✓
Own performance metrics           ✓        ✓
Own portfolio view                ✓        ✓
Manual close own positions        ✓        ✓
Strategy builder / indicators     ✓        ✓

All users' strategies             ✓        ✗
All users' positions              ✓        ✗
All users' performance            ✓        ✗

Risk config (view/edit)           ✓        ✗
Kill switch                       ✓        ✗
Peak equity reset                 ✓        ✗
Cash adjustments                  ✓        ✗

System health / telemetry         ✓        ✗
Pipeline status                   ✓        ✗
Database stats                    ✓        ✗
Background job status             ✓        ✗
Alert rules (edit)                ✓        ✗

User management                   ✓        ✗
Forex account pool config         ✓        ✗
Universe filter config            ✓        ✗
```

---

## 3. Data Ownership

### User-Scoped Entities (require user_id)

Every tradeable entity is tagged with a user_id:

```
Strategy.user_id
Signal.user_id (inherited from strategy)
PaperOrder.user_id (inherited from signal/strategy)
PaperFill.user_id (inherited from order)
Position.user_id (inherited from strategy)
PositionOverride.user_id
RealizedPnlEntry.user_id
DividendPayment.user_id
ShadowFill.user_id
ShadowPosition.user_id
StrategyEvaluation.user_id
PortfolioSnapshot.user_id
CashBalance.user_id
PortfolioMeta.user_id
```

### System-Wide Entities (not user-scoped)

```
OHLCVBar (market data shared across all users)
MarketSymbol
WatchlistEntry (system watchlist, shared)
DividendAnnouncement (market data, shared)
RiskConfig (system-wide — admin managed)
KillSwitch (system-wide or per-strategy)
BrokerAccount (system-wide pool)
AlertRule (system-wide)
AlertInstance (system-wide)
AuditEvent (system-wide, filterable by user context)
MetricDatapoint (system-wide)
```

Market data is expensive to fetch — shared across all users. One universe
filter, one WebSocket stream, one bar storage pipeline serves everyone.
Users diverge at the strategy level and below.

### Per-User Portfolio Context

Each user has their own independent portfolio:

```
User A: $100k starting capital, own equity curve, own drawdown
User B: $50k starting capital, completely independent metrics
```

They share market data and broker infrastructure but all trading
activity and accounting is isolated.

### MVP Simplification

One user (admin) for MVP. The system supports user_id on all entities
from day one, but only one user exists. Multi-user resource isolation
(separate forex pools per user, per-user risk limits) is a future spec.

---

## 4. Row-Level Security

### Enforcement

Every service method that queries user-scoped data filters by user_id.
Enforced at the service layer (not the router layer) so it cannot be
accidentally bypassed.

```python
# strategy_service.py
async def get_strategies(user: User) -> list[Strategy]:
    if user.role == "admin":
        return await repo.get_all()
    return await repo.get_by_user(user.id)

# position_service.py
async def get_positions(user: User, strategy_id: UUID = None) -> list[Position]:
    if user.role == "admin":
        return await repo.get_all(strategy_id=strategy_id)
    return await repo.get_by_user(user.id, strategy_id=strategy_id)
```

### Rule

Every query builder has user_id filtering as a **required parameter**
for non-admin users, not an optional one. This prevents "forgot to filter"
bugs. Admin bypasses the filter to see all data.

---

## 5. Authentication Flow

### Registration (Admin-Created for MVP)

```
1. Admin creates user via POST /api/v1/users
2. Password is hashed with bcrypt (cost factor 12)
3. User record created with status = "active"
4. No email verification for MVP
```

### Login

```
1. User submits email + password to POST /api/v1/auth/login
2. Server looks up user by email
3. If user not found: return 401 "Invalid credentials"
4. If user locked (locked_until > now): return 423 "Account locked"
5. If user suspended: return 403 "Account suspended"
6. Verify password against hash
7. If invalid:
   - Increment failed_login_count
   - If failed_login_count >= AUTH_MAX_FAILED_ATTEMPTS:
     - Set locked_until = now + AUTH_LOCKOUT_DURATION_MINUTES
     - Log: auth.user.locked
   - Return 401 "Invalid credentials"
8. If valid:
   - Reset failed_login_count to 0
   - Clear locked_until
   - Update last_login_at
   - Create access token (JWT, 15 min expiry)
   - Create refresh token (stored in DB, 7 day expiry)
   - Log: auth.user.login
   - Return: { access_token, refresh_token, token_type: "bearer", expires_in }
```

### Token Refresh

```
1. Client sends refresh token to POST /api/v1/auth/refresh
2. Server hashes the token and looks up in refresh_tokens table
3. Validate: exists, not expired, not revoked, user is active
4. If invalid: return 401
5. If valid:
   - Revoke the old refresh token (token rotation)
   - Create new access token
   - Create new refresh token
   - Log: auth.token.refreshed
   - Return: { access_token, refresh_token, expires_in }
```

Token rotation: each refresh token is single-use. If a refresh token is
reused (indicating theft), all refresh tokens for that user are revoked,
forcing re-login. Log: auth.token.revoked

### Logout

```
1. Client calls POST /api/v1/auth/logout
2. Server revokes the refresh token
3. Access token continues working until its 15-min expiry
   (JWT trade-off — acceptable for this use case)
4. Log: auth.user.logout
```

---

## 6. Token System

### Access Token (JWT)

```
Payload:
  - user_id: UUID
  - email: str
  - role: str (admin | user)
  - exp: expiration timestamp
  - iat: issued at timestamp
  - jti: unique token ID

Expiry: AUTH_ACCESS_TOKEN_EXPIRE_MINUTES (default: 15)
Algorithm: HS256
Secret: AUTH_JWT_SECRET_KEY (from environment)
```

JWTs are validated without a database lookup on every request.
The payload contains user_id and role for fast authorization checks.

### Refresh Token

```
RefreshToken:
  - id: UUID
  - user_id: UUID (FK → User)
  - token_hash: str (hashed with SHA-256, never stored in plaintext)
  - expires_at: datetime
  - revoked: bool (default false)
  - revoked_at: datetime, nullable
  - created_at: datetime

Indexes:
  INDEX (token_hash)
  INDEX (user_id, revoked)
```

Refresh tokens are stored as hashes. The plaintext token is returned
to the client once and never stored server-side.

Expiry: AUTH_REFRESH_TOKEN_EXPIRE_DAYS (default: 7)

### Token Cleanup

Daily job removes expired and revoked refresh tokens:

```
DELETE FROM refresh_tokens
WHERE expires_at < NOW() - INTERVAL '1 day'
   OR (revoked = true AND revoked_at < NOW() - INTERVAL '1 day')
```

---

## 7. API Authentication Middleware

### FastAPI Dependencies

```python
# Get current authenticated user (required for all protected routes)
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_jwt(token)
    user = await user_service.get_by_id(payload["user_id"])
    if not user or user.status != "active":
        raise HTTPException(401, "Invalid or inactive user")
    return user

# Require admin role (for admin-only routes)
async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user
```

### Route Protection

```python
# User route (any authenticated user):
@router.get("/strategies")
async def list_strategies(user: User = Depends(get_current_user)):
    return await strategy_service.get_strategies(user)

# Admin route:
@router.put("/risk/config")
async def update_risk_config(
    config: RiskConfigUpdate,
    user: User = Depends(require_admin)
):
    return await risk_service.update_config(config, updated_by=user.email)
```

### Unprotected Routes

Only these routes do not require authentication:

```
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/health          (basic health check for load balancers)
```

All other routes require a valid access token.

---

## 8. Password Security

```
Hashing algorithm: bcrypt
Cost factor: AUTH_BCRYPT_COST_FACTOR (default: 12)
Minimum password length: AUTH_MIN_PASSWORD_LENGTH (default: 12)
Maximum password length: 128 characters
No special character requirements (length > complexity)
```

Password changes require the current password for confirmation.
Admin can force-reset a user's password without the current password.

---

## 9. Account Lockout

```
AUTH_MAX_FAILED_ATTEMPTS=5
AUTH_LOCKOUT_DURATION_MINUTES=15
```

After AUTH_MAX_FAILED_ATTEMPTS consecutive failed login attempts:
- Account is temporarily locked (locked_until set)
- Auth event logged: auth.user.locked
- Lockout clears after AUTH_LOCKOUT_DURATION_MINUTES
- Admin can manually unlock via POST /api/v1/users/:id/unlock

Successful login resets failed_login_count to 0 and clears locked_until.

---

## 10. Auth Audit Events

```
auth.user.login              info      ✅ User '{email}' logged in
auth.user.login_failed       warning   🟡 Failed login for '{email}' (attempt {n})
auth.user.locked             warning   🟡 Account '{email}' locked: {attempts} failed
auth.user.unlocked           info      ✅ Account '{email}' unlocked by {actor}
auth.user.logout             info      ⚙️ User '{email}' logged out
auth.user.created            info      ✅ User '{email}' created by {admin}
auth.user.updated            info      ⚙️ User '{email}' updated: {changes}
auth.user.suspended          warning   🟡 User '{email}' suspended by {admin}
auth.user.activated          info      ✅ User '{email}' activated by {admin}
auth.user.password_changed   info      ⚙️ User '{email}' changed password
auth.user.password_reset     info      ⚙️ User '{email}' password reset by {admin}
auth.token.refreshed         debug     ⚙️ Token refreshed for '{email}'
auth.token.revoked           warning   🟡 All tokens revoked for '{email}' (possible theft)
```

---

## 11. Impact on Other Modules

Adding auth is a cross-cutting change. Every module's router gains
auth dependencies, and every service method for user-scoped data
gains a `user` parameter.

### Router Pattern

```python
# Every protected route includes:
user: User = Depends(get_current_user)

# Admin routes include:
user: User = Depends(require_admin)
```

### Service Pattern

```python
# Every service method for user-scoped data includes:
async def get_strategies(user: User) -> list[Strategy]:
    if user.role == "admin":
        # admin sees all
    else:
        # filter by user.id
```

### Database Pattern

All user-scoped tables include:
```
user_id: UUID (FK → User)
INDEX (user_id, ...) on all user-scoped query patterns
```

---

## 12. Folder Structure

```
backend/app/auth/
    __init__.py
    service.py              ← user CRUD, authentication, authorization logic
    models.py               ← SQLAlchemy models (User, RefreshToken)
    schemas.py              ← Pydantic request/response schemas
    router.py               ← API endpoints
    config.py               ← auth configuration
    dependencies.py         ← FastAPI dependencies (get_current_user, require_admin)
    password.py             ← password hashing and verification (bcrypt)
    tokens.py               ← JWT creation/validation, refresh token management
```

---

## 13. API Endpoints

```
# Authentication
POST /api/v1/auth/login              → email + password → tokens
                                       Response: { access_token, refresh_token,
                                                   token_type, expires_in }
POST /api/v1/auth/refresh            → refresh token → new tokens
                                       Response: { access_token, refresh_token,
                                                   expires_in }
POST /api/v1/auth/logout             → revoke refresh token
POST /api/v1/auth/change-password    → { current_password, new_password }

# Current User (self-service)
GET  /api/v1/auth/me                 → current user profile
PUT  /api/v1/auth/me                 → update own profile (email, username)

# User Management (admin only)
GET    /api/v1/users                 → list all users
GET    /api/v1/users/:id             → user detail
POST   /api/v1/users                 → create user
PUT    /api/v1/users/:id             → update user (role, status)
POST   /api/v1/users/:id/reset-password  → force password reset
POST   /api/v1/users/:id/unlock      → unlock locked account
POST   /api/v1/users/:id/suspend     → suspend user
POST   /api/v1/users/:id/activate    → reactivate suspended user
```

---

## 14. Configuration Variables

```
# JWT
AUTH_JWT_SECRET_KEY=<must-be-set-in-env>
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7

# Password
AUTH_BCRYPT_COST_FACTOR=12
AUTH_MIN_PASSWORD_LENGTH=12

# Lockout
AUTH_MAX_FAILED_ATTEMPTS=5
AUTH_LOCKOUT_DURATION_MINUTES=15
```

**AUTH_JWT_SECRET_KEY must be set in environment variables.**
The application must refuse to start if it is missing or set to a
default/placeholder value.

---

## 15. Database Tables Owned

| Table | Purpose |
|---|---|
| users | User accounts, credentials, roles |
| refresh_tokens | Refresh token lifecycle and revocation |

---

## 16. Future Enhancements (Not MVP)

Noted for architecture awareness, not for implementation:

- Email verification on registration
- Password reset via email link
- OAuth / social login (Google, GitHub)
- Per-user risk limits (separate from system-wide)
- Per-user forex account pool allocation
- API key authentication (for programmatic access / external tools)
- Two-factor authentication (TOTP)
- User groups / teams with shared strategy access
- Fine-grained permissions beyond admin/user

The current data model and auth middleware support all of these as
additions without restructuring.

---

## Acceptance Criteria

This spec is accepted when:

- User data model with roles is defined
- Role-based access matrix is explicit
- Data ownership (user-scoped vs system-wide entities) is documented
- Row-level security enforcement pattern is specified
- Authentication flow (login, refresh, logout) is step-by-step
- JWT access token and database refresh token models are defined
- Token rotation and theft detection are specified
- FastAPI auth dependencies are defined
- Password security requirements are specified
- Account lockout mechanism is specified
- Auth audit events are enumerated
- Impact on other modules (user_id propagation) is documented
- All API endpoints are listed
- All configuration variables are listed
- All database tables are enumerated
- A builder agent can implement this module without asking engineering design questions
