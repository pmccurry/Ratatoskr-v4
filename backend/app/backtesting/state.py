from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime


@dataclass
class BacktestTradeRecord:
    """In-memory trade tracking during backtest."""
    symbol: str
    side: str  # "long" or "short"
    quantity: Decimal
    entry_time: datetime
    entry_price: Decimal
    entry_bar_index: int
    fees: Decimal = Decimal("0")

    exit_time: datetime | None = None
    exit_price: Decimal | None = None
    exit_bar_index: int | None = None
    exit_reason: str | None = None

    pnl: Decimal | None = None
    pnl_percent: Decimal | None = None
    hold_bars: int | None = None
    max_favorable: Decimal = Decimal("0")  # max favorable excursion
    max_adverse: Decimal = Decimal("0")    # max adverse excursion

    def update_excursion(self, bar: dict):
        """Track MFE/MAE based on bar high/low."""
        if self.side == "long":
            favorable = bar["high"] - self.entry_price
            adverse = self.entry_price - bar["low"]
        else:
            favorable = self.entry_price - bar["low"]
            adverse = bar["high"] - self.entry_price
        self.max_favorable = max(self.max_favorable, favorable)
        self.max_adverse = max(self.max_adverse, adverse)


@dataclass
class EquityPoint:
    bar_time: datetime
    bar_index: int
    equity: Decimal
    cash: Decimal
    open_positions: int
    unrealized_pnl: Decimal
    drawdown_pct: Decimal


class BacktestState:
    def __init__(self, initial_capital: Decimal, position_sizing: dict, exit_config: dict, timeframe: str = "1h"):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position_sizing = position_sizing
        self.exit_config = exit_config
        self.timeframe = timeframe

        self.open_positions: list[BacktestTradeRecord] = []
        self.closed_trades: list[BacktestTradeRecord] = []
        self.equity_points: list[EquityPoint] = []
        self.peak_equity = initial_capital
        self.bars_processed = 0
        self.warmup_complete = False
        self._trade_occurred = False

    def get_current_equity(self, bar: dict) -> Decimal:
        """Current equity = cash + unrealized PnL."""
        unrealized = sum(self._calc_unrealized(pos, bar) for pos in self.open_positions)
        return self.cash + unrealized

    def _calc_unrealized(self, pos: BacktestTradeRecord, bar: dict) -> Decimal:
        """Calculate unrealized PnL for a position."""
        current = bar["close"]
        if pos.side == "long":
            return (current - pos.entry_price) * pos.quantity
        else:
            return (pos.entry_price - current) * pos.quantity

    def record_equity(self, bar: dict, bar_index: int):
        """Record equity curve point at appropriate intervals."""
        # Sample interval: every bar for non-1m, every 10 bars for 1m
        sample_interval = 10 if self.timeframe == "1m" else 1

        if bar_index % sample_interval == 0 or self._trade_occurred:
            unrealized = sum(self._calc_unrealized(pos, bar) for pos in self.open_positions)
            equity = self.cash + unrealized
            self.peak_equity = max(self.peak_equity, equity)
            drawdown = ((self.peak_equity - equity) / self.peak_equity * Decimal("100")) if self.peak_equity > 0 else Decimal("0")

            self.equity_points.append(EquityPoint(
                bar_time=bar["timestamp"],
                bar_index=bar_index,
                equity=equity,
                cash=self.cash,
                open_positions=len(self.open_positions),
                unrealized_pnl=unrealized,
                drawdown_pct=drawdown,
            ))
            self._trade_occurred = False

        self.bars_processed += 1
