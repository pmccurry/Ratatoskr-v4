"""E2E tests for manual position close flow."""

from uuid import uuid4

import pytest


class TestManualClose:
    @pytest.mark.asyncio
    async def test_close_nonexistent_position(self, auth_client):
        fake_id = str(uuid4())
        resp = await auth_client.post(f"/api/v1/portfolio/positions/{fake_id}/close")
        assert resp.status_code in (404, 422)
        body = resp.json()
        assert "error" in body

    @pytest.mark.asyncio
    async def test_positions_list_returns_data(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/positions")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_closed_positions_list(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/positions/closed")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_position_detail_nonexistent(self, auth_client):
        fake_id = str(uuid4())
        resp = await auth_client.get(f"/api/v1/portfolio/positions/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_realized_pnl_list(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/pnl/realized")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)
