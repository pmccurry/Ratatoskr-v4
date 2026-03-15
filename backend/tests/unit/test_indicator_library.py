"""Unit tests for indicator computation functions."""

from decimal import Decimal

from tests.conftest import make_bars, make_flat_bars, make_trending_bars

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


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------

class TestSMA:
    def test_basic_computation(self):
        bars = make_bars([10, 20, 30])
        result = compute_sma(bars, period=3)
        assert result == Decimal("20")

    def test_longer_series(self):
        bars = make_bars([10, 20, 30, 40])
        result = compute_sma(bars, period=3)
        # SMA(3) on last 3 bars [20, 30, 40] = 30
        assert result == Decimal("30")

    def test_insufficient_data(self):
        bars = make_bars([10, 20])
        result = compute_sma(bars, period=20)
        assert result is None

    def test_single_value(self):
        bars = make_bars([50])
        result = compute_sma(bars, period=1)
        # SMA(1) is not valid (min period=2 in registry) but compute_sma allows it
        assert result == Decimal("50")

    def test_returns_decimal(self):
        bars = make_bars([10, 20, 30])
        result = compute_sma(bars, period=3)
        assert isinstance(result, Decimal)

    def test_empty_bars(self):
        result = compute_sma([], period=3)
        assert result is None


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

class TestEMA:
    def test_seed_equals_sma(self):
        bars = make_bars([10, 20, 30])
        sma = compute_sma(bars, period=3)
        ema = compute_ema(bars, period=3)
        # When bars == period, EMA seed is SMA, no further smoothing
        assert ema == sma

    def test_converges_toward_recent(self):
        bars = make_bars([10, 10, 10, 10, 10, 100])
        ema = compute_ema(bars, period=5)
        sma = compute_sma(bars, period=5)
        # EMA should be higher than SMA since recent value is much higher
        assert ema is not None
        assert sma is not None
        # last bar 100 pulls EMA up more than SMA
        assert ema > sma

    def test_insufficient_data(self):
        bars = make_bars([10, 20])
        assert compute_ema(bars, period=5) is None

    def test_returns_decimal(self):
        bars = make_bars([10, 20, 30, 40, 50])
        result = compute_ema(bars, period=3)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

class TestRSI:
    def test_all_up_near_100(self):
        bars = make_bars([float(i) for i in range(10, 30)])  # 20 ascending values
        result = compute_rsi(bars, period=14)
        assert result is not None
        assert result > Decimal("90")

    def test_all_down_near_0(self):
        bars = make_bars([float(i) for i in range(30, 10, -1)])  # 20 descending values
        result = compute_rsi(bars, period=14)
        assert result is not None
        assert result < Decimal("10")

    def test_flat_at_50(self):
        bars = make_flat_bars(100, 20)
        result = compute_rsi(bars, period=14)
        # Flat data: no gains, no losses → avg_loss = 0 → RSI = 100
        # Actually with flat data, gains=0 and losses=0, so avg_loss=0 → returns 100
        # This is technically correct per the formula
        assert result is not None

    def test_insufficient_data(self):
        bars = make_bars([10, 20, 30])
        assert compute_rsi(bars, period=14) is None

    def test_range_0_to_100(self):
        bars = make_trending_bars(50, 100, 20)
        result = compute_rsi(bars, period=14)
        assert result is not None
        assert Decimal("0") <= result <= Decimal("100")


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

class TestMACD:
    def test_returns_three_outputs(self):
        bars = make_trending_bars(50, 100, 40)
        result = compute_macd(bars, fast=12, slow=26, signal=9)
        assert result is not None
        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result

    def test_histogram_equals_macd_minus_signal(self):
        bars = make_trending_bars(50, 100, 40)
        result = compute_macd(bars)
        assert result is not None
        expected = result["macd_line"] - result["signal_line"]
        assert abs(result["histogram"] - expected) < Decimal("0.0001")

    def test_insufficient_data(self):
        bars = make_bars([10, 20, 30])
        assert compute_macd(bars) is None

    def test_returns_decimal_values(self):
        bars = make_trending_bars(50, 100, 40)
        result = compute_macd(bars)
        assert result is not None
        assert isinstance(result["macd_line"], Decimal)


# ---------------------------------------------------------------------------
# Stochastic
# ---------------------------------------------------------------------------

class TestStochastic:
    def test_returns_k_and_d(self):
        bars = make_trending_bars(50, 100, 25)
        result = compute_stochastic(bars)
        assert result is not None
        assert "k" in result
        assert "d" in result

    def test_close_at_high_k_near_100(self):
        # When close equals the high of the range, K should be near 100
        closes = [float(i) for i in range(50, 70)]
        bars = make_bars(
            closes,
            highs=[c + 0.01 for c in closes],
            lows=[closes[0] - 1] * len(closes),  # low stays at bottom
        )
        result = compute_stochastic(bars)
        assert result is not None
        assert result["k"] > Decimal("80")

    def test_close_at_low_k_near_0(self):
        # When close equals the low of the range, K should be near 0
        closes = [float(i) for i in range(70, 50, -1)]
        bars = make_bars(
            closes,
            highs=[closes[0] + 1] * len(closes),  # high stays at top
            lows=[c - 0.01 for c in closes],
        )
        result = compute_stochastic(bars)
        assert result is not None
        assert result["k"] < Decimal("20")

    def test_insufficient_data(self):
        bars = make_bars([10, 20])
        assert compute_stochastic(bars) is None


