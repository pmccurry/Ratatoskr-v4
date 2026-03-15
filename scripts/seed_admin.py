"""Standalone script to seed the initial admin user.

Usage: uv run python scripts/seed_admin.py
Must be run from the backend/ directory (via start-dev.sh).
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Allow imports from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def seed() -> None:
    # Load .env if python-dotenv is available, otherwise rely on environment
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    except ImportError:
        pass

    database_url = os.environ.get("DATABASE_URL", "")
    admin_email = os.environ.get("ADMIN_SEED_EMAIL", "admin@ratatoskr.local")
    admin_password = os.environ.get("ADMIN_SEED_PASSWORD", "")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required.")
        sys.exit(1)

    if not admin_password:
        print("ERROR: ADMIN_SEED_PASSWORD environment variable is required.")
        sys.exit(1)

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(database_url)

    # Hash password using bcrypt (matching backend auth pattern)
    import bcrypt

    cost_factor = int(os.environ.get("AUTH_BCRYPT_COST_FACTOR", "12"))
    salt = bcrypt.gensalt(rounds=cost_factor)
    hashed = bcrypt.hashpw(admin_password.encode(), salt).decode()

    async with engine.connect() as conn:
        # Check if any admin user exists
        result = await conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'"))
        count = result.scalar()

        if count and count > 0:
            print("Admin user already exists, skipping seed.")
            await engine.dispose()
            return

        now = datetime.now(timezone.utc)
        user_id = uuid4()

        await conn.execute(
            text(
                "INSERT INTO users (id, email, username, password_hash, role, status, "
                "failed_login_count, created_at, updated_at) "
                "VALUES (:id, :email, :username, :password_hash, :role, :status, "
                ":failed_login_count, :created_at, :updated_at)"
            ),
            {
                "id": str(user_id),
                "email": admin_email,
                "username": "admin",
                "password_hash": hashed,
                "role": "admin",
                "status": "active",
                "failed_login_count": 0,
                "created_at": now,
                "updated_at": now,
            },
        )
        await conn.commit()

        print(f"Admin user created: {admin_email} (id: {user_id})")

    await engine.dispose()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
