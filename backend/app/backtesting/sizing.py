from decimal import Decimal


def calculate_position_size(config: dict, equity: Decimal, price: Decimal, symbol: str = "") -> Decimal:
    """Calculate position size based on sizing config.

    Config types:
    - fixed: {"type": "fixed", "amount": 10000} -- fixed number of units
    - fixed_cash: {"type": "fixed_cash", "amount": 5000} -- buy $X worth
    - percent_equity: {"type": "percent_equity", "percent": 2} -- X% of equity
    - percent_risk: {"type": "percent_risk", "percent": 1, "stop_pips": 50}
    """
    sizing_type = config.get("type", "fixed")

    if sizing_type == "fixed":
        return Decimal(str(config.get("amount", 10000)))

    elif sizing_type == "fixed_cash":
        cash_amount = Decimal(str(config.get("amount", 5000)))
        if price <= 0:
            return Decimal("0")
        return (cash_amount / price).quantize(Decimal("0.01"))

    elif sizing_type == "percent_equity":
        pct = Decimal(str(config.get("percent", 2)))
        cash_amount = equity * pct / Decimal("100")
        if price <= 0:
            return Decimal("0")
        return (cash_amount / price).quantize(Decimal("0.01"))

    elif sizing_type == "percent_risk":
        pct = Decimal(str(config.get("percent", 1)))
        risk_amount = equity * pct / Decimal("100")
        stop_pips = Decimal(str(config.get("stop_pips", 50)))
        pip_value = _get_pip_value(symbol)
        if stop_pips <= 0 or pip_value <= 0:
            return Decimal("0")
        return (risk_amount / (stop_pips * pip_value)).quantize(Decimal("0.01"))

    return Decimal("0")


def _get_pip_value(symbol: str) -> Decimal:
    """Get pip value for a symbol. JPY pairs use 0.01, others 0.0001."""
    if "JPY" in symbol.upper():
        return Decimal("0.01")
    return Decimal("0.0001")
