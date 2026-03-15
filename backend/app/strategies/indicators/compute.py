"""Indicator computation functions — pure, stateless, Decimal-based.

All functions take bar data (list of dicts/objects with open, high, low,
close, volume as Decimal) and return computed values. List is ordered
chronologically (oldest first, newest last).

Functions return None when there are insufficient bars. They never raise
exceptions on bad data.
"""

from decimal import Decimal, InvalidOperation


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_source_value(bar, source: str = "close") -> Decimal:
    """Extract a price source from a bar.

    source: "close" | "open" | "high" | "low" | "hl2" | "hlc3" | "ohlc4"
    """
    try:
        if source == "close":
            return Decimal(str(bar["close"] if isinstance(bar, dict) else bar.close))
        if source == "open":
            return Decimal(str(bar["open"] if isinstance(bar, dict) else bar.open))
        if source == "high":
            return Decimal(str(bar["high"] if isinstance(bar, dict) else bar.high))
        if source == "low":
            return Decimal(str(bar["low"] if isinstance(bar, dict) else bar.low))

        h = Decimal(str(bar["high"] if isinstance(bar, dict) else bar.high))
        l = Decimal(str(bar["low"] if isinstance(bar, dict) else bar.low))
        c = Decimal(str(bar["close"] if isinstance(bar, dict) else bar.close))
        o = Decimal(str(bar["open"] if isinstance(bar, dict) else bar.open))

        if source == "hl2":
            return (h + l) / Decimal("2")
        if source == "hlc3":
            return (h + l + c) / Decimal("3")
        if source == "ohlc4":
            return (o + h + l + c) / Decimal("4")

        return Decimal(str(bar["close"] if isinstance(bar, dict) else bar.close))
    except (KeyError, AttributeError, TypeError, InvalidOperation):
        return Decimal("0")


def _get_field(bar, field: str) -> Decimal:
    """Safely extract a Decimal field from a bar."""
    try:
        val = bar[field] if isinstance(bar, dict) else getattr(bar, field)
        return Decimal(str(val))
    except (KeyError, AttributeError, TypeError, InvalidOperation):
        return Decimal("0")


def _extract_series(bars: list, source: str = "close") -> list[Decimal]:
    """Extract a series of source values from bars."""
    return [get_source_value(b, source) for b in bars]


# ---------------------------------------------------------------------------
# Trend (4)
# ---------------------------------------------------------------------------

def compute_sma(bars: list, period: int = 20, source: str = "close") -> Decimal | None:
    """Simple Moving Average. Requires >= period bars."""
    if len(bars) < period:
        return None
    try:
        values = _extract_series(bars[-period:], source)
        return sum(values) / Decimal(str(period))
    except Exception:
        return None


def compute_ema(bars: list, period: int = 20, source: str = "close") -> Decimal | None:
    """Exponential Moving Average.

    Multiplier = 2 / (period + 1)
    EMA = (value - prev_ema) * multiplier + prev_ema
    Requires >= period bars (uses SMA of first `period` bars as seed).
    """
    if len(bars) < period:
        return None
    try:
        values = _extract_series(bars, source)
        multiplier = Decimal("2") / Decimal(str(period + 1))

        # Seed with SMA of first `period` values
        ema = sum(values[:period]) / Decimal(str(period))

        for val in values[period:]:
            ema = (val - ema) * multiplier + ema

        return ema
    except Exception:
        return None


def compute_wma(bars: list, period: int = 20, source: str = "close") -> Decimal | None:
    """Weighted Moving Average.

    Weight = position (1 for oldest, period for newest).
    WMA = sum(weight * value) / sum(weights)
    Requires >= period bars.
    """
    if len(bars) < period:
        return None
    try:
        values = _extract_series(bars[-period:], source)
        weight_sum = Decimal("0")
        weighted_sum = Decimal("0")
        for i, val in enumerate(values, start=1):
            w = Decimal(str(i))
            weighted_sum += w * val
            weight_sum += w
        if weight_sum == 0:
            return None
        return weighted_sum / weight_sum
    except Exception:
        return None


