"""Auth module business logic layer."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import (
    AccountLockedError,
    AccountSuspendedError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.auth.models import RefreshToken, User
from app.auth.password import hash_password, validate_password_length, verify_password
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.schemas import CreateUserRequest, TokenResponse, UpdateProfileRequest, UpdateUserRequest
from app.auth.tokens import create_access_token, generate_refresh_token, hash_refresh_token
from app.common.config import get_settings
from app.common.utils import utcnow


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.token_repo = RefreshTokenRepository()

    async def login(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        settings = get_settings()
        user = await self.user_repo.get_by_email(db, email)

        if not user:
            raise InvalidCredentialsError()

        # Check lockout
        if user.locked_until and user.locked_until > utcnow():
            raise AccountLockedError(locked_until=user.locked_until.isoformat())

        # Check suspended
        if user.status == "suspended":
            raise AccountSuspendedError()

        # Verify password
        if not verify_password(password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= settings.auth_max_failed_attempts:
                user.locked_until = utcnow() + timedelta(
                    minutes=settings.auth_lockout_duration_minutes
                )
            await self.user_repo.update(db, user)
            raise InvalidCredentialsError()

        # Successful login
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = utcnow()
        await self.user_repo.update(db, user)

        # Create tokens
        access_token, expires_in = create_access_token(user.id, user.email, user.role)
        plaintext_refresh, refresh_hash = generate_refresh_token()

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=utcnow() + timedelta(days=settings.auth_refresh_token_expire_days),
        )
        await self.token_repo.create(db, refresh_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=plaintext_refresh,
            token_type="bearer",
            expires_in=expires_in,
        )

    async def refresh_tokens(self, db: AsyncSession, refresh_token_str: str) -> TokenResponse:
        settings = get_settings()
        token_hash = hash_refresh_token(refresh_token_str)
        stored_token = await self.token_repo.get_by_hash(db, token_hash)

        if not stored_token or stored_token.revoked or stored_token.expires_at < utcnow():
            from app.auth.errors import TokenInvalidError

            raise TokenInvalidError()

        # Load user
        user = await self.user_repo.get_by_id(db, stored_token.user_id)
        if not user or user.status != "active":
            from app.auth.errors import TokenInvalidError

            raise TokenInvalidError()

        # Revoke old token (rotation)
        await self.token_repo.revoke(db, stored_token.id)

        # Create new tokens
        access_token, expires_in = create_access_token(user.id, user.email, user.role)
        plaintext_refresh, refresh_hash = generate_refresh_token()

        new_refresh = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=utcnow() + timedelta(days=settings.auth_refresh_token_expire_days),
        )
        await self.token_repo.create(db, new_refresh)

        return TokenResponse(
            access_token=access_token,
            refresh_token=plaintext_refresh,
            token_type="bearer",
            expires_in=expires_in,
        )

    async def logout(self, db: AsyncSession, refresh_token_str: str) -> None:
        token_hash = hash_refresh_token(refresh_token_str)
        stored_token = await self.token_repo.get_by_hash(db, token_hash)
        if stored_token and not stored_token.revoked:
            await self.token_repo.revoke(db, stored_token.id)

    async def change_password(
        self, db: AsyncSession, user_id: UUID, current_password: str, new_password: str
    ) -> None:
        user = await self.user_repo.get_by_id(db, user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError()

        validate_password_length(new_password)
        user.password_hash = hash_password(new_password)
        await self.user_repo.update(db, user)

        # Revoke all refresh tokens
        await self.token_repo.revoke_all_for_user(db, user_id)

    async def create_user(self, db: AsyncSession, data: CreateUserRequest) -> User:
        # Check uniqueness
        existing = await self.user_repo.get_by_email(db, data.email)
        if existing:
            raise UserAlreadyExistsError("email", data.email)

        existing = await self.user_repo.get_by_username(db, data.username)
        if existing:
            raise UserAlreadyExistsError("username", data.username)

        # Validate and hash password
        password_hash = hash_password(data.password)

        user = User(
            email=data.email,
            username=data.username,
            password_hash=password_hash,
            role=data.role,
            status="active",
        )
        return await self.user_repo.create(db, user)

    async def get_user(self, db: AsyncSession, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(db, user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        return user

    async def get_users(
        self, db: AsyncSession, page: int, page_size: int
    ) -> tuple[list[User], int]:
        return await self.user_repo.get_all(db, page, page_size)

    async def update_user(
        self, db: AsyncSession, user_id: UUID, data: UpdateUserRequest
    ) -> User:
        user = await self.get_user(db, user_id)

        if data.email is not None and data.email != user.email:
            existing = await self.user_repo.get_by_email(db, data.email)
            if existing:
                raise UserAlreadyExistsError("email", data.email)
            user.email = data.email

        if data.username is not None and data.username != user.username:
            existing = await self.user_repo.get_by_username(db, data.username)
            if existing:
                raise UserAlreadyExistsError("username", data.username)
            user.username = data.username

        if data.role is not None:
            user.role = data.role

        if data.status is not None:
            user.status = data.status

        return await self.user_repo.update(db, user)

    async def update_profile(
        self, db: AsyncSession, user_id: UUID, data: UpdateProfileRequest
    ) -> User:
        user = await self.get_user(db, user_id)

        if data.email is not None and data.email != user.email:
            existing = await self.user_repo.get_by_email(db, data.email)
            if existing:
                raise UserAlreadyExistsError("email", data.email)
            user.email = data.email

        if data.username is not None and data.username != user.username:
            existing = await self.user_repo.get_by_username(db, data.username)
            if existing:
                raise UserAlreadyExistsError("username", data.username)
            user.username = data.username

        return await self.user_repo.update(db, user)

    async def reset_password(
        self, db: AsyncSession, user_id: UUID, new_password: str
    ) -> None:
        user = await self.get_user(db, user_id)
        password_hash = hash_password(new_password)
        user.password_hash = password_hash
        await self.user_repo.update(db, user)
        await self.token_repo.revoke_all_for_user(db, user_id)

    async def unlock_user(self, db: AsyncSession, user_id: UUID) -> None:
        user = await self.get_user(db, user_id)
        user.locked_until = None
        user.failed_login_count = 0
        await self.user_repo.update(db, user)

    async def suspend_user(self, db: AsyncSession, user_id: UUID) -> None:
        user = await self.get_user(db, user_id)
        user.status = "suspended"
        await self.user_repo.update(db, user)
        await self.token_repo.revoke_all_for_user(db, user_id)

    async def activate_user(self, db: AsyncSession, user_id: UUID) -> None:
        user = await self.get_user(db, user_id)
        user.status = "active"
        await self.user_repo.update(db, user)
