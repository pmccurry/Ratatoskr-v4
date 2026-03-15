"""Alpaca paper trading executor — submits orders to Alpaca paper API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx

from app.paper_trading.executors.base import Executor, FillResult, OrderResult

if TYPE_CHECKING:
    from app.paper_trading.config import PaperTradingConfig
    from app.paper_trading.executors.simulated import SimulatedExecutor
    from app.paper_trading.models import PaperOrder

logger = logging.getLogger(__name__)


class AlpacaPaperExecutor(Executor):
    """Executor that submits orders to the Alpaca paper trading API.

    Used for equities and options when execution_mode_equities = "paper".
    Falls back to SimulatedExecutor if the API is unavailable.
    """

    @property
    def execution_mode(self) -> str:
        return "paper"

    def __init__(
        self,
        config: PaperTradingConfig,
        simulated_executor: SimulatedExecutor,
    ):
        self._config = config
        self._simulated = simulated_executor
        self._client: httpx.AsyncClient | None = None
        self._base_url: str = ""
        self._api_key: str = ""
        self._api_secret: str = ""
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load Alpaca API credentials from settings."""
        from app.common.config import get_settings
        settings = get_settings()
        self._base_url = settings.alpaca_base_url
        self._api_key = settings.alpaca_api_key
        self._api_secret = settings.alpaca_api_secret

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "APCA-API-KEY-ID": self._api_key,
                    "APCA-API-SECRET-KEY": self._api_secret,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def submit_order(
        self, order: PaperOrder, reference_price: Decimal
    ) -> OrderResult:
        """Submit order to Alpaca paper API."""
        if not self._api_key or not self._api_secret:
            return await self._fallback_submit(
                order, reference_price, "No Alpaca API credentials configured"
            )

        try:
            client = self._get_client()
            payload = {
                "symbol": order.symbol,
                "qty": str(order.requested_qty),
                "side": order.side,
                "type": order.order_type,
                "time_in_force": "day",
            }

            response = await client.post("/v2/orders", json=payload)

            if response.status_code in (200, 201):
                data = response.json()
                broker_order_id = data.get("id", "")
                return OrderResult(
                    success=True,
                    broker_order_id=broker_order_id,
                    status="accepted",
                )
            else:
                reason = f"Alpaca API error: {response.status_code} {response.text[:200]}"
                logger.warning("Alpaca order submission failed: %s", reason)
                return await self._fallback_submit(order, reference_price, reason)

        except httpx.HTTPError as e:
            reason = f"Alpaca connection error: {e}"
            logger.warning("Alpaca order submission failed: %s", reason)
            return await self._fallback_submit(order, reference_price, reason)

    async def simulate_fill(
        self, order: PaperOrder, reference_price: Decimal
    ) -> FillResult:
        """Get fill from Alpaca or simulate."""
        if not order.broker_order_id:
            # No broker order — use simulation
            return await self._simulated.simulate_fill(order, reference_price)

        try:
            fill = await self._poll_alpaca_fill(order)
            if fill:
                return fill
        except Exception as e:
            logger.warning("Alpaca fill poll failed, falling back: %s", e)

        # Fallback to simulation
        return await self._fallback_fill(order, reference_price, "Alpaca fill poll failed")

    async def cancel_order(self, order: PaperOrder) -> bool:
        """Cancel via Alpaca API."""
        if not order.broker_order_id:
            return True

        try:
            client = self._get_client()
            response = await client.delete(f"/v2/orders/{order.broker_order_id}")
            return response.status_code in (200, 204)
        except Exception as e:
            logger.warning("Alpaca cancel failed: %s", e)
            return False

    async def _poll_alpaca_fill(self, order: PaperOrder) -> FillResult | None:
        """Poll Alpaca for fill data (up to 3 attempts)."""
        client = self._get_client()

        for attempt in range(3):
            if attempt > 0:
                await asyncio.sleep(1)

            response = await client.get(f"/v2/orders/{order.broker_order_id}")
            if response.status_code != 200:
                continue

            data = response.json()
            status = data.get("status", "")

            if status == "filled":
                filled_qty = Decimal(str(data.get("filled_qty", "0")))
                filled_avg_price = Decimal(str(data.get("filled_avg_price", "0")))
                filled_at_str = data.get("filled_at", "")

                try:
                    filled_at = datetime.fromisoformat(filled_at_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    filled_at = datetime.now(timezone.utc)

                # Calculate values
                gross_value = filled_qty * filled_avg_price
                # Alpaca paper trading has no commission
                fee = Decimal("0")
                net_value = gross_value

                return FillResult(
                    order_id=order.id,
                    qty=filled_qty,
                    reference_price=filled_avg_price,
                    price=filled_avg_price,
                    fee=fee,
                    slippage_bps=Decimal("0"),
                    slippage_amount=Decimal("0"),
                    gross_value=gross_value,
                    net_value=net_value,
                    filled_at=filled_at,
                    broker_fill_id=data.get("id"),
                )

            if status in ("canceled", "expired", "rejected"):
                return None

        return None

    async def _fallback_submit(
        self, order: PaperOrder, reference_price: Decimal, reason: str
    ) -> OrderResult:
        """Fall back to simulation for order submission."""
        from app.common.config import get_settings
        settings = get_settings()

        if settings.paper_trading_broker_fallback in ("", "false", "disabled", "none"):
            return OrderResult(
                success=False,
                rejection_reason=f"Alpaca unavailable and fallback disabled: {reason}",
            )

        logger.warning("Falling back to simulation: %s", reason)
        return await self._simulated.submit_order(order, reference_price)

    async def _fallback_fill(
        self, order: PaperOrder, reference_price: Decimal, reason: str
    ) -> FillResult:
        """Fall back to simulation for fill."""
        logger.warning("Falling back to simulated fill: %s", reason)
        return await self._simulated.simulate_fill(order, reference_price)
