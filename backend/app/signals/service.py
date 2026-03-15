"""Signal service — creation, validation, dedup, lifecycle, and analytics."""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.signals.config import SignalConfig
from app.signals.dedup import SignalDeduplicator
from app.signals.errors import SignalNotFoundError, SignalTransitionError
from app.signals.models import Signal
from app.signals.repository import SignalRepository

logger = logging.getLogger(__name__)

_VALID_SIDES = {"buy", "sell"}
_VALID_SIGNAL_TYPES = {"entry", "exit", "scale_in", "scale_out"}
_VALID_SOURCES = {"strategy", "manual", "safety", "system"}
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"risk_approved", "risk_rejected", "risk_modified", "expired", "canceled"},
    "risk_approved": {"order_filled", "order_rejected"},
    "risk_modified": {"order_filled", "order_rejected"},
}


class SignalService:
    """Signal creation, validation, deduplication, lifecycle, and analytics.

    This is the inter-module interface. Other modules call:
    - create_signal() — strategy runner, manual close, safety monitor, system
    - get_pending_signals() — risk engine
    - update_signal_status() — risk engine (after evaluation)
    """

    def __init__(self, config: SignalConfig, deduplicator: SignalDeduplicator):
        self._config = config
        self._dedup = deduplicator
        self._repo = SignalRepository()

    async def create_signal(
        self, db: AsyncSession, signal_data: dict
    ) -> Signal | None:
        """Create a signal with validation and deduplication.

        This method never raises exceptions. Validation and dedup failures
        are logged but don't propagate — the caller (strategy runner) should
        not be disrupted by signal-layer issues.
        """
        try:
            errors = await self._validate_signal(db, signal_data)
            if errors:
                logger.warning(
                    "Signal validation failed for %s %s: %s",
                    signal_data.get("side"), signal_data.get("symbol"), errors,
                )
                return None

            strategy_id = signal_data["strategy_id"]
            symbol = signal_data["symbol"]
            side = signal_data["side"]
            signal_type = signal_data["signal_type"]
            source = signal_data["source"]
            timeframe = signal_data["timeframe"]
            ts = signal_data["ts"]

            is_dup, existing_id = await self._dedup.is_duplicate(
                db, strategy_id, symbol, side, signal_type, source, timeframe, ts
            )
            if is_dup:
                # Emit audit event for deduplication
                try:
                    from app.observability.startup import get_event_emitter
                    emitter = get_event_emitter()
                    if emitter:
                        await emitter.emit(
                            event_type="signal.deduplicated",
                            category="signals",
                            severity="debug",
                            source_module="signals",
                            summary=f"📊 Signal deduplicated: {side} {symbol}",
                            entity_type="signal",
                            entity_id=existing_id,
                            strategy_id=strategy_id,
                            symbol=symbol,
                            details={
                                "side": side,
                                "signal_type": signal_type,
                                "source": source,
                                "existing_signal_id": str(existing_id) if existing_id else None,
                            },
                        )
                except Exception:
                    pass  # Event emission never disrupts trading pipeline
                return None

            expiry_seconds = self._config.get_expiry_duration(timeframe)
            expires_at = ts + timedelta(seconds=expiry_seconds)

            confidence = signal_data.get("confidence")
            if confidence is not None:
                confidence = Decimal(str(confidence))

            signal = Signal(
                strategy_id=strategy_id,
                strategy_version=signal_data["strategy_version"],
                symbol=symbol,
                market=signal_data.get("market", "equities"),
                timeframe=timeframe,
                side=side,
                signal_type=signal_type,
                source=source,
                confidence=confidence,
                status="pending",
                payload_json=signal_data.get("payload_json"),
                position_id=signal_data.get("position_id"),
                exit_reason=signal_data.get("exit_reason"),
                ts=ts,
                expires_at=expires_at,
            )

            signal = await self._repo.create(db, signal)
            logger.info(
                "Signal created: %s %s %s (strategy=%s, type=%s, source=%s, id=%s)",
                side.upper(), symbol, signal_type, strategy_id,
                signal_type, source, signal.id,
            )

            # Emit audit event
            try:
                from app.observability.startup import get_event_emitter
                emitter = get_event_emitter()
                if emitter:
                    await emitter.emit(
                        event_type="signal.created",
                        category="signals",
                        severity="info",
                        source_module="signals",
                        summary=f"📊 {side.upper()} {symbol} signal ({signal_type}, {source})",
                        entity_type="signal",
                        entity_id=signal.id,
                        strategy_id=strategy_id,
                        symbol=symbol,
                        details={
                            "signal_type": signal_type,
                            "source": source,
                            "side": side,
                            "timeframe": timeframe,
                        },
                    )
            except Exception:
                pass  # Event emission is non-critical

            return signal
        except Exception as e:
            logger.error("Signal creation error: %s", e)
            return None

    async def _validate_signal(
        self, db: AsyncSession, signal_data: dict
    ) -> list[str]:
        """Validate a signal before creation. Returns list of errors."""
        errors: list[str] = []

        strategy_id = signal_data.get("strategy_id")
        if not strategy_id:
            errors.append("strategy_id is required")
        else:
            from app.strategies.repository import StrategyRepository
            strategy = await StrategyRepository().get_by_id(db, strategy_id)
            if not strategy:
                errors.append(f"Strategy {strategy_id} not found")

        symbol = signal_data.get("symbol")
        if not symbol:
            errors.append("symbol is required")
        else:
            from app.market_data.service import MarketDataService
            on_watchlist = await MarketDataService().is_symbol_on_watchlist(db, symbol)
            if not on_watchlist:
                # Log but don't block — watchlist may not be populated yet
                logger.debug("Symbol %s not on watchlist", symbol)

        side = signal_data.get("side")
        if side not in _VALID_SIDES:
            errors.append(f"side must be one of: {', '.join(sorted(_VALID_SIDES))}")

        signal_type = signal_data.get("signal_type")
        if signal_type not in _VALID_SIGNAL_TYPES:
            errors.append(
                f"signal_type must be one of: {', '.join(sorted(_VALID_SIGNAL_TYPES))}"
            )

        source = signal_data.get("source")
        if source not in _VALID_SOURCES:
            errors.append(f"source must be one of: {', '.join(sorted(_VALID_SOURCES))}")

        ts = signal_data.get("ts")
        if ts is None:
            errors.append("ts is required")
        else:
            now = datetime.now(timezone.utc)
            if ts > now + timedelta(seconds=5):
                errors.append("ts cannot be in the future")
            if ts < now - timedelta(minutes=5):
                errors.append("ts is too old (more than 5 minutes in the past)")

        if not signal_data.get("strategy_version"):
            errors.append("strategy_version is required")
        if not signal_data.get("timeframe"):
            errors.append("timeframe is required")

        # TODO (TASK-013): Logical checks for position existence
        # - Entry signal: no existing open position for strategy+symbol
        # - Exit signal: position_id references a real position
        # - Scale_in: position exists and not at max size
        # - Scale_out: position exists with quantity to reduce

        return errors

    async def get_signal(
        self, db: AsyncSession, signal_id: UUID, user_id: UUID
    ) -> Signal:
        """Get signal by ID. Verify ownership through strategy's user_id."""
        signal = await self._repo.get_by_id(db, signal_id)
        if not signal:
            raise SignalNotFoundError(str(signal_id))
        await self._verify_ownership(db, signal.strategy_id, user_id)
        return signal

    async def list_signals(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        status: str | None = None,
        signal_type: str | None = None,
        source: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Signal], int]:
        """List signals with filters, enforcing user ownership."""
        user_strategy_ids = await self._get_user_strategy_ids(db, user_id)
        if not user_strategy_ids:
            return [], 0

        if strategy_id and strategy_id not in user_strategy_ids:
            return [], 0

        # If no specific strategy, we need to filter by all user's strategies
        # For now, if strategy_id is provided use it, otherwise get all
        if not strategy_id:
            # Get all signals for user's strategies
            all_signals = []
            total = 0
            for sid in user_strategy_ids:
                sigs, cnt = await self._repo.get_filtered(
                    db, strategy_id=sid, symbol=symbol, status=status,
                    signal_type=signal_type, source=source,
                    date_start=date_start, date_end=date_end,
                    page=page, page_size=page_size,
                )
                all_signals.extend(sigs)
                total += cnt
            # Re-sort and paginate
            all_signals.sort(key=lambda s: s.created_at, reverse=True)
            return all_signals[:page_size], total

        return await self._repo.get_filtered(
            db, strategy_id=strategy_id, symbol=symbol, status=status,
            signal_type=signal_type, source=source,
            date_start=date_start, date_end=date_end,
            page=page, page_size=page_size,
        )

    async def get_recent(
        self, db: AsyncSession, user_id: UUID, limit: int = 20
    ) -> list[Signal]:
        """Get recent signals across all of user's strategies."""
        user_strategy_ids = await self._get_user_strategy_ids(db, user_id)
        if not user_strategy_ids:
            return []

        from sqlalchemy import select
        result = await db.execute(
            select(Signal)
            .where(Signal.strategy_id.in_(user_strategy_ids))
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cancel_signal(
        self, db: AsyncSession, signal_id: UUID, user_id: UUID
    ) -> Signal:
        """Cancel a pending signal. Only valid for status='pending'."""
        signal = await self.get_signal(db, signal_id, user_id)

        if signal.status != "pending":
            raise SignalTransitionError(
                message=f"Cannot cancel signal with status '{signal.status}'",
                details={"current_status": signal.status},
            )

        signal = await self._repo.update_status(db, signal_id, "canceled")
        logger.info("Signal %s canceled by user", signal_id)
        return signal

    async def get_pending_signals(self, db: AsyncSession) -> list[Signal]:
        """Get all pending signals for risk engine consumption.

        Returns signals ordered by created_at (oldest first — FIFO).
        """
        return await self._repo.get_pending(db)

    async def update_signal_status(
        self, db: AsyncSession, signal_id: UUID, new_status: str
    ) -> Signal:
        """Update signal status (called by risk engine).

        Validates transition: pending → risk_approved/risk_rejected/risk_modified/expired/canceled
        """
        signal = await self._repo.get_by_id(db, signal_id)
        if not signal:
            raise SignalNotFoundError(str(signal_id))

        allowed = _VALID_TRANSITIONS.get(signal.status, set())
        if new_status not in allowed:
            raise SignalTransitionError(
                message=f"Cannot transition from '{signal.status}' to '{new_status}'",
                details={
                    "current_status": signal.status,
                    "requested_status": new_status,
                    "allowed": sorted(allowed) if allowed else [],
                },
            )

        old_status = signal.status
        signal = await self._repo.update_status(db, signal_id, new_status)
        logger.info("Signal %s status changed to %s", signal_id, new_status)

        # Emit audit event
        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                severity = "warning" if new_status in ("risk_rejected", "expired") else "info"
                emoji = {"risk_approved": "✅", "risk_rejected": "❌", "risk_modified": "⚙️",
                         "expired": "⏰", "canceled": "🚫"}.get(new_status, "📊")
                await emitter.emit(
                    event_type="signal.status_changed",
                    category="signals",
                    severity=severity,
                    source_module="signals",
                    summary=f"{emoji} Signal {signal.symbol} {old_status} → {new_status}",
                    entity_type="signal",
                    entity_id=signal_id,
                    strategy_id=signal.strategy_id,
                    symbol=signal.symbol,
                    details={"old_status": old_status, "new_status": new_status},
                )
        except Exception:
            pass

        return signal

    async def cancel_strategy_signals(
        self, db: AsyncSession, strategy_id: UUID
    ) -> int:
        """Cancel all pending signals for a strategy.

        Called when a strategy is paused or disabled.
        """
        count = await self._repo.cancel_by_strategy(db, strategy_id)
        if count > 0:
            logger.info(
                "Canceled %d pending signals for strategy %s", count, strategy_id
            )
        return count

    async def get_stats(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
    ) -> dict:
        """Get signal analytics summary."""
        if strategy_id:
            await self._verify_ownership(db, strategy_id, user_id)

        return await self._repo.get_stats(
            db, strategy_id=strategy_id,
            date_start=date_start, date_end=date_end,
        )

    async def _verify_ownership(
        self, db: AsyncSession, strategy_id: UUID, user_id: UUID
    ) -> None:
        """Verify that a strategy belongs to the user."""
        from app.strategies.repository import StrategyRepository
        strategy = await StrategyRepository().get_by_id(db, strategy_id)
        if not strategy or strategy.user_id != user_id:
            raise SignalNotFoundError()

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
