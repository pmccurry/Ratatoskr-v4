"""E2E tests for strategy lifecycle via API."""

from uuid import uuid4

import pytest


def _valid_strategy_payload(key: str | None = None) -> dict:
    return {
        "key": key or f"test_{uuid4().hex[:8]}",
        "name": "E2E Test Strategy",
        "description": "Strategy for E2E testing",
        "market": "equities",
        "config": {
            "timeframe": "1h",
            "symbols": {"mode": "explicit", "list": ["AAPL"]},
            "entryConditions": {
                "logic": "and",
                "conditions": [
                    {
                        "left": {"type": "indicator", "indicator": "rsi", "params": {"period": 14}},
                        "operator": "less_than",
                        "right": {"type": "value", "value": 30},
                    }
                ],
            },
            "stopLoss": {"type": "percent", "value": 2.0},
            "positionSizing": {"method": "percent_equity", "value": 5, "maxPositions": 3},
        },
    }


class TestStrategyLifecycleAPI:
    @pytest.mark.asyncio
    async def test_create_draft_strategy(self, auth_client):
        resp = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "draft"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_strategy_response_envelope(self, auth_client):
        resp = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], dict)

    @pytest.mark.asyncio
    async def test_create_strategy_fields_camelcase(self, auth_client):
        resp = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        data = resp.json()["data"]
        assert "currentVersion" in data or "current_version" not in data

    @pytest.mark.asyncio
    async def test_get_strategy_detail(self, auth_client):
        create = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        strategy_id = create.json()["data"]["id"]

        resp = await auth_client.get(f"/api/v1/strategies/{strategy_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == strategy_id

    @pytest.mark.asyncio
    async def test_list_strategies(self, auth_client):
        resp = await auth_client.get("/api/v1/strategies")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_enable_strategy(self, auth_client):
        create = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        sid = create.json()["data"]["id"]

        resp = await auth_client.post(f"/api/v1/strategies/{sid}/enable")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pause_strategy(self, auth_client):
        create = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        sid = create.json()["data"]["id"]
        await auth_client.post(f"/api/v1/strategies/{sid}/enable")

        resp = await auth_client.post(f"/api/v1/strategies/{sid}/pause")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_disable_strategy(self, auth_client):
        create = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        sid = create.json()["data"]["id"]
        await auth_client.post(f"/api/v1/strategies/{sid}/enable")

        resp = await auth_client.post(f"/api/v1/strategies/{sid}/disable")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_draft_strategy(self, auth_client):
        create = await auth_client.post("/api/v1/strategies", json=_valid_strategy_payload())
        sid = create.json()["data"]["id"]

        resp = await auth_client.delete(f"/api/v1/strategies/{sid}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_get_indicator_catalog(self, auth_client):
        resp = await auth_client.get("/api/v1/strategies/indicators")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "key" in data[0]

    @pytest.mark.asyncio
    async def test_create_invalid_strategy(self, auth_client):
        resp = await auth_client.post("/api/v1/strategies", json={
            "name": "",
            "market": "invalid",
        })
        assert resp.status_code in (400, 422)
