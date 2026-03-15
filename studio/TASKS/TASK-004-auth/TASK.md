# TASK-004 — Auth Module Implementation

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the auth module: user model, password hashing, JWT access tokens,
refresh tokens, login/logout/refresh flows, FastAPI auth dependencies
(get_current_user, require_admin), and user management endpoints.

After this task:
- Users can be created (admin-only)
- Users can log in and receive access + refresh tokens
- Users can refresh tokens and log out
- Every protected route can use `Depends(get_current_user)` for authentication
- Admin routes can use `Depends(require_admin)` for authorization
- The user model exists in the database with a working Alembic migration

This task implements auth infrastructure. It does NOT add auth dependencies
to other module routers yet — that happens when each module is implemented.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/auth_module_spec.md — PRIMARY SPEC, read completely
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions, repository pattern

## Constraints

- Do NOT implement any domain logic outside auth (no strategies, signals, etc.)
- Do NOT add auth dependencies to other module routers (they stay as empty stubs)
- Do NOT create models for any other module
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow the repository pattern: router → service → repository → database
- Follow the API conventions: response envelope, error format, camelCase JSON
- Follow the error handling pattern: use DomainError subclasses, not raw HTTPException

---

## Deliverables

### 1. User Model (backend/app/auth/models.py)

SQLAlchemy model inheriting from BaseModel (common/base_model.py).

```
User:
  - id: UUID (from BaseModel)
  - email: str (unique, indexed)
  - username: str (unique, indexed)
  - password_hash: str
  - role: str (default "user", values: "admin" | "user")
  - status: str (default "active", values: "active" | "suspended" | "pending")
  - failed_login_count: int (default 0)
  - locked_until: datetime, nullable
  - last_login_at: datetime, nullable
  - created_at: datetime (from BaseModel)
  - updated_at: datetime (from BaseModel)

Indexes:
  UNIQUE (email)
  UNIQUE (username)
  INDEX (role, status)
```

```
RefreshToken:
  - id: UUID (from BaseModel)
  - user_id: UUID (FK → User, indexed)
  - token_hash: str (SHA-256 hash, indexed)
  - expires_at: datetime
  - revoked: bool (default false)
  - revoked_at: datetime, nullable
  - created_at: datetime (from BaseModel)
  - updated_at: datetime (from BaseModel)

Indexes:
  INDEX (token_hash)
  INDEX (user_id, revoked)
```

### 2. Auth Schemas (backend/app/auth/schemas.py)

Pydantic models for request/response validation. Follow API conventions:
camelCase field aliases for JSON serialization.

```
Request schemas:
  LoginRequest:       email (str), password (str)
  RefreshRequest:     refresh_token (str)
  ChangePasswordRequest: current_password (str), new_password (str)
  CreateUserRequest:  email (str), username (str), password (str), role (str, default "user")
  UpdateUserRequest:  email (str, optional), username (str, optional), role (str, optional), status (str, optional)
  UpdateProfileRequest: email (str, optional), username (str, optional)

Response schemas:
  TokenResponse:      access_token (str), refresh_token (str), token_type ("bearer"), expires_in (int)
  UserResponse:       id, email, username, role, status, last_login_at, created_at
  UserListResponse:   PaginatedResponse[UserResponse]
```

Password fields must NEVER appear in response schemas.

### 3. Password Utilities (backend/app/auth/password.py)

```python
def hash_password(password: str) -> str:
    """Hash password using bcrypt with configured cost factor."""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
```

Use passlib with bcrypt backend. Cost factor from settings (AUTH_BCRYPT_COST_FACTOR, default 12).

Validate password meets minimum length (AUTH_MIN_PASSWORD_LENGTH, default 12)
before hashing. Raise DomainError if too short.

### 4. Token Utilities (backend/app/auth/tokens.py)

**Access token (JWT):**
```python
def create_access_token(user_id: UUID, email: str, role: str) -> str:
    """Create a JWT access token with expiry."""
    # Payload: user_id, email, role, exp, iat, jti (unique token ID)
    # Expiry: AUTH_ACCESS_TOKEN_EXPIRE_MINUTES from settings
    # Algorithm: AUTH_JWT_ALGORITHM from settings
    # Secret: AUTH_JWT_SECRET_KEY from settings

def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    # Raises DomainError(AUTH_TOKEN_EXPIRED) if expired
    # Raises DomainError(AUTH_TOKEN_INVALID) if invalid
```

**Refresh token:**
```python
def generate_refresh_token() -> tuple[str, str]:
    """Generate a refresh token and its hash."""
    # Returns: (plaintext_token, sha256_hash)
    # The plaintext is returned to the client once
    # The hash is stored in the database

def hash_refresh_token(token: str) -> str:
    """Hash a refresh token with SHA-256."""
```

Use python-jose for JWT. Use secrets.token_urlsafe for refresh tokens.
Use hashlib.sha256 for refresh token hashing.

### 5. Auth Repository (backend/app/auth/repository.py)

Database access layer. All methods take an AsyncSession parameter.

