import math
from decimal import Decimal
from .state import BacktestState, BacktestTradeRecord


def compute_metrics(state: BacktestState) -> dict:
    """Compute comprehensive backtest performance metrics."""
    trades = state.closed_trades

    if not trades:
        return {
            "total_trades": 0,
            "note": "No trades generated",
            "initial_capital": float(state.initial_capital),
            "final_equity": float(state.equity_points[-1].equity) if state.equity_points else float(state.initial_capital),
            "bars_processed": state.bars_processed,
        }

    winners = [t for t in trades if t.pnl and t.pnl > 0]
    losers = [t for t in trades if t.pnl is not None and t.pnl <= 0]

    gross_profit = sum(t.pnl for t in winners) if winners else Decimal("0")
    gross_loss = abs(sum(t.pnl for t in losers)) if losers else Decimal("0")
    total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
    total_fees = sum(t.fees for t in trades)

    # Per-trade returns for Sharpe ratio
    returns = []
    for t in trades:
        if t.pnl is not None and t.entry_price and t.quantity:
            cost = t.entry_price * t.quantity
            if cost > 0:
                returns.append(float(t.pnl / cost))

    final_equity = float(state.equity_points[-1].equity) if state.equity_points else float(state.initial_capital)

    metrics = {
        # Trade counts
        "total_trades": len(trades),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(len(winners) / len(trades) * 100, 2),

        # PnL
        "total_pnl": float(total_pnl),
        "total_fees": float(total_fees),
        "net_pnl": float(total_pnl - total_fees),
        "avg_pnl_per_trade": float(total_pnl / len(trades)),
        "best_trade": float(max(t.pnl for t in trades if t.pnl is not None)),
        "worst_trade": float(min(t.pnl for t in trades if t.pnl is not None)),

        # Ratios
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else None,
        "avg_win": float(gross_profit / len(winners)) if winners else 0,
        "avg_loss": float(gross_loss / len(losers)) if losers else 0,
        "avg_win_loss_ratio": (float(gross_profit / len(winners)) / float(gross_loss / len(losers))) if (winners and losers) else None,

        # Risk
        "max_drawdown_pct": float(max(p.drawdown_pct for p in state.equity_points)) if state.equity_points else 0,
        "sharpe_ratio": _annualized_sharpe(returns, state.timeframe),

        # Duration
        "avg_hold_bars": round(sum(t.hold_bars or 0 for t in trades) / len(trades), 1),
        "max_hold_bars": max(t.hold_bars or 0 for t in trades),

        # Streaks
        "max_winning_streak": _max_streak(trades, winning=True),
        "max_losing_streak": _max_streak(trades, winning=False),

        # Excursion
        "avg_max_favorable": float(sum(t.max_favorable for t in trades) / len(trades)),
        "avg_max_adverse": float(sum(t.max_adverse for t in trades) / len(trades)),

        # Capital
        "initial_capital": float(state.initial_capital),
        "final_equity": final_equity,
        "total_return_pct": round((final_equity - float(state.initial_capital)) / float(state.initial_capital) * 100, 2),
        "bars_processed": state.bars_processed,
    }

    return metrics


def _annualized_sharpe(returns: list[float], timeframe: str) -> float:
    """Calculate annualized Sharpe ratio from per-trade returns."""
    if len(returns) < 2:
        return 0.0

    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    std_return = math.sqrt(variance)

    if std_return == 0:
        return 0.0

    # Use number of trades as annualization factor (capped by periods/year)
    periods_per_year = {"1m": 525600, "1h": 8760, "4h": 2190, "1d": 365}.get(timeframe, 365)
    factor = min(len(returns), periods_per_year)

    return round(float((mean_return / std_return) * math.sqrt(factor)), 4)


def _max_streak(trades: list[BacktestTradeRecord], winning: bool) -> int:
    """Find maximum consecutive winning or losing streak."""
    max_streak = 0
    current = 0
    for t in trades:
        if t.pnl is None:
            continue
        is_win = t.pnl > 0
        if is_win == winning:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak
