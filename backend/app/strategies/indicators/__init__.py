"""Indicator library — register all MVP indicators."""

from app.strategies.indicators.compute import (
    compute_adx,
    compute_atr,
    compute_bbands,
    compute_cci,
    compute_close,
    compute_ema,
    compute_high,
    compute_keltner,
    compute_low,
    compute_macd,
    compute_mfi,
    compute_minus_di,
    compute_obv,
    compute_open,
    compute_plus_di,
    compute_prev_close,
    compute_prev_high,
    compute_prev_low,
    compute_rsi,
    compute_sma,
    compute_stochastic,
    compute_volume,
    compute_volume_sma,
    compute_vwap,
    compute_williams_r,
    compute_wma,
)
from app.strategies.indicators.registry import (
    IndicatorDefinition,
    IndicatorParam,
    IndicatorRegistry,
)

_SOURCE_PARAM = IndicatorParam(
    "source", "select", default="close",
    options=["close", "open", "high", "low", "hl2", "hlc3", "ohlc4"],
)

# Create the global registry
registry = IndicatorRegistry()

# === Trend (4) ===

registry.register(IndicatorDefinition(
    key="sma",
    name="Simple Moving Average",
    category="trend",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=500),
        _SOURCE_PARAM,
    ],
    outputs=["number"],
    description="Average of the last N bars",
    compute_fn=compute_sma,
))

registry.register(IndicatorDefinition(
    key="ema",
    name="Exponential Moving Average",
    category="trend",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=500),
        _SOURCE_PARAM,
    ],
    outputs=["number"],
    description="Exponentially weighted moving average with recent bar emphasis",
    compute_fn=compute_ema,
))

registry.register(IndicatorDefinition(
    key="wma",
    name="Weighted Moving Average",
    category="trend",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=500),
        _SOURCE_PARAM,
    ],
    outputs=["number"],
    description="Linearly weighted moving average favoring recent bars",
    compute_fn=compute_wma,
))

registry.register(IndicatorDefinition(
    key="vwap",
    name="Volume Weighted Average Price",
    category="trend",
    params=[],
    outputs=["number"],
    description="Average price weighted by volume across the session",
    compute_fn=compute_vwap,
))

# === Momentum (6) ===

registry.register(IndicatorDefinition(
    key="rsi",
    name="Relative Strength Index",
    category="momentum",
    params=[
        IndicatorParam("period", "int", default=14, min=2, max=200),
        _SOURCE_PARAM,
    ],
    outputs=["number"],
    description="Momentum oscillator measuring speed and magnitude of price changes (0-100)",
    compute_fn=compute_rsi,
))

registry.register(IndicatorDefinition(
    key="macd",
    name="MACD",
    category="momentum",
    params=[
        IndicatorParam("fast", "int", default=12, min=2, max=100),
        IndicatorParam("slow", "int", default=26, min=2, max=200),
        IndicatorParam("signal", "int", default=9, min=2, max=100),
    ],
    outputs=["macd_line", "signal_line", "histogram"],
    description="Moving Average Convergence Divergence — trend-following momentum indicator",
    compute_fn=compute_macd,
))

registry.register(IndicatorDefinition(
    key="stochastic",
    name="Stochastic Oscillator",
    category="momentum",
    params=[
        IndicatorParam("k_period", "int", default=14, min=2, max=200),
        IndicatorParam("d_period", "int", default=3, min=2, max=50),
        IndicatorParam("slowing", "int", default=3, min=1, max=50),
    ],
    outputs=["k", "d"],
    description="Compares closing price to price range over a period (0-100)",
    compute_fn=compute_stochastic,
))

registry.register(IndicatorDefinition(
    key="cci",
    name="Commodity Channel Index",
    category="momentum",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=200),
    ],
    outputs=["number"],
    description="Measures current price level relative to average price over a period",
    compute_fn=compute_cci,
))

registry.register(IndicatorDefinition(
    key="mfi",
    name="Money Flow Index",
    category="momentum",
    params=[
        IndicatorParam("period", "int", default=14, min=2, max=200),
    ],
    outputs=["number"],
    description="Volume-weighted RSI — measures buying and selling pressure (0-100)",
    compute_fn=compute_mfi,
))

registry.register(IndicatorDefinition(
    key="williams_r",
    name="Williams %R",
    category="momentum",
    params=[
        IndicatorParam("period", "int", default=14, min=2, max=200),
    ],
    outputs=["number"],
    description="Momentum indicator showing overbought/oversold levels (-100 to 0)",
    compute_fn=compute_williams_r,
))