```python
class UserRepository:
    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None
    async def get_by_username(self, db: AsyncSession, username: str) -> User | None
    async def get_all(self, db: AsyncSession, page: int, page_size: int) -> tuple[list[User], int]
    async def create(self, db: AsyncSession, user: User) -> User
    async def update(self, db: AsyncSession, user: User) -> User

class RefreshTokenRepository:
    async def create(self, db: AsyncSession, token: RefreshToken) -> RefreshToken
    async def get_by_hash(self, db: AsyncSession, token_hash: str) -> RefreshToken | None
    async def revoke(self, db: AsyncSession, token_id: UUID) -> None
    async def revoke_all_for_user(self, db: AsyncSession, user_id: UUID) -> int
    async def cleanup_expired(self, db: AsyncSession) -> int
```

### 6. Auth Service (backend/app/auth/service.py)

Business logic layer. Orchestrates repositories, password utils, and token utils.

```python
class AuthService:
    async def login(self, db, email: str, password: str) -> TokenResponse:
        """
        1. Look up user by email
        2. If not found → DomainError(AUTH_INVALID_CREDENTIALS)
        3. If locked → DomainError(AUTH_ACCOUNT_LOCKED)
        4. If suspended → DomainError(AUTH_ACCOUNT_SUSPENDED) [use 403]
        5. Verify password
        6. If wrong:
           - increment failed_login_count
           - if count >= max_attempts → set locked_until, emit event
           - DomainError(AUTH_INVALID_CREDENTIALS)
        7. If correct:
           - reset failed_login_count, clear locked_until
           - update last_login_at
           - create access token
           - create refresh token (store hash in DB)
           - return TokenResponse
        """

    async def refresh_tokens(self, db, refresh_token: str) -> TokenResponse:
        """
        1. Hash the provided token
        2. Look up by hash
        3. Validate: exists, not expired, not revoked, user is active
        4. If invalid → DomainError(AUTH_TOKEN_INVALID)
        5. Revoke the old refresh token (token rotation)
        6. Create new access + refresh tokens
        7. Return TokenResponse
        """

    async def logout(self, db, refresh_token: str) -> None:
        """
        1. Hash the provided token
        2. Look up and revoke it
        """

    async def change_password(self, db, user_id: UUID, current: str, new: str) -> None:
        """
        1. Get user
        2. Verify current password
        3. Validate new password length
        4. Hash new password and update user
        5. Revoke all refresh tokens for this user
        """

    async def create_user(self, db, data: CreateUserRequest) -> User:
        """
        1. Check email uniqueness
        2. Check username uniqueness
        3. Validate password length
        4. Hash password
        5. Create user record
        6. Return user (without password)
        """

    async def get_user(self, db, user_id: UUID) -> User:
        """Get user by ID or raise NOT_FOUND."""

    async def get_users(self, db, page: int, page_size: int) -> tuple[list[User], int]:
        """Get paginated user list."""

    async def update_user(self, db, user_id: UUID, data: UpdateUserRequest) -> User:
        """Update user fields (admin operation)."""

    async def reset_password(self, db, user_id: UUID, new_password: str) -> None:
        """Admin force password reset. Revokes all refresh tokens."""

    async def unlock_user(self, db, user_id: UUID) -> None:
        """Clear locked_until and reset failed_login_count."""

    async def suspend_user(self, db, user_id: UUID) -> None:
        """Set status to suspended. Revoke all refresh tokens."""

    async def activate_user(self, db, user_id: UUID) -> None:
        """Set status to active."""
```

### 7. Auth Dependencies (backend/app/auth/dependencies.py)

FastAPI dependencies for route protection.

```python
async def get_current_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    1. Decode the JWT access token
    2. Extract user_id from payload
    3. Fetch user from database
    4. Verify user exists and status is "active"
    5. Return user
    
    Raises DomainError(AUTH_TOKEN_EXPIRED) or DomainError(AUTH_TOKEN_INVALID)
    """

async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    1. Check user.role == "admin"
    2. If not → DomainError(AUTH_INSUFFICIENT_PERMISSIONS)
    3. Return user
    """
```

### 8. Auth Errors (backend/app/auth/errors.py)

Domain-specific error classes:

```python
class InvalidCredentialsError(DomainError):
    # code: AUTH_INVALID_CREDENTIALS, status: 401

class AccountLockedError(DomainError):
    # code: AUTH_ACCOUNT_LOCKED, status: 423

class AccountSuspendedError(DomainError):
    # code: AUTH_ACCOUNT_SUSPENDED, status: 403

class TokenExpiredError(DomainError):
    # code: AUTH_TOKEN_EXPIRED, status: 401

class TokenInvalidError(DomainError):
    # code: AUTH_TOKEN_INVALID, status: 401

class InsufficientPermissionsError(DomainError):
    # code: AUTH_INSUFFICIENT_PERMISSIONS, status: 403

class UserNotFoundError(DomainError):
    # code: AUTH_USER_NOT_FOUND, status: 404

class UserAlreadyExistsError(DomainError):
    # code: AUTH_USER_ALREADY_EXISTS, status: 409

class PasswordTooShortError(DomainError):
    # code: AUTH_PASSWORD_TOO_SHORT, status: 400
```