def compute_vwap(bars: list) -> Decimal | None:
    """Volume Weighted Average Price.

    VWAP = sum(typical_price * volume) / sum(volume)
    typical_price = (high + low + close) / 3
    Requires >= 1 bar.
    """
    if not bars:
        return None
    try:
        tp_vol_sum = Decimal("0")
        vol_sum = Decimal("0")
        for b in bars:
            h = _get_field(b, "high")
            l = _get_field(b, "low")
            c = _get_field(b, "close")
            v = _get_field(b, "volume")
            tp = (h + l + c) / Decimal("3")
            tp_vol_sum += tp * v
            vol_sum += v
        if vol_sum == 0:
            return None
        return tp_vol_sum / vol_sum
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Momentum (6)
# ---------------------------------------------------------------------------

def compute_rsi(bars: list, period: int = 14, source: str = "close") -> Decimal | None:
    """Relative Strength Index with Wilder's smoothing.

    Requires >= period + 1 bars.
    """
    if len(bars) < period + 1:
        return None
    try:
        values = _extract_series(bars, source)
        changes = [values[i] - values[i - 1] for i in range(1, len(values))]

        # Initial average gain/loss (SMA of first period changes)
        gains = [c if c > 0 else Decimal("0") for c in changes[:period]]
        losses = [abs(c) if c < 0 else Decimal("0") for c in changes[:period]]
        avg_gain = sum(gains) / Decimal(str(period))
        avg_loss = sum(losses) / Decimal(str(period))

        # Wilder's smoothing for remaining
        p = Decimal(str(period))
        for c in changes[period:]:
            if c > 0:
                avg_gain = (avg_gain * (p - 1) + c) / p
                avg_loss = (avg_loss * (p - 1)) / p
            else:
                avg_gain = (avg_gain * (p - 1)) / p
                avg_loss = (avg_loss * (p - 1) + abs(c)) / p

        if avg_loss == 0:
            return Decimal("100")

        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))
        return rsi
    except Exception:
        return None


def compute_macd(
    bars: list, fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, Decimal] | None:
    """MACD. Returns {"macd_line", "signal_line", "histogram"}.

    Requires >= slow + signal - 1 bars.
    """
    required = slow + signal - 1
    if len(bars) < required:
        return None
    try:
        values = _extract_series(bars, "close")

        def _ema_series(data: list[Decimal], period: int) -> list[Decimal]:
            mult = Decimal("2") / Decimal(str(period + 1))
            ema_val = sum(data[:period]) / Decimal(str(period))
            result = [ema_val]
            for val in data[period:]:
                ema_val = (val - ema_val) * mult + ema_val
                result.append(ema_val)
            return result

        fast_emas = _ema_series(values, fast)
        slow_emas = _ema_series(values, slow)

        # Align: fast_emas starts at index fast-1, slow_emas starts at slow-1
        # We need to align them from the slow start point
        offset = slow - fast
        macd_series = [
            fast_emas[offset + i] - slow_emas[i]
            for i in range(len(slow_emas))
        ]

        if len(macd_series) < signal:
            return None

        signal_emas = _ema_series(macd_series, signal)

        macd_line = macd_series[-1]
        signal_line = signal_emas[-1]
        histogram = macd_line - signal_line

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
        }
    except Exception:
        return None


