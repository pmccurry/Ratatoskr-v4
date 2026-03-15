"""Auth module Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


# === Request schemas ===


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(alias="currentPassword")
    new_password: str = Field(alias="newPassword")

    model_config = {"populate_by_name": True}


class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    role: str | None = None
    status: str | None = None


class UpdateProfileRequest(BaseModel):
    email: str | None = None
    username: str | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(alias="newPassword")

    model_config = {"populate_by_name": True}


# === Response schemas ===


class TokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    expires_in: int = Field(alias="expiresIn")

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str
    status: str
    last_login_at: datetime | None = Field(default=None, alias="lastLoginAt")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}
