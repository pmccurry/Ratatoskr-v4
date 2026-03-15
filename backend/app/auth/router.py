"""Auth module API endpoints."""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.auth.schemas import (
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UpdateUserRequest,
    UserResponse,
)
from app.auth.service import AuthService
from app.common.database import get_db
from app.common.rate_limiter import check_login_rate, check_password_rate, check_refresh_rate
from app.common.schemas import PaginationMeta

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

_auth_service = AuthService()


def _user_response(user: User) -> dict:
    """Convert User model to response envelope."""
    return {
        "data": UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role,
            status=user.status,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        ).model_dump(by_alias=True)
    }


# === Authentication endpoints ===


@router.post("/login", dependencies=[Depends(check_login_rate)])
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    token_response = await _auth_service.login(db, body.email, body.password)
    return {"data": token_response.model_dump(by_alias=True)}


@router.post("/refresh", dependencies=[Depends(check_refresh_rate)])
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_response = await _auth_service.refresh_tokens(db, body.refresh_token)
    return {"data": token_response.model_dump(by_alias=True)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await _auth_service.logout(db, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", dependencies=[Depends(check_password_rate)])
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _auth_service.change_password(db, user.id, body.current_password, body.new_password)
    return {"data": {"message": "Password changed successfully"}}


# === Current user endpoints ===


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.put("/me")
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await _auth_service.update_profile(db, user.id, body)
    return _user_response(updated)


# === User management endpoints (admin only) ===


@users_router.get("")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    users, total = await _auth_service.get_users(db, page, page_size)
    return {
        "data": [
            UserResponse(
                id=str(u.id),
                email=u.email,
                username=u.username,
                role=u.role,
                status=u.status,
                last_login_at=u.last_login_at,
                created_at=u.created_at,
            ).model_dump(by_alias=True)
            for u in users
        ],
        "pagination": PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
        ).model_dump(by_alias=True),
    }


@users_router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await _auth_service.get_user(db, user_id)
    return _user_response(user)


@users_router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await _auth_service.create_user(db, body)
    return _user_response(user)


@users_router.put("/{user_id}")
async def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await _auth_service.update_user(db, user_id, body)
    return _user_response(user)


@users_router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: UUID,
    body: ResetPasswordRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _auth_service.reset_password(db, user_id, body.new_password)
    return {"data": {"message": "Password reset successfully"}}


@users_router.post("/{user_id}/unlock")
async def unlock_user(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _auth_service.unlock_user(db, user_id)
    return {"data": {"message": "User unlocked"}}


@users_router.post("/{user_id}/suspend")
async def suspend_user(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _auth_service.suspend_user(db, user_id)
    return {"data": {"message": "User suspended"}}


@users_router.post("/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _auth_service.activate_user(db, user_id)
    return {"data": {"message": "User activated"}}
