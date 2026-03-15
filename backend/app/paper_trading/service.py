"""Paper trading service — consumes risk-approved signals, produces orders and fills."""

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from math import floor
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.paper_trading.cash_manager import CashManager
from app.paper_trading.config import PaperTradingConfig
from app.paper_trading.errors import (
    FillNotFoundError,
    OrderNotFoundError,
)
from app.paper_trading.executors.base import Executor
from app.paper_trading.executors.simulated import SimulatedExecutor
from app.paper_trading.models import PaperFill, PaperOrder
from app.paper_trading.repository import PaperFillRepository, PaperOrderRepository

logger = logging.getLogger(__name__)


class PaperTradingService:
    """Consumes risk-approved signals and produces orders and fills."""

    def __init__(
        self,
        config: PaperTradingConfig,
        simulated_executor: SimulatedExecutor,
        cash_manager: CashManager,
        forex_pool_executor: object | None = None,
        alpaca_executor: object | None = None,
        shadow_tracker: object | None = None,
        forex_pool_manager: object | None = None,
    ):
        self._config = config
        self._simulated_executor = simulated_executor
        self._cash_manager = cash_manager
        self._forex_pool_executor = forex_pool_executor
        self._alpaca_executor = alpaca_executor
        self._shadow_tracker = shadow_tracker
        self._forex_pool_manager = forex_pool_manager
        self._order_repo = PaperOrderRepository()
        self._fill_repo = PaperFillRepository()

    async def process_approved_signals(self, db: AsyncSession) -> dict:
        """Process all risk-approved/modified signals.

        Called periodically by the background order consumer.
        """
        from app.signals.models import Signal
        from sqlalchemy import select

        result = await db.execute(
            select(Signal)
            .where(Signal.status.in_(["risk_approved", "risk_modified"]))
            .order_by(Signal.created_at.asc())
        )
        signals = list(result.scalars().all())

        processed = 0
        filled = 0
        rejected = 0

        for signal in signals:
            try:
                order = await self.process_signal(db, signal)
                processed += 1
                if order.status == "filled":
                    filled += 1
                elif order.status == "rejected":
                    rejected += 1
            except Exception as e:
                logger.error("Error processing signal %s: %s", signal.id, e)

        return {"processed": processed, "filled": filled, "rejected": rejected}

    async def process_signal(
        self, db: AsyncSession, signal: object
    ) -> PaperOrder:
        """Process a single approved signal into an order and fill."""
        now = datetime.now(timezone.utc)

        # Get risk decision for this signal
        from app.risk.repository import RiskDecisionRepository

        decision_repo = RiskDecisionRepository()
        risk_decision = await decision_repo.get_by_signal_id(db, signal.id)

        if not risk_decision:
            logger.error("No risk decision found for signal %s", signal.id)
            order = await self._create_rejected_order(
                db, signal, None, now, "no_risk_decision",
            )
            await self._update_signal_status(db, signal.id, "order_rejected")
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="paper_trading.order.rejected",
                        category="trading",
                        severity="warning",
                        source_module="paper_trading",
                        summary=f"❌ Order rejected: {signal.symbol} (no_risk_decision)",
                        entity_type="signal",
                        entity_id=signal.id,
                        strategy_id=signal.strategy_id,
                        symbol=signal.symbol,
                        details={"reason": "no_risk_decision", "signal_id": str(signal.id)},
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline
            return order

        # Determine order parameters (check for modifications)
        modifications = risk_decision.modifications_json or {}

        # Get reference price
        reference_price = await self._get_reference_price(db, signal.symbol)
        if reference_price is None:
            order = await self._create_rejected_order(
                db, signal, risk_decision.id, now, "no_reference_price",
            )
            await self._update_signal_status(db, signal.id, "order_rejected")
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="paper_trading.order.rejected",
                        category="trading",
                        severity="warning",
                        source_module="paper_trading",
                        summary=f"❌ Order rejected: {signal.symbol} (no_reference_price)",
                        entity_type="paper_order",
                        entity_id=order.id,
                        strategy_id=signal.strategy_id,
                        symbol=signal.symbol,
                        details={"reason": "no_reference_price", "signal_id": str(signal.id)},
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline
            return order

        # Determine quantity
        qty = await self._determine_qty(
            db, signal, risk_decision, reference_price
        )
        if qty <= 0:
            order = await self._create_rejected_order(
                db, signal, risk_decision.id, now, "invalid_quantity",
            )
            await self._update_signal_status(db, signal.id, "order_rejected")
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="paper_trading.order.rejected",
                        category="trading",
                        severity="warning",
                        source_module="paper_trading",
                        summary=f"❌ Order rejected: {signal.symbol} (invalid_quantity)",
                        entity_type="paper_order",
                        entity_id=order.id,
                        strategy_id=signal.strategy_id,
                        symbol=signal.symbol,
                        details={"reason": "invalid_quantity", "signal_id": str(signal.id)},
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline
            return order

        # Determine contract multiplier
        contract_multiplier = 1
        if signal.market == "options" or getattr(signal, "underlying_symbol", None):
            contract_multiplier = self._config.default_contract_multiplier

        # Create order
        order = PaperOrder(
            signal_id=signal.id,
            risk_decision_id=risk_decision.id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            market=getattr(signal, "market", "equities"),
            side=signal.side,
            order_type="market",
            signal_type=signal.signal_type,
            requested_qty=qty,
            requested_price=None,
            status="pending",
            execution_mode="simulation",
            underlying_symbol=getattr(signal, "underlying_symbol", None),
            contract_type=getattr(signal, "contract_type", None),
            strike_price=getattr(signal, "strike_price", None),
            expiration_date=getattr(signal, "expiration_date", None),
            contract_multiplier=contract_multiplier,
            submitted_at=now,
        )

        # Check cash availability
        required_cash = self._cash_manager.calculate_required_cash(
            order, reference_price
        )
        is_available, available_cash = await self._cash_manager.check_availability(
            db, required_cash, order.market
        )
        if not is_available:
            order.status = "rejected"
            order.rejection_reason = (
                f"Insufficient cash: required={required_cash}, available={available_cash}"
            )
            order = await self._order_repo.create(db, order)
            await self._update_signal_status(db, signal.id, "order_rejected")
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="paper_trading.order.rejected",
                        category="trading",
                        severity="warning",
                        source_module="paper_trading",
                        summary=f"❌ Order rejected: {signal.symbol} (insufficient_cash)",
                        entity_type="paper_order",
                        entity_id=order.id,
                        strategy_id=signal.strategy_id,
                        symbol=signal.symbol,
                        details={
                            "reason": "insufficient_cash",
                            "signal_id": str(signal.id),
                            "required": str(required_cash),
                            "available": str(available_cash),
                        },
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline
            return order

        order = await self._order_repo.create(db, order)

        # Emit order created event
        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="paper_trading.order.created",
                    category="trading",
                    severity="info",
                    source_module="paper_trading",
                    summary=f"📝 Order: {order.side} {order.requested_qty} {order.symbol} @ {order.order_type}",
                    entity_type="paper_order",
                    entity_id=order.id,
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    details={
                        "signal_id": str(signal.id),
                        "order_id": str(order.id),
                        "side": order.side,
                        "qty": str(order.requested_qty),
                        "order_type": order.order_type,
                        "signal_type": order.signal_type,
                        "market": order.market,
                    },
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        # Get executor and submit
        executor = await self._get_executor(order.market)

        # Forex pool executor needs db for allocation queries
        from app.paper_trading.executors.forex_pool import ForexPoolExecutor
        if isinstance(executor, ForexPoolExecutor):
            submit_result = await executor.submit_order(order, reference_price, db=db)
        else:
            submit_result = await executor.submit_order(order, reference_price)

        if not submit_result.success:
            order.status = "rejected"
            order.rejection_reason = submit_result.rejection_reason
            await self._order_repo.update(db, order)
            await self._update_signal_status(db, signal.id, "order_rejected")
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="paper_trading.order.rejected",
                        category="trading",
                        severity="warning",
                        source_module="paper_trading",
                        summary=f"❌ Order rejected: {order.symbol} ({submit_result.rejection_reason})",
                        entity_type="paper_order",
                        entity_id=order.id,
                        strategy_id=order.strategy_id,
                        symbol=order.symbol,
                        details={
                            "reason": submit_result.rejection_reason,
                            "signal_id": str(signal.id),
                            "order_id": str(order.id),
                        },
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline

            # Shadow tracking for contention-blocked forex signals
            if (
                submit_result.rejection_reason == "no_available_account"
                and self._shadow_tracker
                and self._shadow_tracker.should_track(signal, submit_result.rejection_reason)
            ):
                try:
                    await self._shadow_tracker.create_shadow_entry(
                        db, signal, order, reference_price
                    )
                except Exception as e:
                    logger.error("Shadow entry creation failed: %s", e)

            return order

        # Order accepted
        order.status = "accepted"
        order.accepted_at = datetime.now(timezone.utc)
        if submit_result.broker_order_id:
            order.broker_order_id = submit_result.broker_order_id
        await self._order_repo.update(db, order)

        # Simulate fill
        try:
            fill_result = await executor.simulate_fill(order, reference_price)
        except Exception as e:
            order.status = "rejected"
            order.rejection_reason = f"Fill simulation failed: {e}"
            await self._order_repo.update(db, order)
            await self._update_signal_status(db, signal.id, "order_rejected")
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="paper_trading.order.rejected",
                        category="trading",
                        severity="warning",
                        source_module="paper_trading",
                        summary=f"❌ Order rejected: {order.symbol} (fill_simulation_failed)",
                        entity_type="paper_order",
                        entity_id=order.id,
                        strategy_id=order.strategy_id,
                        symbol=order.symbol,
                        details={
                            "reason": "fill_simulation_failed",
                            "signal_id": str(signal.id),
                            "order_id": str(order.id),
                            "error": str(e),
                        },
                    )
            except Exception:
                pass  # Event emission never disrupts trading pipeline
            return order

        # Create fill record
        fill = PaperFill(
            order_id=order.id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side=order.side,
            qty=fill_result.qty,
            reference_price=fill_result.reference_price,
            price=fill_result.price,
            gross_value=fill_result.gross_value,
            fee=fill_result.fee,
            slippage_bps=fill_result.slippage_bps,
            slippage_amount=fill_result.slippage_amount,
            net_value=fill_result.net_value,
            broker_fill_id=fill_result.broker_fill_id,
            filled_at=fill_result.filled_at,
        )
        fill = await self._fill_repo.create(db, fill)

        # Update order as filled
        order.status = "filled"
        order.filled_qty = fill_result.qty
        order.filled_avg_price = fill_result.price
        order.filled_at = fill_result.filled_at
        await self._order_repo.update(db, order)

        # Emit fill event
        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="paper_trading.order.filled",
                    category="trading",
                    severity="info",
                    source_module="paper_trading",
                    summary=f"💰 {order.side.upper()} {order.symbol} filled: {fill_result.qty}@{fill_result.price}",
                    entity_type="fill",
                    entity_id=fill.id,
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    details={
                        "signal_id": str(signal.id),
                        "order_id": str(order.id),
                        "qty": str(fill_result.qty),
                        "price": str(fill_result.price),
                        "fee": str(fill_result.fee),
                        "net_value": str(fill_result.net_value),
                    },
                )
        except Exception:
            pass

        # Update signal status
        await self._update_signal_status(db, signal.id, "order_filled")

        # Notify portfolio module
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                # Get user_id from strategy
                from app.strategies.repository import StrategyRepository
                strategy = await StrategyRepository().get_by_id(db, order.strategy_id)
                if strategy:
                    await portfolio_service.process_fill(db, fill, order, strategy.user_id)
        except Exception as e:
            logger.error("Portfolio fill processing failed (non-fatal): %s", e)

        # Release forex account allocation on exit fills
        if (
            order.market == "forex"
            and order.signal_type in ("exit", "scale_out")
            and self._forex_pool_manager
        ):
            try:
                await self._forex_pool_manager.release(
                    db, order.strategy_id, order.symbol
                )
            except Exception as e:
                logger.error("Forex pool release failed (non-fatal): %s", e)

        logger.info(
            "Order filled: %s %s %s qty=%s price=%s (order=%s)",
            order.side.upper(),
            order.symbol,
            order.signal_type,
            fill_result.qty,
            fill_result.price,
            order.id,
        )

        return order

    async def _create_rejected_order(
        self,
        db: AsyncSession,
        signal: object,
        risk_decision_id: UUID | None,
        now: datetime,
        reason: str,
    ) -> PaperOrder:
        """Create a rejected order record."""
        from uuid import uuid4

        order = PaperOrder(
            signal_id=signal.id,
            risk_decision_id=risk_decision_id or uuid4(),
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            market=getattr(signal, "market", "equities"),
            side=signal.side,
            order_type="market",
            signal_type=signal.signal_type,
            requested_qty=Decimal("0"),
            status="rejected",
            rejection_reason=reason,
            execution_mode="simulation",
            contract_multiplier=1,
            submitted_at=now,
        )
        return await self._order_repo.create(db, order)

    async def _determine_qty(
        self,
        db: AsyncSession,
        signal: object,
        risk_decision: object,
        reference_price: Decimal,
    ) -> Decimal:
        """Calculate order quantity from strategy config."""
        # Check if risk modified the quantity
        modifications = getattr(risk_decision, "modifications_json", None) or {}
        if "qty" in modifications:
            return Decimal(str(modifications["qty"]))

        # Get strategy config for position sizing
        from app.strategies.repository import StrategyConfigRepository

        config_repo = StrategyConfigRepository()
        active_config = await config_repo.get_active(db, signal.strategy_id)
        strategy_config = active_config.config_json if active_config else {}

        sizing = strategy_config.get("position_sizing", {})
        method = sizing.get("method", "fixed_qty")
        value = Decimal(str(sizing.get("value", "100")))

        # Equity stubbed to initial_cash until TASK-013
        equity = self._config.initial_cash

        if method == "fixed_qty":
            qty = value
        elif method == "fixed_dollar":
            if reference_price > 0:
                qty = value / reference_price
            else:
                return Decimal("0")
        elif method == "percent_equity":
            dollar_value = equity * value / Decimal("100")
            if reference_price > 0:
                qty = dollar_value / reference_price
            else:
                return Decimal("0")
        elif method == "risk_based":
            risk_percent = Decimal(str(sizing.get("risk_percent", "1")))
            stop_price = Decimal(str(sizing.get("stop_price", "0")))
            risk_per_share = abs(reference_price - stop_price)
            if risk_per_share > 0:
                risk_amount = equity * risk_percent / Decimal("100")
                qty = risk_amount / risk_per_share
            else:
                return Decimal("0")
        else:
            qty = value

        # Round based on market
        market = getattr(signal, "market", "equities")
        if market == "equities":
            qty = Decimal(str(int(qty)))  # whole shares
        elif market == "options":
            qty = Decimal(str(int(qty)))  # whole contracts

        return max(qty, Decimal("0"))

    async def _get_executor(self, market: str) -> Executor:
        """Get the appropriate executor for a market.

        Equities: AlpacaPaperExecutor if mode=paper and available, else Simulated.
        Forex: ForexPoolExecutor if available, else Simulated.
        """
        if market == "forex" and self._forex_pool_executor:
            return self._forex_pool_executor
        if market in ("equities", "options") and self._alpaca_executor:
            if self._config.execution_mode_equities == "paper":
                return self._alpaca_executor
        return self._simulated_executor

    async def _get_reference_price(
        self, db: AsyncSession, symbol: str
    ) -> Decimal | None:
        """Get the reference price for fill simulation."""
        try:
            from app.market_data.service import MarketDataService

            price = await MarketDataService().get_latest_close(db, symbol, "1m")
            if price is not None:
                return price
            # Fall back to other timeframes
            for tf in ("5m", "15m", "1h", "1d"):
                price = await MarketDataService().get_latest_close(db, symbol, tf)
                if price is not None:
                    return price
        except Exception as e:
            logger.warning("Failed to get reference price for %s: %s", symbol, e)
        return None

    async def _update_signal_status(
        self, db: AsyncSession, signal_id: UUID, new_status: str
    ) -> None:
        """Update signal status through SignalService for transition validation."""
        try:
            from app.signals.startup import get_signal_service

            signal_service = get_signal_service()
            if signal_service:
                await signal_service.update_signal_status(db, signal_id, new_status)
            else:
                logger.warning(
                    "SignalService not available, cannot update signal %s to %s",
                    signal_id, new_status,
                )
        except Exception as e:
            logger.error("Failed to update signal %s status: %s", signal_id, e)

    # --- Read Operations ---

    async def get_order(
        self, db: AsyncSession, order_id: UUID, user_id: UUID
    ) -> PaperOrder:
        """Get order by ID. Verify ownership through strategy."""
        order = await self._order_repo.get_by_id(db, order_id)
        if not order:
            raise OrderNotFoundError(str(order_id))
        await self._verify_ownership(db, order.strategy_id, user_id)
        return order

    async def list_orders(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        status: str | None = None,
        signal_type: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PaperOrder], int]:
        """List orders with filters. Enforce ownership."""
        user_strategy_ids = await self._get_user_strategy_ids(db, user_id)
        if not user_strategy_ids:
            return [], 0

        if strategy_id and strategy_id not in user_strategy_ids:
            return [], 0

        if strategy_id:
            return await self._order_repo.get_filtered(
                db,
                strategy_id=strategy_id,
                symbol=symbol,
                status=status,
                signal_type=signal_type,
                date_start=date_start,
                date_end=date_end,
                page=page,
                page_size=page_size,
            )

        # All user strategies
        all_orders = []
        total = 0
        for sid in user_strategy_ids:
            orders, cnt = await self._order_repo.get_filtered(
                db,
                strategy_id=sid,
                symbol=symbol,
                status=status,
                signal_type=signal_type,
                date_start=date_start,
                date_end=date_end,
                page=page,
                page_size=page_size,
            )
            all_orders.extend(orders)
            total += cnt

        all_orders.sort(key=lambda o: o.created_at, reverse=True)
        return all_orders[:page_size], total

    async def get_fill(
        self, db: AsyncSession, fill_id: UUID, user_id: UUID
    ) -> PaperFill:
        """Get fill by ID. Verify ownership."""
        fill = await self._fill_repo.get_by_id(db, fill_id)
        if not fill:
            raise FillNotFoundError(str(fill_id))
        await self._verify_ownership(db, fill.strategy_id, user_id)
        return fill

    async def list_fills(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        side: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PaperFill], int]:
        """List fills with filters. Enforce ownership."""
        user_strategy_ids = await self._get_user_strategy_ids(db, user_id)
        if not user_strategy_ids:
            return [], 0

        if strategy_id and strategy_id not in user_strategy_ids:
            return [], 0

        if strategy_id:
            return await self._fill_repo.get_filtered(
                db,
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                date_start=date_start,
                date_end=date_end,
                page=page,
                page_size=page_size,
            )

        all_fills = []
        total = 0
        for sid in user_strategy_ids:
            fills, cnt = await self._fill_repo.get_filtered(
                db,
                strategy_id=sid,
                symbol=symbol,
                side=side,
                date_start=date_start,
                date_end=date_end,
                page=page,
                page_size=page_size,
            )
            all_fills.extend(fills)
            total += cnt

        all_fills.sort(key=lambda f: f.filled_at, reverse=True)
        return all_fills[:page_size], total

    async def get_order_fills(
        self, db: AsyncSession, order_id: UUID, user_id: UUID
    ) -> list[PaperFill]:
        """Get all fills for an order."""
        order = await self.get_order(db, order_id, user_id)
        return await self._fill_repo.get_by_order_id(db, order.id)

    async def get_recent_fills(
        self, db: AsyncSession, user_id: UUID, limit: int = 20
    ) -> list[PaperFill]:
        """Get recent fills across all strategies."""
        user_strategy_ids = await self._get_user_strategy_ids(db, user_id)
        if not user_strategy_ids:
            return []

        from sqlalchemy import select

        result = await db.execute(
            select(PaperFill)
            .where(PaperFill.strategy_id.in_(user_strategy_ids))
            .order_by(PaperFill.filled_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _verify_ownership(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID
    ) -> None:
        """Verify that a strategy belongs to the user."""
        from app.strategies.repository import StrategyRepository

        strategy = await StrategyRepository().get_by_id(db, strategy_id)
        if not strategy or strategy.user_id != user_id:
            raise OrderNotFoundError()

    async def _get_user_strategy_ids(
        self, db: AsyncSession, user_id: UUID
    ) -> list[UUID]:
        """Get all strategy IDs belonging to a user."""
        from sqlalchemy import select
        from app.strategies.models import Strategy

        result = await db.execute(
            select(Strategy.id).where(Strategy.user_id == user_id)
        )
        return [row[0] for row in result.all()]
