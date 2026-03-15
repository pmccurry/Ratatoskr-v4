"""Portfolio service — inter-module interface for positions, cash, equity."""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.config import PortfolioConfig
from app.portfolio.errors import PositionNotFoundError
from app.portfolio.fill_processor import FillProcessor
from app.portfolio.models import CashBalance, Position
from app.portfolio.repository import (
    CashBalanceRepository,
    PortfolioMetaRepository,
    PositionRepository,
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Portfolio management and inter-module interface."""

    def __init__(self, config: PortfolioConfig, fill_processor: FillProcessor):
        self._config = config
        self._fill_processor = fill_processor
        self._position_repo = PositionRepository()
        self._cash_repo = CashBalanceRepository()
        self._meta_repo = PortfolioMetaRepository()

    # --- Fill Processing (called by paper trading) ---

    async def process_fill(
        self, db: AsyncSession, fill: object, order: object, user_id: UUID
    ) -> Position:
        """Process a fill into a position update. Delegates to FillProcessor."""
        return await self._fill_processor.process_fill(db, fill, order, user_id)

    # --- Position Queries ---

    async def get_open_positions(
        self, db: AsyncSession, strategy_id: UUID
    ) -> list[Position]:
        """Get open positions for a strategy. Used by runner for exit evaluation."""
        return await self._position_repo.get_open_by_strategy(db, strategy_id)

    async def get_open_position_for_symbol(
        self, db: AsyncSession, strategy_id: UUID, symbol: str
    ) -> Position | None:
        """Get open position for a specific strategy+symbol."""
        return await self._position_repo.get_open_by_strategy_symbol(
            db, strategy_id, symbol
        )

    async def get_all_open_positions(
        self, db: AsyncSession, user_id: UUID
    ) -> list[Position]:
        """Get all open positions for a user."""
        return await self._position_repo.get_all_open(db, user_id)

    async def get_positions_count(
        self, db: AsyncSession, strategy_id: UUID
    ) -> int:
        """Count open positions for a strategy."""
        return await self._position_repo.get_open_positions_count(db, strategy_id)

    async def get_orphaned_positions(self, db: AsyncSession) -> list[tuple]:
        """Get positions whose strategy is paused/disabled."""
        from app.strategies.models import Strategy
        from sqlalchemy import or_

        result = await db.execute(
            select(Position, Strategy)
            .join(Strategy, Position.strategy_id == Strategy.id)
            .where(
                Position.status == "open",
                or_(
                    Strategy.status == "paused",
                    Strategy.status == "disabled",
                ),
            )
        )
        return [(row[0], row[1]) for row in result.all()]

    # --- Cash ---

    async def get_cash(
        self, db: AsyncSession, user_id: UUID,
        account_scope: str = "equities"
    ) -> Decimal:
        """Get cash balance for an account scope."""
        cash = await self._cash_repo.get_by_scope(db, account_scope, user_id)
        return cash.balance if cash else Decimal("0")

    async def get_total_cash(self, db: AsyncSession, user_id: UUID) -> Decimal:
        """Get total cash across all accounts."""
        return await self._cash_repo.get_total_cash(db, user_id)

    async def get_all_cash_balances(
        self, db: AsyncSession, user_id: UUID
    ) -> list[CashBalance]:
        """Get all cash balances."""
        return await self._cash_repo.get_all(db, user_id)

    # --- Equity and Exposure ---

    async def get_equity(self, db: AsyncSession, user_id: UUID) -> Decimal:
        """total_cash + sum(open position market_values)"""
        total_cash = await self.get_total_cash(db, user_id)
        positions = await self._position_repo.get_all_open(db, user_id)
        positions_value = sum(
            (p.market_value for p in positions), Decimal("0")
        )
        return total_cash + positions_value

    async def get_peak_equity(self, db: AsyncSession, user_id: UUID) -> Decimal:
        """Read from PortfolioMeta."""
        peak_str = await self._meta_repo.get(db, "peak_equity", user_id)
        if peak_str:
            return Decimal(peak_str)
        # If no peak recorded, use current equity
        return await self.get_equity(db, user_id)

    async def get_drawdown(self, db: AsyncSession, user_id: UUID) -> dict:
        """Calculate current drawdown."""
        current_equity = await self.get_equity(db, user_id)
        peak_equity = await self.get_peak_equity(db, user_id)

        if peak_equity > 0:
            drawdown_percent = (peak_equity - current_equity) / peak_equity * 100
        else:
            drawdown_percent = Decimal("0")

        return {
            "peak_equity": peak_equity,
            "current_equity": current_equity,
            "drawdown_percent": max(drawdown_percent, Decimal("0")),
        }

    async def get_symbol_exposure(
        self, db: AsyncSession, symbol: str
    ) -> Decimal:
        """Total market value of all open positions in a symbol."""
        positions = await self._position_repo.get_open_by_symbol(db, symbol)
        return sum((p.market_value for p in positions), Decimal("0"))

    async def get_strategy_exposure(
        self, db: AsyncSession, strategy_id: UUID
    ) -> Decimal:
        """Total market value of all open positions for a strategy."""
        positions = await self._position_repo.get_open_by_strategy(db, strategy_id)
        return sum((p.market_value for p in positions), Decimal("0"))

    async def get_total_exposure(
        self, db: AsyncSession, user_id: UUID
    ) -> Decimal:
        """Total market value of all open positions."""
        positions = await self._position_repo.get_all_open(db, user_id)
        return sum((p.market_value for p in positions), Decimal("0"))

    async def get_daily_realized_loss(
        self, db: AsyncSession, user_id: UUID
    ) -> Decimal:
        """Sum of realized losses today."""
        return await self._position_repo.get_today_closed_losses(db, user_id)

    # --- Portfolio Summary ---

    async def get_summary(self, db: AsyncSession, user_id: UUID) -> dict:
        """Full portfolio summary."""
        positions = await self._position_repo.get_all_open(db, user_id)
        total_cash = await self.get_total_cash(db, user_id)
        peak_equity = await self.get_peak_equity(db, user_id)

        positions_value = sum(
            (p.market_value for p in positions), Decimal("0")
        )
        unrealized_pnl = sum(
            (p.unrealized_pnl for p in positions), Decimal("0")
        )

        # All realized PnL (open + closed positions)
        from sqlalchemy import func
        result = await db.execute(
            select(func.coalesce(func.sum(Position.realized_pnl), Decimal("0")))
            .where(Position.user_id == user_id)
        )
        realized_pnl_total = result.scalar_one()

        equity = total_cash + positions_value
        total_return = unrealized_pnl + realized_pnl_total

        # Use initial_cash as denominator for total return percent
        initial_cash = self._config.initial_cash
        total_return_percent = (
            total_return / initial_cash * 100 if initial_cash > 0 else Decimal("0")
        )

        drawdown_percent = Decimal("0")
        if peak_equity > 0:
            drawdown_percent = max(
                (peak_equity - equity) / peak_equity * 100, Decimal("0")
            )

        return {
            "equity": equity,
            "cash": total_cash,
            "positions_value": positions_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl_total": realized_pnl_total,
            "total_return": total_return,
            "total_return_percent": total_return_percent,
            "drawdown_percent": drawdown_percent,
            "peak_equity": peak_equity,
            "open_positions_count": len(positions),
        }

    async def get_equity_breakdown(self, db: AsyncSession, user_id: UUID) -> dict:
        """Equity breakdown by market."""
        positions = await self._position_repo.get_all_open(db, user_id)
        balances = await self._cash_repo.get_all(db, user_id)

        equities_cash = Decimal("0")
        forex_cash = Decimal("0")
        for b in balances:
            if b.account_scope == "equities":
                equities_cash = b.balance
            elif b.account_scope.startswith("forex_pool"):
                forex_cash += b.balance

        equities_positions = Decimal("0")
        forex_positions = Decimal("0")
        for p in positions:
            if p.market == "forex":
                forex_positions += p.market_value
            else:
                equities_positions += p.market_value

        total_cash = equities_cash + forex_cash
        total_positions = equities_positions + forex_positions

        return {
            "total_equity": total_cash + total_positions,
            "total_cash": total_cash,
            "total_positions_value": total_positions,
            "equities_cash": equities_cash,
            "equities_positions_value": equities_positions,
            "forex_cash": forex_cash,
            "forex_positions_value": forex_positions,
        }

    # --- Read Operations ---

    async def get_position(
        self, db: AsyncSession, position_id: UUID, user_id: UUID
    ) -> Position:
        """Get position by ID. Verify ownership."""
        position = await self._position_repo.get_by_id(db, position_id)
        if not position or position.user_id != user_id:
            raise PositionNotFoundError(str(position_id))
        return position

    async def list_positions(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
        symbol: str | None = None,
        status: str | None = None,
        market: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Position], int]:
        """List positions with filters and pagination."""
        return await self._position_repo.get_filtered(
            db, user_id,
            strategy_id=strategy_id,
            symbol=symbol,
            status=status,
            market=market,
            page=page,
            page_size=page_size,
        )

    async def get_open_positions_for_user(
        self, db: AsyncSession, user_id: UUID
    ) -> list[Position]:
        """All open positions for the user."""
        return await self._position_repo.get_all_open(db, user_id)

    async def get_closed_positions(
        self,
        db: AsyncSession,
        user_id: UUID,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Position], int]:
        """Closed positions with date range filter."""
        return await self._position_repo.get_closed_filtered(
            db, user_id,
            date_start=date_start,
            date_end=date_end,
            page=page,
            page_size=page_size,
        )

    # --- Cash Initialization ---

    async def initialize_cash(self, db: AsyncSession, user_id: UUID) -> None:
        """Create initial cash balances if they don't exist."""
        # Equities account
        existing = await self._cash_repo.get_by_scope(db, "equities", user_id)
        if not existing:
            await self._cash_repo.create(db, CashBalance(
                account_scope="equities",
                balance=self._config.initial_cash,
                user_id=user_id,
            ))

        # Forex pool accounts
        for i in range(1, self._config.forex_pool_size + 1):
            scope = f"forex_pool_{i}"
            existing = await self._cash_repo.get_by_scope(db, scope, user_id)
            if not existing:
                await self._cash_repo.create(db, CashBalance(
                    account_scope=scope,
                    balance=self._config.forex_capital_per_account,
                    user_id=user_id,
                ))

        # Initialize meta
        peak = await self._meta_repo.get(db, "peak_equity", user_id)
        if not peak:
            total_cash = await self._cash_repo.get_total_cash(db, user_id)
            await self._meta_repo.set(db, "peak_equity", str(total_cash), user_id)
            await self._meta_repo.set(db, "initial_capital", str(self._config.initial_cash), user_id)

        logger.info("Cash balances initialized for user %s", user_id)

    # --- Snapshots ---

    async def get_equity_curve(
        self, db: AsyncSession, user_id: UUID,
        start: datetime | None = None, end: datetime | None = None,
    ) -> list[dict]:
        from app.portfolio.startup import get_snapshot_manager
        mgr = get_snapshot_manager()
        if not mgr:
            return []
        return await mgr.get_equity_curve(db, user_id, start=start, end=end)

    async def get_snapshots(
        self, db: AsyncSession, user_id: UUID,
        snapshot_type: str | None = None,
        start: datetime | None = None, end: datetime | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list, int]:
        from app.portfolio.startup import get_snapshot_manager
        mgr = get_snapshot_manager()
        if not mgr:
            return [], 0
        return await mgr.get_snapshots(
            db, user_id, snapshot_type=snapshot_type,
            start=start, end=end, page=page, page_size=page_size,
        )

    # --- PnL ---

    async def get_pnl_entries(
        self, db: AsyncSession, user_id: UUID,
        strategy_id: UUID | None = None, symbol: str | None = None,
        start: datetime | None = None, end: datetime | None = None,
        page: int = 1, page_size: int = 50,
    ) -> tuple[list, int]:
        from app.portfolio.startup import get_pnl_ledger
        ledger = get_pnl_ledger()
        if not ledger:
            return [], 0
        return await ledger.get_entries(
            db, user_id, strategy_id=strategy_id, symbol=symbol,
            start=start, end=end, page=page, page_size=page_size,
        )

    async def get_pnl_summary(
        self, db: AsyncSession, user_id: UUID,
        strategy_id: UUID | None = None,
    ) -> dict:
        from app.portfolio.startup import get_pnl_ledger
        ledger = get_pnl_ledger()
        if not ledger:
            return {"today": 0, "this_week": 0, "this_month": 0, "total": 0,
                    "by_strategy": {}, "by_symbol": {}}
        return await ledger.get_summary(db, user_id, strategy_id=strategy_id)

    # --- Dividends ---

    async def get_dividend_payments(
        self, db: AsyncSession, user_id: UUID,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list, int]:
        from app.portfolio.dividends import DividendProcessor
        processor = DividendProcessor()
        return await processor.get_payment_history(db, user_id, page=page, page_size=page_size)

    async def get_upcoming_dividends(
        self, db: AsyncSession, user_id: UUID,
    ) -> list[dict]:
        from app.portfolio.dividends import DividendProcessor
        processor = DividendProcessor()
        return await processor.get_upcoming(db, user_id)

    async def get_dividend_summary(
        self, db: AsyncSession, user_id: UUID,
    ) -> dict:
        from app.portfolio.dividends import DividendProcessor
        processor = DividendProcessor()
        return await processor.get_income_summary(db, user_id)

    # --- Metrics ---

    async def get_metrics(
        self, db: AsyncSession, user_id: UUID,
        strategy_id: UUID | None = None,
    ) -> dict:
        from app.portfolio.metrics import PerformanceMetrics
        metrics = PerformanceMetrics(self._config)
        return await metrics.calculate(db, user_id, strategy_id=strategy_id)

    # --- Admin ---

    async def reset_peak_equity(
        self, db: AsyncSession, user_id: UUID, admin_user: str,
    ) -> None:
        current_equity = await self.get_equity(db, user_id)
        await self._meta_repo.set(db, "peak_equity", str(current_equity), user_id)
        logger.info("Peak equity reset by %s for user %s to %s", admin_user, user_id, current_equity)

    async def adjust_cash(
        self, db: AsyncSession, user_id: UUID, account_scope: str,
        amount: Decimal, reason: str, admin_user: str,
    ) -> CashBalance:
        cash = await self._cash_repo.update_balance(db, account_scope, user_id, amount)
        logger.info(
            "Cash adjusted by %s: user=%s scope=%s amount=%s reason=%s",
            admin_user, user_id, account_scope, amount, reason,
        )
        return cash
