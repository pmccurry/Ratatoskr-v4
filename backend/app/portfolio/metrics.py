"""Performance metrics — calculates trading performance on demand."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolio.models import (
    DividendPayment,
    PortfolioSnapshot,
    Position,
    RealizedPnlEntry,
)

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Calculates trading performance metrics on demand."""

    def __init__(self, config: object):
        self._config = config

    async def calculate(
        self,
        db: AsyncSession,
        user_id: UUID,
        strategy_id: UUID | None = None,
    ) -> dict:
        """Calculate all performance metrics."""
        # Get PnL entries
        query = select(RealizedPnlEntry).where(
            RealizedPnlEntry.user_id == user_id
        )
        if strategy_id:
            query = query.where(RealizedPnlEntry.strategy_id == strategy_id)
        query = query.order_by(RealizedPnlEntry.closed_at.asc())

        result = await db.execute(query)
        entries = list(result.scalars().all())

        # Basic stats
        total_trades = len(entries)
        winners = [e for e in entries if e.net_pnl > 0]
        losers = [e for e in entries if e.net_pnl < 0]
        winning_trades = len(winners)
        losing_trades = len(losers)

        total_pnl = sum((e.net_pnl for e in entries), Decimal("0"))
        total_fees = sum((e.fees for e in entries), Decimal("0"))

        win_rate = Decimal("0")
        if total_trades > 0:
            win_rate = Decimal(str(winning_trades)) / Decimal(str(total_trades)) * 100

        # Average winner / loser
        average_winner = Decimal("0")
        if winners:
            average_winner = sum((e.net_pnl for e in winners), Decimal("0")) / len(winners)

        average_loser = Decimal("0")
        if losers:
            average_loser = sum((e.net_pnl for e in losers), Decimal("0")) / len(losers)

        # Profit factor
        profit_factor = Decimal("0")
        total_wins = sum((e.net_pnl for e in winners), Decimal("0"))
        total_losses = abs(sum((e.net_pnl for e in losers), Decimal("0")))
        if total_losses > 0:
            profit_factor = total_wins / total_losses

        # Risk reward ratio
        risk_reward_ratio = Decimal("0")
        if average_loser != 0:
            risk_reward_ratio = abs(average_winner / average_loser)

        # Average holding period
        average_hold_bars = Decimal("0")
        if total_trades > 0:
            total_bars = sum(e.holding_period_bars for e in entries)
            average_hold_bars = Decimal(str(total_bars)) / Decimal(str(total_trades))

        # Streaks
        longest_win_streak, longest_loss_streak = self._calculate_streaks(entries)

        # Unrealized PnL
        pos_query = select(
            func.coalesce(func.sum(Position.unrealized_pnl), Decimal("0"))
        ).where(Position.user_id == user_id, Position.status == "open")
        if strategy_id:
            pos_query = pos_query.where(Position.strategy_id == strategy_id)
        unrealized_result = await db.execute(pos_query)
        unrealized_pnl = unrealized_result.scalar_one()

        # Dividend income
        div_query = select(
            func.coalesce(func.sum(DividendPayment.net_amount), Decimal("0"))
        ).where(
            DividendPayment.user_id == user_id,
            DividendPayment.status == "paid",
        )
        div_result = await db.execute(div_query)
        total_dividend_income = div_result.scalar_one()

        # Total return
        total_return = total_pnl + unrealized_pnl + total_dividend_income

        # Total return percent (relative to initial capital)
        total_return_percent = Decimal("0")
        initial_cash = Decimal(str(self._config.initial_cash))
        if initial_cash > 0:
            total_return_percent = total_return / initial_cash * 100

        # Sharpe & Sortino
        sharpe_ratio = await self._calculate_sharpe(
            db, user_id, self._config.risk_free_rate
        )
        sortino_ratio = await self._calculate_sortino(
            db, user_id, self._config.risk_free_rate
        )

        # Max drawdown
        max_drawdown = await self._calculate_max_drawdown(db, user_id)

        return {
            "total_return": total_return,
            "total_return_percent": total_return_percent,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "average_winner": average_winner,
            "average_loser": average_loser,
            "risk_reward_ratio": risk_reward_ratio,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "average_hold_bars": average_hold_bars,
            "longest_win_streak": longest_win_streak,
            "longest_loss_streak": longest_loss_streak,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "total_fees": total_fees,
            "total_dividend_income": total_dividend_income,
        }

    async def _calculate_sharpe(
        self,
        db: AsyncSession,
        user_id: UUID,
        risk_free_rate: Decimal,
    ) -> Decimal | None:
        """Sharpe ratio from daily close snapshots."""
        result = await db.execute(
            select(PortfolioSnapshot.equity)
            .where(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_type == "daily_close",
            )
            .order_by(PortfolioSnapshot.ts.asc())
        )
        equities = [row[0] for row in result.all()]

        if len(equities) < 2:
            return None

        # Calculate daily returns
        returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                daily_return = (equities[i] - equities[i - 1]) / equities[i - 1]
                returns.append(daily_return)

        if not returns:
            return None

        n = len(returns)
        mean_return = sum(returns) / n
        daily_rf = risk_free_rate / 252

        variance = sum((r - mean_return) ** 2 for r in returns) / n
        std_dev = variance ** Decimal("0.5")

        if std_dev == 0:
            return None

        # Annualized
        sharpe = (mean_return - daily_rf) / std_dev * Decimal("252") ** Decimal("0.5")
        return round(sharpe, 4)

    async def _calculate_sortino(
        self,
        db: AsyncSession,
        user_id: UUID,
        risk_free_rate: Decimal,
    ) -> Decimal | None:
        """Sortino ratio — like Sharpe but only downside deviation."""
        result = await db.execute(
            select(PortfolioSnapshot.equity)
            .where(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_type == "daily_close",
            )
            .order_by(PortfolioSnapshot.ts.asc())
        )
        equities = [row[0] for row in result.all()]

        if len(equities) < 2:
            return None

        returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                daily_return = (equities[i] - equities[i - 1]) / equities[i - 1]
                returns.append(daily_return)

        if not returns:
            return None

        n = len(returns)
        mean_return = sum(returns) / n
        daily_rf = risk_free_rate / 252

        # Only negative returns for downside deviation.
        # Downside deviation uses ALL returns in the denominator (not just
        # negative returns). This is the standard convention for Sortino ratio
        # where downside_dev = sqrt(sum(min(0, r-MAR)²) / N) and N = total periods.
        negative_returns = [r for r in returns if r < daily_rf]
        if not negative_returns:
            return None

        downside_variance = sum(
            (r - daily_rf) ** 2 for r in negative_returns
        ) / n
        downside_dev = downside_variance ** Decimal("0.5")

        if downside_dev == 0:
            return None

        sortino = (mean_return - daily_rf) / downside_dev * Decimal("252") ** Decimal("0.5")
        return round(sortino, 4)

    async def _calculate_max_drawdown(
        self, db: AsyncSession, user_id: UUID
    ) -> Decimal:
        """Max peak-to-trough decline from snapshot time series."""
        result = await db.execute(
            select(PortfolioSnapshot.equity)
            .where(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_type.in_(["periodic", "daily_close"]),
            )
            .order_by(PortfolioSnapshot.ts.asc())
        )
        equities = [row[0] for row in result.all()]

        if not equities:
            return Decimal("0")

        peak = equities[0]
        max_dd = Decimal("0")

        for equity in equities:
            if equity > peak:
                peak = equity
            if peak > 0:
                dd = (peak - equity) / peak * 100
                if dd > max_dd:
                    max_dd = dd

        return round(max_dd, 4)

    def _calculate_streaks(
        self, entries: list
    ) -> tuple[int, int]:
        """Longest win and loss streaks from PnL entries."""
        longest_win = 0
        longest_loss = 0
        current_win = 0
        current_loss = 0

        for entry in entries:
            if entry.net_pnl > 0:
                current_win += 1
                current_loss = 0
                if current_win > longest_win:
                    longest_win = current_win
            elif entry.net_pnl < 0:
                current_loss += 1
                current_win = 0
                if current_loss > longest_loss:
                    longest_loss = current_loss
            else:
                current_win = 0
                current_loss = 0

        return longest_win, longest_loss