These must be registered in the error-to-status mapping in common/errors.py
(add the new codes to the existing map).

### 9. Auth Router (backend/app/auth/router.py)

Replace the empty router stub with full auth endpoints.
Follow API conventions: response envelope, error format, camelCase JSON.

```
Authentication:
  POST /api/v1/auth/login           → LoginRequest body → TokenResponse
  POST /api/v1/auth/refresh         → RefreshRequest body → TokenResponse
  POST /api/v1/auth/logout          → RefreshRequest body → 204 No Content
  POST /api/v1/auth/change-password → ChangePasswordRequest body → 200 (requires auth)

Current User (self-service, requires auth):
  GET  /api/v1/auth/me              → UserResponse
  PUT  /api/v1/auth/me              → UpdateProfileRequest body → UserResponse

User Management (admin only):
  GET    /api/v1/users              → PaginatedResponse[UserResponse]
  GET    /api/v1/users/:id          → UserResponse
  POST   /api/v1/users              → CreateUserRequest body → UserResponse (201)
  PUT    /api/v1/users/:id          → UpdateUserRequest body → UserResponse
  POST   /api/v1/users/:id/reset-password → {new_password} body → 200
  POST   /api/v1/users/:id/unlock   → 200
  POST   /api/v1/users/:id/suspend  → 200
  POST   /api/v1/users/:id/activate → 200
```

Note: The user management endpoints use a SEPARATE router with prefix "/users"
(not under "/auth"). Both routers are registered in main.py.

All responses use the standard envelope: `{"data": {...}}` for success,
`{"error": {...}}` for errors.

### 10. Register User Management Router in main.py

Add the users router to main.py alongside the existing auth router:

```python
from backend.app.auth.router import router as auth_router, users_router
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
```

Or if implemented as two routers in the same file, register both.

### 11. Alembic Migration

Create the first Alembic migration for the users and refresh_tokens tables.

```bash
cd backend
alembic revision --autogenerate -m "create_users_and_refresh_tokens"
```

The migration should create:
- users table with all columns and indexes
- refresh_tokens table with all columns, indexes, and FK to users

Verify the migration applies cleanly:
```bash
alembic upgrade head
```

### 12. Seed Admin User

Create a utility script or management command that seeds an initial admin user.
This is needed because user creation requires admin auth, but no admin exists initially.

Location: `backend/app/auth/seed.py`

```python
async def seed_admin_user():
    """Create the initial admin user if no users exist."""
    # Only runs if the users table is empty
    # Creates: admin@ratatoskr.local / role=admin
    # Password from environment variable ADMIN_SEED_PASSWORD (required)
    # Prints the credentials to stdout (first run only)
```

Add a CLI entrypoint or call from a script:
```bash
uv run python -m app.auth.seed
```

Add ADMIN_SEED_PASSWORD to .env.example and .env:
```
ADMIN_SEED_PASSWORD=changeme-admin-password-123
```

### 13. Auth Config Addition

Add to the Settings class in common/config.py (if not already there):
```
admin_seed_password: str = ""
```

---

## Acceptance Criteria

1. User model exists with all fields, indexes, and constraints as specified
2. RefreshToken model exists with all fields, FK to User, and indexes
3. Alembic migration creates both tables and applies cleanly
4. password.py hashes and verifies passwords with bcrypt at configured cost factor
5. password.py validates minimum password length and raises DomainError if too short
6. tokens.py creates JWT access tokens with correct payload (user_id, email, role, exp, iat, jti)
7. tokens.py decodes and validates JWT tokens, raising appropriate DomainErrors
8. tokens.py generates refresh tokens and hashes them with SHA-256
9. Auth service login flow works: correct credentials return tokens, wrong credentials return 401, lockout after N failures
10. Auth service refresh flow works: valid refresh token returns new tokens, old token is revoked (rotation)
11. Auth service logout flow revokes the refresh token
12. Auth service change password verifies current password and revokes all refresh tokens
13. get_current_user dependency extracts user from JWT and returns User object
14. require_admin dependency rejects non-admin users with 403
15. All auth API endpoints exist and return correct response format (envelope)
16. POST /api/v1/auth/login accepts email+password, returns tokens
17. POST /api/v1/auth/refresh accepts refresh token, returns new tokens
18. POST /api/v1/auth/logout accepts refresh token, returns 204
19. GET /api/v1/auth/me returns current user (requires auth)
20. POST /api/v1/users creates user (requires admin)
21. GET /api/v1/users returns paginated user list (requires admin)
22. Admin seed script creates initial admin user when no users exist
23. All auth errors use DomainError subclasses (not raw HTTPException)
24. New error codes are registered in the common error-to-status mapping
25. Password hash is NEVER returned in any API response
26. Repository pattern followed: router → service → repository → database
27. No domain logic for other modules created
28. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-004-auth/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
