"""Seed initial admin user when no users exist."""

import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.password import hash_password
from app.auth.repository import UserRepository
from app.common.config import get_settings
from app.common.database import get_engine, get_session_factory


async def seed_admin_user() -> None:
    """Create the initial admin user if no users exist."""
    settings = get_settings()

    if not settings.admin_seed_password:
        print("ERROR: ADMIN_SEED_PASSWORD environment variable is required for seeding.")
        sys.exit(1)

    factory = get_session_factory()
    async with factory() as db:
        repo = UserRepository()
        count = await repo.count(db)

        if count > 0:
            print(f"Database already has {count} user(s). Skipping seed.")
            return

        user = User(
            email="admin@ratatoskr.local",
            username="admin",
            password_hash=hash_password(settings.admin_seed_password),
            role="admin",
            status="active",
        )
        await repo.create(db, user)
        await db.commit()

        print("Admin user created:")
        print(f"  Email:    admin@ratatoskr.local")
        print(f"  Username: admin")
        print(f"  Role:     admin")
        print(f"  ID:       {user.id}")

    await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(seed_admin_user())