def compute_stochastic(
    bars: list, k_period: int = 14, d_period: int = 3, slowing: int = 3
) -> dict[str, Decimal] | None:
    """Stochastic Oscillator. Returns {"k", "d"}.

    Requires >= k_period + slowing + d_period - 2 bars.
    """
    required = k_period + slowing + d_period - 2
    if len(bars) < required:
        return None
    try:
        # Compute raw %K series
        raw_k_series = []
        for i in range(k_period - 1, len(bars)):
            window = bars[i - k_period + 1 : i + 1]
            highest = max(_get_field(b, "high") for b in window)
            lowest = min(_get_field(b, "low") for b in window)
            close = _get_field(bars[i], "close")
            if highest == lowest:
                raw_k_series.append(Decimal("50"))
            else:
                raw_k_series.append(
                    (close - lowest) / (highest - lowest) * Decimal("100")
                )

        if len(raw_k_series) < slowing:
            return None

        # %K = SMA(slowing) of raw_k
        k_series = []
        for i in range(slowing - 1, len(raw_k_series)):
            window = raw_k_series[i - slowing + 1 : i + 1]
            k_series.append(sum(window) / Decimal(str(slowing)))

        if len(k_series) < d_period:
            return None

        # %D = SMA(d_period) of %K
        d_window = k_series[-d_period:]
        d_value = sum(d_window) / Decimal(str(d_period))

        return {"k": k_series[-1], "d": d_value}
    except Exception:
        return None


def compute_cci(bars: list, period: int = 20) -> Decimal | None:
    """Commodity Channel Index.

    CCI = (tp - SMA(tp)) / (0.015 * mean_deviation)
    Requires >= period bars.
    """
    if len(bars) < period:
        return None
    try:
        window = bars[-period:]
        tps = [
            (_get_field(b, "high") + _get_field(b, "low") + _get_field(b, "close"))
            / Decimal("3")
            for b in window
        ]
        sma_tp = sum(tps) / Decimal(str(period))
        mean_dev = sum(abs(tp - sma_tp) for tp in tps) / Decimal(str(period))

        if mean_dev == 0:
            return Decimal("0")

        return (tps[-1] - sma_tp) / (Decimal("0.015") * mean_dev)
    except Exception:
        return None


def compute_mfi(bars: list, period: int = 14) -> Decimal | None:
    """Money Flow Index.

    Requires >= period + 1 bars.
    """
    if len(bars) < period + 1:
        return None
    try:
        window = bars[-(period + 1) :]
        pos_flow = Decimal("0")
        neg_flow = Decimal("0")

        for i in range(1, len(window)):
            tp = (
                _get_field(window[i], "high")
                + _get_field(window[i], "low")
                + _get_field(window[i], "close")
            ) / Decimal("3")
            prev_tp = (
                _get_field(window[i - 1], "high")
                + _get_field(window[i - 1], "low")
                + _get_field(window[i - 1], "close")
            ) / Decimal("3")
            raw_mf = tp * _get_field(window[i], "volume")

            if tp > prev_tp:
                pos_flow += raw_mf
            elif tp < prev_tp:
                neg_flow += raw_mf

        if neg_flow == 0:
            return Decimal("100")

        mf_ratio = pos_flow / neg_flow
        return Decimal("100") - (Decimal("100") / (Decimal("1") + mf_ratio))
    except Exception:
        return None


def compute_williams_r(bars: list, period: int = 14) -> Decimal | None:
    """Williams %R.

    %R = (highest_high - close) / (highest_high - lowest_low) * -100
    Requires >= period bars.
    """
    if len(bars) < period:
        return None
    try:
        window = bars[-period:]
        highest = max(_get_field(b, "high") for b in window)
        lowest = min(_get_field(b, "low") for b in window)
        close = _get_field(window[-1], "close")

        if highest == lowest:
            return Decimal("0")

        return (highest - close) / (highest - lowest) * Decimal("-100")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Volatility (3)
# ---------------------------------------------------------------------------

def compute_bbands(
    bars: list, period: int = 20, std_dev: float = 2.0
) -> dict[str, Decimal] | None:
    """Bollinger Bands. Returns {"upper", "middle", "lower"}.

    Requires >= period bars.
    """
    if len(bars) < period:
        return None
    try:
        values = _extract_series(bars[-period:], "close")
        middle = sum(values) / Decimal(str(period))

        # Standard deviation
        variance = sum((v - middle) ** 2 for v in values) / Decimal(str(period))
        std = variance.sqrt()
        sd = Decimal(str(std_dev))

        return {
            "upper": middle + sd * std,
            "middle": middle,
            "lower": middle - sd * std,
        }
    except Exception:
        return None