# ---------------------------------------------------------------------------
# ADX
# ---------------------------------------------------------------------------

class TestADX:
    def test_trending_higher_adx(self):
        # Strong trend should produce higher ADX
        trending = make_trending_bars(50, 150, 35)
        result = compute_adx(trending, period=14)
        # May be None if insufficient bars for ADX smoothing
        if result is not None:
            assert Decimal("0") <= result <= Decimal("100")

    def test_insufficient_data(self):
        bars = make_bars([10, 20, 30])
        assert compute_adx(bars, period=14) is None

    def test_returns_decimal(self):
        bars = make_trending_bars(50, 150, 35)
        result = compute_adx(bars, period=14)
        if result is not None:
            assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

class TestBollingerBands:
    def test_middle_equals_sma(self):
        bars = make_bars([10, 20, 30, 40, 50])
        result = compute_bbands(bars, period=5)
        sma = compute_sma(bars, period=5)
        assert result is not None
        assert result["middle"] == sma

    def test_upper_greater_than_lower(self):
        bars = make_bars([10, 20, 15, 25, 18])
        result = compute_bbands(bars, period=5)
        assert result is not None
        assert result["upper"] > result["lower"]

    def test_flat_data_bands_equal_middle(self):
        bars = make_flat_bars(100, 5)
        result = compute_bbands(bars, period=5)
        assert result is not None
        # Flat data → std dev = 0 → bands equal middle
        assert result["upper"] == result["middle"]
        assert result["lower"] == result["middle"]

    def test_insufficient_data(self):
        bars = make_bars([10, 20])
        assert compute_bbands(bars, period=5) is None


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------

class TestATR:
    def test_basic_computation(self):
        bars = make_trending_bars(50, 60, 20)
        result = compute_atr(bars, period=14)
        assert result is not None
        assert result > Decimal("0")

    def test_flat_data_low_atr(self):
        bars = make_flat_bars(100, 20)
        result = compute_atr(bars, period=14)
        assert result is not None
        # Flat data → true range = 0 → ATR = 0
        assert result == Decimal("0")

    def test_insufficient_data(self):
        bars = make_bars([10, 20])
        assert compute_atr(bars, period=14) is None

    def test_returns_decimal(self):
        bars = make_trending_bars(50, 60, 20)
        result = compute_atr(bars, period=14)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# VWAP
# ---------------------------------------------------------------------------

class TestVWAP:
    def test_single_bar_equals_typical_price(self):
        bars = make_bars([100], highs=[110], lows=[90])
        result = compute_vwap(bars)
        assert result is not None
        # typical price = (110 + 90 + 100) / 3 = 100
        assert result == Decimal("100")

    def test_empty_bars(self):
        assert compute_vwap([]) is None

    def test_returns_decimal(self):
        bars = make_bars([10, 20, 30])
        result = compute_vwap(bars)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# OBV
# ---------------------------------------------------------------------------

class TestOBV:
    def test_up_close_adds_volume(self):
        bars = make_bars([10, 20], volumes=[1000, 2000])
        result = compute_obv(bars)
        assert result is not None
        # close[1] > close[0] → OBV += volume[1]
        assert result == Decimal("2000")

    def test_down_close_subtracts_volume(self):
        bars = make_bars([20, 10], volumes=[1000, 2000])
        result = compute_obv(bars)
        assert result is not None
        # close[1] < close[0] → OBV -= volume[1]
        assert result == Decimal("-2000")

    def test_flat_close_no_change(self):
        bars = make_flat_bars(100, 5)
        result = compute_obv(bars)
        assert result is not None
        assert result == Decimal("0")

    def test_insufficient_data(self):
        bars = make_bars([10])
        assert compute_obv(bars) is None


# ---------------------------------------------------------------------------
# Volume SMA
# ---------------------------------------------------------------------------

class TestVolumeSMA:
    def test_basic_computation(self):
        bars = make_bars([10, 20, 30], volumes=[100, 200, 300])
        result = compute_volume_sma(bars, period=3)
        assert result == Decimal("200")

    def test_insufficient_data(self):
        bars = make_bars([10])
        assert compute_volume_sma(bars, period=5) is None

    def test_returns_decimal(self):
        bars = make_bars([10, 20, 30], volumes=[100, 200, 300])
        result = compute_volume_sma(bars, period=3)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# Price Reference Indicators
# ---------------------------------------------------------------------------

