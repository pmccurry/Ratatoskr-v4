"""E2E tests for authentication flow."""

import pytest


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@ratatoskr.local",
            "password": "changeme123456",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "accessToken" in data
        assert "refreshToken" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@ratatoskr.local",
            "password": "wrong_password_here",
        })
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"].startswith("AUTH_")

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "doesntmatter",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_response_is_camelcase(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@ratatoskr.local",
            "password": "changeme123456",
        })
        data = resp.json()["data"]
        assert "accessToken" in data
        assert "access_token" not in data


class TestProtectedRoutes:
    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, client):
        resp = await client.get("/api/v1/strategies")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_200(self, auth_client):
        resp = await auth_client.get("/api/v1/strategies")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, client):
        client.headers["Authorization"] = "Bearer invalid.jwt.token"
        resp = await client.get("/api/v1/strategies")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me(self, auth_client):
        resp = await auth_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "email" in data


class TestTokenRefresh:
    @pytest.mark.asyncio
    async def test_refresh_returns_new_tokens(self, client):
        # First login to get refresh token
        login = await client.post("/api/v1/auth/login", json={
            "email": "admin@ratatoskr.local",
            "password": "changeme123456",
        })
        refresh_token = login.json()["data"]["refreshToken"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refreshToken": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "accessToken" in data
        assert "refreshToken" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_returns_401(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refreshToken": "invalid-refresh-token",
        })
        assert resp.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(self, client):
        # Login
        login = await client.post("/api/v1/auth/login", json={
            "email": "admin@ratatoskr.local",
            "password": "changeme123456",
        })
        refresh_token = login.json()["data"]["refreshToken"]

        # Logout
        resp = await client.post("/api/v1/auth/logout", json={
            "refreshToken": refresh_token,
        })
        assert resp.status_code == 204

        # Subsequent refresh with same token should fail
        resp = await client.post("/api/v1/auth/refresh", json={
            "refreshToken": refresh_token,
        })
        assert resp.status_code == 401
