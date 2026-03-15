"""FastAPI auth dependencies for route protection."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import InsufficientPermissionsError, TokenInvalidError
from app.auth.models import User
from app.auth.repository import UserRepository
from app.auth.tokens import decode_access_token
from app.common.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_user_repo = UserRepository()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate user from JWT access token.

    Raises TokenExpiredError if token is expired.
    Raises TokenInvalidError if token is invalid or user is not active.
    """
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidError()

    user = await _user_repo.get_by_id(db, user_id)
    if not user or user.status != "active":
        raise TokenInvalidError()

    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require the current user to have admin role.

    Raises InsufficientPermissionsError if user is not admin.
    """
    if user.role != "admin":
        raise InsufficientPermissionsError()
    return user
