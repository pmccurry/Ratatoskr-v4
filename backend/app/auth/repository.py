"""Auth module database access layer."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User
from app.common.utils import utcnow


class UserRepository:
    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_all(
        self, db: AsyncSession, page: int, page_size: int
    ) -> tuple[list[User], int]:
        # Count total
        count_result = await db.execute(select(func.count()).select_from(User))
        total = count_result.scalar_one()

        # Fetch page
        offset = (page - 1) * page_size
        result = await db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        users = list(result.scalars().all())
        return users, total

    async def create(self, db: AsyncSession, user: User) -> User:
        db.add(user)
        await db.flush()
        return user

    async def update(self, db: AsyncSession, user: User) -> User:
        await db.flush()
        return user

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(User))
        return result.scalar_one()


class RefreshTokenRepository:
    async def create(self, db: AsyncSession, token: RefreshToken) -> RefreshToken:
        db.add(token)
        await db.flush()
        return token

    async def get_by_hash(self, db: AsyncSession, token_hash: str) -> RefreshToken | None:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, db: AsyncSession, token_id: UUID) -> None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked=True, revoked_at=utcnow())
        )

    async def revoke_all_for_user(self, db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)  # noqa: E712
            .values(revoked=True, revoked_at=utcnow())
        )
        return result.rowcount

    async def cleanup_expired(self, db: AsyncSession) -> int:
        now = utcnow()
        result = await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.expires_at < now,
            )
            .values(revoked=True, revoked_at=now)
        )
        return result.rowcount
