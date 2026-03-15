"""E2E tests for risk endpoints and kill switch."""

import pytest


class TestRiskEndpoints:
    @pytest.mark.asyncio
    async def test_risk_overview(self, auth_client):
        resp = await auth_client.get("/api/v1/risk/overview")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_risk_config(self, auth_client):
        resp = await auth_client.get("/api/v1/risk/config")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_update_risk_config(self, auth_client):
        resp = await auth_client.put("/api/v1/risk/config", json={
            "maxPositionSizePercent": 15.0,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_risk_decisions_list(self, auth_client):
        resp = await auth_client.get("/api/v1/risk/decisions")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_exposure_breakdown(self, auth_client):
        resp = await auth_client.get("/api/v1/risk/exposure")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_drawdown_state(self, auth_client):
        resp = await auth_client.get("/api/v1/risk/drawdown")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body


class TestKillSwitchAPI:
    @pytest.mark.asyncio
    async def test_kill_switch_status(self, auth_client):
        resp = await auth_client.get("/api/v1/risk/kill-switch/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_activate_kill_switch(self, auth_client):
        resp = await auth_client.post("/api/v1/risk/kill-switch/activate", json={
            "scope": "global",
            "reason": "E2E test activation",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_deactivate_kill_switch(self, auth_client):
        # Ensure it's active first
        await auth_client.post("/api/v1/risk/kill-switch/activate", json={
            "scope": "global",
            "reason": "E2E test",
        })

        resp = await auth_client.post("/api/v1/risk/kill-switch/deactivate", json={
            "scope": "global",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_kill_switch_round_trip(self, auth_client):
        # Activate
        resp1 = await auth_client.post("/api/v1/risk/kill-switch/activate", json={
            "scope": "global",
            "reason": "Round trip test",
        })
        assert resp1.status_code == 200

        # Verify active
        status = await auth_client.get("/api/v1/risk/kill-switch/status")
        assert status.status_code == 200

        # Deactivate
        resp2 = await auth_client.post("/api/v1/risk/kill-switch/deactivate", json={
            "scope": "global",
        })
        assert resp2.status_code == 200


class TestRiskConfigAudit:
    @pytest.mark.asyncio
    async def test_config_audit_trail(self, auth_client):
        # Make a config change
        await auth_client.put("/api/v1/risk/config", json={
            "maxDailyLossPercent": 5.0,
        })

        # Check audit trail
        resp = await auth_client.get("/api/v1/risk/config/audit")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
