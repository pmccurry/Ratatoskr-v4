"""Indicator helpers for the Strategy SDK.

All methods accept a ``pd.DataFrame`` (the bar history passed to ``on_bar``)
and a ``source`` column name.  They extract the column internally so users
never need to write ``history["close"]``.
"""

from __future__ import annotations

import math

import pandas as pd


class Indicators:
    """Indicator calculations for Python strategies.

    Every method that returns a scalar gives the **most recent** value.
    Methods ending in ``_series`` return the full ``pd.Series``.
    """

    # ------------------------------------------------------------------
    # Moving averages
    # ------------------------------------------------------------------

    @staticmethod
    def sma(history: pd.DataFrame, period: int, source: str = "close") -> float:
        """Simple Moving Average — latest value."""
        if len(history) < period:
            return float("nan")
        return float(history[source].tail(period).mean())

    @staticmethod
    def sma_series(history: pd.DataFrame, period: int, source: str = "close") -> pd.Series:
        """Simple Moving Average — full series."""
        return history[source].rolling(window=period).mean()

    @staticmethod
    def ema(history: pd.DataFrame, period: int, source: str = "close") -> float:
        """Exponential Moving Average — latest value."""
        if len(history) < period:
            return float("nan")
        return float(history[source].ewm(span=period, adjust=False).mean().iloc[-1])

    # ------------------------------------------------------------------
    # Momentum
    # ------------------------------------------------------------------

    @staticmethod
    def rsi(history: pd.DataFrame, period: int = 14, source: str = "close") -> float:
        """Relative Strength Index (0–100) — latest value."""
        if len(history) < period + 1:
            return float("nan")
        delta = history[source].diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi_val = 100 - (100 / (1 + rs))
        return float(rsi_val.iloc[-1])

    # ------------------------------------------------------------------
    # Volatility
    # ------------------------------------------------------------------

    @staticmethod
    def atr(history: pd.DataFrame, period: int = 14) -> float:
        """Average True Range — latest value."""
        if len(history) < period + 1:
            return float("nan")
        high = history["high"]
        low = history["low"]
        prev_close = history["close"].shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return float(tr.rolling(window=period).mean().iloc[-1])

    @staticmethod
    def bollinger(
        history: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        source: str = "close",
    ) -> tuple[float, float, float]:
        """Bollinger Bands — returns ``(upper, middle, lower)``."""
        sma = history[source].rolling(window=period).mean()
        std = history[source].rolling(window=period).std()
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        return (float(upper.iloc[-1]), float(sma.iloc[-1]), float(lower.iloc[-1]))

    @staticmethod
    def macd(
        history: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        source: str = "close",
    ) -> tuple[float, float, float]:
        """MACD — returns ``(macd_line, signal_line, histogram)``."""
        fast_ema = history[source].ewm(span=fast, adjust=False).mean()
        slow_ema = history[source].ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return (float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1]))

    # ------------------------------------------------------------------
    # Lookback extremes
    # ------------------------------------------------------------------

    @staticmethod
    def highest(history: pd.DataFrame, period: int, source: str = "high") -> float:
        """Highest value over last *period* bars."""
        return float(history[source].tail(period).max())

    @staticmethod
    def lowest(history: pd.DataFrame, period: int, source: str = "low") -> float:
        """Lowest value over last *period* bars."""
        return float(history[source].tail(period).min())

    # ------------------------------------------------------------------
    # Crossover helpers
    # ------------------------------------------------------------------

    @staticmethod
    def crosses_above(series_a: pd.Series, series_b) -> bool:
        """True if *series_a* crossed above *series_b* on the latest bar.

        ``series_b`` can be a ``pd.Series`` or a scalar (int/float).
        """
        if len(series_a) < 2:
            return False
        prev_a = float(series_a.iloc[-2])
        curr_a = float(series_a.iloc[-1])
        if math.isnan(prev_a) or math.isnan(curr_a):
            return False
        if isinstance(series_b, (int, float)):
            return prev_a <= series_b and curr_a > series_b
        if len(series_b) < 2:
            return False
        prev_b = float(series_b.iloc[-2])
        curr_b = float(series_b.iloc[-1])
        if math.isnan(prev_b) or math.isnan(curr_b):
            return False
        return prev_a <= prev_b and curr_a > curr_b

    @staticmethod
    def crosses_below(series_a: pd.Series, series_b) -> bool:
        """True if *series_a* crossed below *series_b* on the latest bar.

        ``series_b`` can be a ``pd.Series`` or a scalar (int/float).
        """
        if len(series_a) < 2:
            return False
        prev_a = float(series_a.iloc[-2])
        curr_a = float(series_a.iloc[-1])
        if math.isnan(prev_a) or math.isnan(curr_a):
            return False
        if isinstance(series_b, (int, float)):
            return prev_a >= series_b and curr_a < series_b
        if len(series_b) < 2:
            return False
        prev_b = float(series_b.iloc[-2])
        curr_b = float(series_b.iloc[-1])
        if math.isnan(prev_b) or math.isnan(curr_b):
            return False
        return prev_a >= prev_b and curr_a < curr_b