def compute_atr(bars: list, period: int = 14) -> Decimal | None:
    """Average True Range with Wilder's smoothing.

    Requires >= period + 1 bars.
    """
    if len(bars) < period + 1:
        return None
    try:
        true_ranges = []
        for i in range(1, len(bars)):
            h = _get_field(bars[i], "high")
            l = _get_field(bars[i], "low")
            pc = _get_field(bars[i - 1], "close")
            tr = max(h - l, abs(h - pc), abs(l - pc))
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return None

        # Initial ATR = SMA of first period TRs
        atr = sum(true_ranges[:period]) / Decimal(str(period))

        # Wilder's smoothing
        p = Decimal(str(period))
        for tr in true_ranges[period:]:
            atr = (atr * (p - 1) + tr) / p

        return atr
    except Exception:
        return None


def compute_keltner(
    bars: list, period: int = 20, atr_multiplier: float = 1.5
) -> dict[str, Decimal] | None:
    """Keltner Channels. Returns {"upper", "middle", "lower"}.

    middle = EMA(period), bands = middle +/- atr_multiplier * ATR(period)
    Requires >= period + 1 bars.
    """
    if len(bars) < period + 1:
        return None
    try:
        middle = compute_ema(bars, period, "close")
        atr = compute_atr(bars, period)
        if middle is None or atr is None:
            return None
        mult = Decimal(str(atr_multiplier))
        return {
            "upper": middle + mult * atr,
            "middle": middle,
            "lower": middle - mult * atr,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Volume (3)
# ---------------------------------------------------------------------------

def compute_volume(bars: list) -> Decimal | None:
    """Raw bar volume. Returns latest bar's volume. Requires >= 1 bar."""
    if not bars:
        return None
    try:
        return _get_field(bars[-1], "volume")
    except Exception:
        return None


def compute_volume_sma(bars: list, period: int = 20) -> Decimal | None:
    """SMA of volume. Requires >= period bars."""
    if len(bars) < period:
        return None
    try:
        volumes = [_get_field(b, "volume") for b in bars[-period:]]
        return sum(volumes) / Decimal(str(period))
    except Exception:
        return None


def compute_obv(bars: list) -> Decimal | None:
    """On Balance Volume. Requires >= 2 bars."""
    if len(bars) < 2:
        return None
    try:
        obv = Decimal("0")
        for i in range(1, len(bars)):
            c = _get_field(bars[i], "close")
            pc = _get_field(bars[i - 1], "close")
            v = _get_field(bars[i], "volume")
            if c > pc:
                obv += v
            elif c < pc:
                obv -= v
        return obv
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Trend Strength (3)
# ---------------------------------------------------------------------------

def _compute_directional_movement(bars: list, period: int = 14) -> tuple | None:
    """Shared computation for ADX, +DI, -DI.

    Returns (plus_di, minus_di, adx) or None if insufficient data.
    Requires >= 2 * period + 1 bars for ADX smoothing.
    """
    if len(bars) < period + 1:
        return None
    try:
        p = Decimal(str(period))

        # Compute +DM, -DM, and TR series
        plus_dm_list = []
        minus_dm_list = []
        tr_list = []
        for i in range(1, len(bars)):
            h = _get_field(bars[i], "high")
            l = _get_field(bars[i], "low")
            ph = _get_field(bars[i - 1], "high")
            pl = _get_field(bars[i - 1], "low")
            pc = _get_field(bars[i - 1], "close")

            up_move = h - ph
            down_move = pl - l

            plus_dm = up_move if up_move > down_move and up_move > 0 else Decimal("0")
            minus_dm = down_move if down_move > up_move and down_move > 0 else Decimal("0")

            tr = max(h - l, abs(h - pc), abs(l - pc))

            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
            tr_list.append(tr)

        if len(tr_list) < period:
            return None

        # Wilder's smoothing for initial period
        smoothed_plus_dm = sum(plus_dm_list[:period])
        smoothed_minus_dm = sum(minus_dm_list[:period])
        smoothed_tr = sum(tr_list[:period])

        # Continue smoothing
        dx_list = []
        plus_di = None
        minus_di = None

        for i in range(period, len(tr_list)):
            smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / p) + plus_dm_list[i]
            smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / p) + minus_dm_list[i]
            smoothed_tr = smoothed_tr - (smoothed_tr / p) + tr_list[i]

            if smoothed_tr == 0:
                plus_di = Decimal("0")
                minus_di = Decimal("0")
            else:
                plus_di = (smoothed_plus_dm / smoothed_tr) * Decimal("100")
                minus_di = (smoothed_minus_dm / smoothed_tr) * Decimal("100")

            di_sum = plus_di + minus_di
            if di_sum == 0:
                dx_list.append(Decimal("0"))
            else:
                dx_list.append(abs(plus_di - minus_di) / di_sum * Decimal("100"))

        # Also compute for the initial period point
        if smoothed_tr == sum(tr_list[:period]) and smoothed_tr != 0:
            plus_di = (sum(plus_dm_list[:period]) / smoothed_tr) * Decimal("100")
            minus_di = (sum(minus_dm_list[:period]) / smoothed_tr) * Decimal("100")

        if not dx_list:
            return (plus_di, minus_di, None) if plus_di is not None else None

        # ADX = Wilder's smoothing of DX
        if len(dx_list) < period:
            adx = sum(dx_list) / Decimal(str(len(dx_list)))
        else:
            adx = sum(dx_list[:period]) / p
            for dx in dx_list[period:]:
                adx = (adx * (p - 1) + dx) / p

        return (plus_di, minus_di, adx)
    except Exception:
        return None


