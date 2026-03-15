"""E2E tests for signal, order, fill, and portfolio read endpoints."""

import pytest


class TestSignalEndpoints:
    @pytest.mark.asyncio
    async def test_list_signals_empty(self, auth_client):
        resp = await auth_client.get("/api/v1/signals")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_list_signals_with_filters(self, auth_client):
        resp = await auth_client.get("/api/v1/signals", params={
            "status": "pending",
            "symbol": "AAPL",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_signal_recent(self, auth_client):
        resp = await auth_client.get("/api/v1/signals/recent", params={"limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_signal_stats(self, auth_client):
        resp = await auth_client.get("/api/v1/signals/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body


class TestOrderAndFillEndpoints:
    @pytest.mark.asyncio
    async def test_list_orders(self, auth_client):
        resp = await auth_client.get("/api/v1/paper-trading/orders")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_list_fills(self, auth_client):
        resp = await auth_client.get("/api/v1/paper-trading/fills")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_fills_recent(self, auth_client):
        resp = await auth_client.get("/api/v1/paper-trading/fills/recent", params={"limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body


class TestPortfolioEndpoints:
    @pytest.mark.asyncio
    async def test_portfolio_summary(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_positions_open(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/positions/open")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_equity_curve(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/equity-curve")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_portfolio_metrics(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_pnl_summary(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/pnl/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_cash_balances(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/cash")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_dividends_summary(self, auth_client):
        resp = await auth_client.get("/api/v1/portfolio/dividends/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
