"""Risk module configuration."""

from decimal import Decimal

from app.common.config import get_settings


class RiskModuleConfig:
    """Risk module startup configuration from environment variables.

    These are defaults — the actual risk limits are stored in the
    RiskConfig database table and may differ from these values.
    """

    def __init__(self):
        s = get_settings()
        self.default_max_position_size_percent = Decimal(str(s.risk_default_max_position_size_percent))
        self.default_max_symbol_exposure_percent = Decimal(str(s.risk_default_max_symbol_exposure_percent))
        self.default_max_strategy_exposure_percent = Decimal(str(s.risk_default_max_strategy_exposure_percent))
        self.default_max_total_exposure_percent = Decimal(str(s.risk_default_max_total_exposure_percent))
        self.default_max_drawdown_percent = Decimal(str(s.risk_default_max_drawdown_percent))
        self.default_max_drawdown_catastrophic_percent = Decimal(str(s.risk_default_max_drawdown_catastrophic_percent))
        self.default_max_daily_loss_percent = Decimal(str(s.risk_default_max_daily_loss_percent))
        self.default_min_position_value = Decimal(str(s.risk_default_min_position_value))
        self.evaluation_timeout = s.risk_evaluation_timeout_sec


def get_risk_module_config() -> RiskModuleConfig:
    """Create and return a RiskModuleConfig instance."""
    return RiskModuleConfig()