def compute_adx(bars: list, period: int = 14) -> Decimal | None:
    """Average Directional Index. Requires >= 2 * period + 1 bars."""
    result = _compute_directional_movement(bars, period)
    if result is None:
        return None
    return result[2]


def compute_plus_di(bars: list, period: int = 14) -> Decimal | None:
    """Plus Directional Indicator (+DI). Requires >= period + 1 bars."""
    result = _compute_directional_movement(bars, period)
    if result is None:
        return None
    return result[0]


def compute_minus_di(bars: list, period: int = 14) -> Decimal | None:
    """Minus Directional Indicator (-DI). Requires >= period + 1 bars."""
    result = _compute_directional_movement(bars, period)
    if result is None:
        return None
    return result[1]


# ---------------------------------------------------------------------------
# Price Reference (7)
# ---------------------------------------------------------------------------

def compute_close(bars: list) -> Decimal | None:
    """Latest close price. Requires >= 1 bar."""
    if not bars:
        return None
    return _get_field(bars[-1], "close")


def compute_open(bars: list) -> Decimal | None:
    """Latest open price. Requires >= 1 bar."""
    if not bars:
        return None
    return _get_field(bars[-1], "open")


def compute_high(bars: list) -> Decimal | None:
    """Latest high price. Requires >= 1 bar."""
    if not bars:
        return None
    return _get_field(bars[-1], "high")


def compute_low(bars: list) -> Decimal | None:
    """Latest low price. Requires >= 1 bar."""
    if not bars:
        return None
    return _get_field(bars[-1], "low")


def compute_prev_close(bars: list) -> Decimal | None:
    """Previous bar's close price. Requires >= 2 bars."""
    if len(bars) < 2:
        return None
    return _get_field(bars[-2], "close")


def compute_prev_high(bars: list) -> Decimal | None:
    """Previous bar's high price. Requires >= 2 bars."""
    if len(bars) < 2:
        return None
    return _get_field(bars[-2], "high")


def compute_prev_low(bars: list) -> Decimal | None:
    """Previous bar's low price. Requires >= 2 bars."""
    if len(bars) < 2:
        return None
    return _get_field(bars[-2], "low")