# === Volatility (3) ===

registry.register(IndicatorDefinition(
    key="bbands",
    name="Bollinger Bands",
    category="volatility",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=200),
        IndicatorParam("std_dev", "float", default=2.0, min=0.1, max=5.0),
    ],
    outputs=["upper", "middle", "lower"],
    description="Volatility bands placed above and below a moving average",
    compute_fn=compute_bbands,
))

registry.register(IndicatorDefinition(
    key="atr",
    name="Average True Range",
    category="volatility",
    params=[
        IndicatorParam("period", "int", default=14, min=2, max=200),
    ],
    outputs=["number"],
    description="Measures market volatility based on price range",
    compute_fn=compute_atr,
))

registry.register(IndicatorDefinition(
    key="keltner",
    name="Keltner Channels",
    category="volatility",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=200),
        IndicatorParam("atr_multiplier", "float", default=1.5, min=0.1, max=5.0),
    ],
    outputs=["upper", "middle", "lower"],
    description="Volatility-based envelope set above and below an EMA",
    compute_fn=compute_keltner,
))

# === Volume (3) ===

registry.register(IndicatorDefinition(
    key="volume",
    name="Volume",
    category="volume",
    params=[],
    outputs=["number"],
    description="Current bar volume",
    compute_fn=compute_volume,
))

registry.register(IndicatorDefinition(
    key="volume_sma",
    name="Volume SMA",
    category="volume",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=500),
    ],
    outputs=["number"],
    description="Simple moving average of volume",
    compute_fn=compute_volume_sma,
))

registry.register(IndicatorDefinition(
    key="obv",
    name="On Balance Volume",
    category="volume",
    params=[],
    outputs=["number"],
    description="Cumulative volume indicator — adds volume on up days, subtracts on down days",
    compute_fn=compute_obv,
))

# === Trend Strength (3) ===

registry.register(IndicatorDefinition(
    key="adx",
    name="Average Directional Index",
    category="trend_strength",
    params=[
        IndicatorParam("period", "int", default=14, min=2, max=200),
    ],
    outputs=["number"],
    description="Measures trend strength regardless of direction (0-100)",
    compute_fn=compute_adx,
))

registry.register(IndicatorDefinition(
    key="plus_di",
    name="Plus Directional Indicator",
    category="trend_strength",
    params=[
        IndicatorParam("period", "int", default=14, min=2, max=200),
    ],
    outputs=["number"],
    description="Measures upward price movement strength (+DI)",
    compute_fn=compute_plus_di,
))

registry.register(IndicatorDefinition(
    key="minus_di",
    name="Minus Directional Indicator",
    category="trend_strength",
    params=[
        IndicatorParam("period", "int", default=14, min=2, max=200),
    ],
    outputs=["number"],
    description="Measures downward price movement strength (-DI)",
    compute_fn=compute_minus_di,
))

# === Price Reference (7) ===

registry.register(IndicatorDefinition(
    key="close",
    name="Close",
    category="price_reference",
    params=[],
    outputs=["number"],
    description="Latest closing price",
    compute_fn=compute_close,
))

registry.register(IndicatorDefinition(
    key="open",
    name="Open",
    category="price_reference",
    params=[],
    outputs=["number"],
    description="Latest opening price",
    compute_fn=compute_open,
))

registry.register(IndicatorDefinition(
    key="high",
    name="High",
    category="price_reference",
    params=[],
    outputs=["number"],
    description="Latest high price",
    compute_fn=compute_high,
))

registry.register(IndicatorDefinition(
    key="low",
    name="Low",
    category="price_reference",
    params=[],
    outputs=["number"],
    description="Latest low price",
    compute_fn=compute_low,
))

registry.register(IndicatorDefinition(
    key="prev_close",
    name="Previous Close",
    category="price_reference",
    params=[],
    outputs=["number"],
    description="Previous bar's closing price",
    compute_fn=compute_prev_close,
))

registry.register(IndicatorDefinition(
    key="prev_high",
    name="Previous High",
    category="price_reference",
    params=[],
    outputs=["number"],
    description="Previous bar's high price",
    compute_fn=compute_prev_high,
))

registry.register(IndicatorDefinition(
    key="prev_low",
    name="Previous Low",
    category="price_reference",
    params=[],
    outputs=["number"],
    description="Previous bar's low price",
    compute_fn=compute_prev_low,
))


def get_registry() -> IndicatorRegistry:
    """Return the global indicator registry."""
    return registry
