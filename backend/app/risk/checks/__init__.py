"""Risk checks registry — ordered list of all checks."""

from app.risk.checks.base import RiskCheck
from app.risk.checks.daily_loss import DailyLossCheck
from app.risk.checks.drawdown import DrawdownCheck
from app.risk.checks.duplicate import DuplicateOrderCheck
from app.risk.checks.exposure import (
    PortfolioExposureCheck,
    StrategyExposureCheck,
    SymbolExposureCheck,
)
from app.risk.checks.kill_switch import KillSwitchCheck
from app.risk.checks.position_limit import PositionLimitCheck
from app.risk.checks.position_sizing import PositionSizingCheck
from app.risk.checks.strategy_enable import StrategyEnableCheck
from app.risk.checks.symbol import MarketHoursCheck, SymbolTradabilityCheck


def get_risk_checks() -> list[RiskCheck]:
    """Return all risk checks in evaluation order."""
    return [
        KillSwitchCheck(),          # 1. Global kill switch
        StrategyEnableCheck(),      # 2. Strategy-level enable
        SymbolTradabilityCheck(),   # 3. Symbol tradability
        MarketHoursCheck(),         # 4. Market hours
        DuplicateOrderCheck(),      # 5. Duplicate order guard
        PositionLimitCheck(),       # 6. Position limit
        PositionSizingCheck(),      # 7. Position sizing
        SymbolExposureCheck(),      # 8. Per-symbol exposure
        StrategyExposureCheck(),    # 9. Per-strategy exposure
        PortfolioExposureCheck(),   # 10. Portfolio-level exposure
        DrawdownCheck(),            # 11. Drawdown
        DailyLossCheck(),           # 12. Daily loss limit
    ]
