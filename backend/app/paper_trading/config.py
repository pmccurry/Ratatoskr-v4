"""Paper trading module configuration."""

from decimal import Decimal

from app.common.config import get_settings


class PaperTradingConfig:
    def __init__(self):
        s = get_settings()
        # Execution modes
        self.execution_mode_equities = s.paper_trading_execution_mode_equities
        self.execution_mode_forex = s.paper_trading_execution_mode_forex
        self.broker_fallback = s.paper_trading_broker_fallback
        # Slippage
        self.slippage_bps_equities = Decimal(str(s.paper_trading_slippage_bps_equities))
        self.slippage_bps_forex = Decimal(str(s.paper_trading_slippage_bps_forex))
        self.slippage_bps_options = Decimal(str(s.paper_trading_slippage_bps_options))
        # Fees
        self.fee_per_trade_equities = Decimal(str(s.paper_trading_fee_per_trade_equities))
        self.fee_spread_bps_forex = Decimal(str(s.paper_trading_fee_spread_bps_forex))
        self.fee_per_trade_options = Decimal(str(s.paper_trading_fee_per_trade_options))
        # Options
        self.default_contract_multiplier = s.paper_trading_default_contract_multiplier
        # Cash
        self.initial_cash = Decimal(str(s.paper_trading_initial_cash))
        # Forex pool (used by TASK-012b)
        self.forex_account_pool_size = s.paper_trading_forex_account_pool_size
        self.forex_capital_per_account = Decimal(str(s.paper_trading_forex_capital_per_account))
