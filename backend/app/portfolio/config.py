"""Portfolio module configuration."""

from decimal import Decimal

from app.common.config import get_settings


class PortfolioConfig:
    def __init__(self):
        s = get_settings()
        self.mark_to_market_interval = s.portfolio_mark_to_market_interval_sec
        self.snapshot_interval = s.portfolio_snapshot_interval_sec
        self.risk_free_rate = Decimal(str(s.portfolio_risk_free_rate))
        self.initial_cash = Decimal(str(s.paper_trading_initial_cash))
        self.forex_pool_size = s.paper_trading_forex_account_pool_size
        self.forex_capital_per_account = Decimal(str(s.paper_trading_forex_capital_per_account))