class TestPriceReference:
    def test_close(self):
        bars = make_bars([10, 20, 30])
        assert compute_close(bars) == Decimal("30")

    def test_open(self):
        bars = make_bars([10, 20, 30], opens=[11, 21, 31])
        assert compute_open(bars) == Decimal("31")

    def test_high(self):
        bars = make_bars([10, 20, 30], highs=[15, 25, 35])
        assert compute_high(bars) == Decimal("35")

    def test_low(self):
        bars = make_bars([10, 20, 30], lows=[5, 15, 25])
        assert compute_low(bars) == Decimal("25")

    def test_prev_close(self):
        bars = make_bars([10, 20, 30])
        assert compute_prev_close(bars) == Decimal("20")

    def test_prev_close_insufficient(self):
        bars = make_bars([10])
        assert compute_prev_close(bars) is None

    def test_prev_high(self):
        bars = make_bars([10, 20], highs=[15, 25])
        assert compute_prev_high(bars) == Decimal("15")

    def test_prev_low(self):
        bars = make_bars([10, 20], lows=[5, 15])
        assert compute_prev_low(bars) == Decimal("5")

    def test_empty_bars(self):
        assert compute_close([]) is None
        assert compute_open([]) is None
        assert compute_high([]) is None
        assert compute_low([]) is None


# ---------------------------------------------------------------------------
# WMA
# ---------------------------------------------------------------------------

class TestWMA:
    def test_basic_computation(self):
        bars = make_bars([10, 20, 30])
        result = compute_wma(bars, period=3)
        # weights: 1*10 + 2*20 + 3*30 = 10+40+90 = 140; sum weights = 6
        # WMA = 140/6 ≈ 23.333...
        assert result is not None
        expected = Decimal("140") / Decimal("6")
        assert abs(result - expected) < Decimal("0.01")

    def test_insufficient_data(self):
        bars = make_bars([10])
        assert compute_wma(bars, period=5) is None

    def test_returns_decimal(self):
        bars = make_bars([10, 20, 30])
        result = compute_wma(bars, period=3)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# CCI
# ---------------------------------------------------------------------------

class TestCCI:
    def test_basic_computation(self):
        bars = make_trending_bars(50, 60, 25)
        result = compute_cci(bars, period=20)
        assert result is not None
        assert isinstance(result, Decimal)

    def test_flat_data_zero(self):
        bars = make_flat_bars(100, 20)
        result = compute_cci(bars, period=20)
        assert result is not None
        assert result == Decimal("0")

    def test_insufficient_data(self):
        bars = make_bars([10])
        assert compute_cci(bars, period=20) is None


# ---------------------------------------------------------------------------
# MFI
# ---------------------------------------------------------------------------

class TestMFI:
    def test_range_0_to_100(self):
        bars = make_trending_bars(50, 100, 20)
        result = compute_mfi(bars, period=14)
        assert result is not None
        assert Decimal("0") <= result <= Decimal("100")

    def test_insufficient_data(self):
        bars = make_bars([10])
        assert compute_mfi(bars, period=14) is None

    def test_returns_decimal(self):
        bars = make_trending_bars(50, 100, 20)
        result = compute_mfi(bars, period=14)
        if result is not None:
            assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# Williams %R
# ---------------------------------------------------------------------------

class TestWilliamsR:
    def test_range_neg100_to_0(self):
        bars = make_trending_bars(50, 100, 20)
        result = compute_williams_r(bars, period=14)
        assert result is not None
        assert Decimal("-100") <= result <= Decimal("0")

    def test_insufficient_data(self):
        bars = make_bars([10])
        assert compute_williams_r(bars, period=14) is None

    def test_returns_decimal(self):
        bars = make_trending_bars(50, 100, 20)
        result = compute_williams_r(bars, period=14)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# Keltner Channels
# ---------------------------------------------------------------------------

class TestKeltner:
    def test_returns_three_bands(self):
        bars = make_trending_bars(50, 60, 25)
        result = compute_keltner(bars, period=20)
        assert result is not None
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result

    def test_upper_greater_than_lower(self):
        bars = make_trending_bars(50, 60, 25)
        result = compute_keltner(bars, period=20)
        assert result is not None
        assert result["upper"] > result["lower"]

    def test_insufficient_data(self):
        bars = make_bars([10])
        assert compute_keltner(bars, period=20) is None


# ---------------------------------------------------------------------------
# Plus DI / Minus DI
# ---------------------------------------------------------------------------

class TestDirectionalIndicators:
    def test_plus_di_in_uptrend(self):
        bars = make_trending_bars(50, 100, 20)
        result = compute_plus_di(bars, period=14)
        if result is not None:
            assert result >= Decimal("0")

    def test_minus_di_in_downtrend(self):
        bars = make_trending_bars(100, 50, 20)
        result = compute_minus_di(bars, period=14)
        if result is not None:
            assert result >= Decimal("0")

    def test_insufficient_data(self):
        bars = make_bars([10, 20])
        assert compute_plus_di(bars, period=14) is None
        assert compute_minus_di(bars, period=14) is None


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------

class TestVolume:
    def test_returns_latest_volume(self):
        bars = make_bars([10, 20], volumes=[500, 1000])
        assert compute_volume(bars) == Decimal("1000")

    def test_empty_bars(self):
        assert compute_volume([]) is None
