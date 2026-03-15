"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === Environment ===
    environment: str = "development"

    # === CORS ===
    cors_allowed_origins: str = ""

    # === Database ===
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30

    # === Auth ===
    auth_jwt_secret_key: str
    auth_jwt_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 15
    auth_refresh_token_expire_days: int = 7
    auth_bcrypt_cost_factor: int = 12
    auth_min_password_length: int = 12
    auth_max_failed_attempts: int = 5
    auth_lockout_duration_minutes: int = 15

    # === Rate Limiting ===
    auth_login_rate_limit: int = 5
    auth_login_rate_window_sec: int = 60
    auth_refresh_rate_limit: int = 10
    auth_refresh_rate_window_sec: int = 60
    auth_password_change_rate_limit: int = 3
    auth_password_change_rate_window_sec: int = 60

    # === Broker Credentials ===
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_ws_url: str = "wss://stream.data.alpaca.markets/v2/sip"
    oanda_access_token: str = ""
    oanda_account_id: str = ""
    oanda_base_url: str = "https://api-fxpractice.oanda.com"
    oanda_stream_url: str = "https://stream-fxpractice.oanda.com"

    # === Universe Filter ===
    universe_filter_equities_min_volume: int = 500000
    universe_filter_equities_min_price: float = 5.00
    universe_filter_equities_exchanges: str = "NYSE,NASDAQ,AMEX"
    universe_filter_equities_schedule: str = "0 9 * * 1-5"
    universe_filter_forex_pairs: str = "EUR_USD,GBP_USD,USD_JPY,USD_CHF,AUD_USD,USD_CAD,NZD_USD,EUR_GBP,EUR_JPY,GBP_JPY"

    # === WebSocket ===
    ws_reconnect_initial_delay_sec: int = 1
    ws_reconnect_max_delay_sec: int = 60
    ws_reconnect_backoff_multiplier: int = 2
    ws_heartbeat_interval_sec: int = 60
    ws_stale_data_threshold_sec: int = 120
    ws_bar_queue_max_size: int = 10000

    # === Bar Storage ===
    bar_batch_write_size: int = 100
    bar_batch_write_interval_sec: int = 3

    # === Backfill ===
    backfill_1m_days: int = 30
    backfill_1h_days: int = 365
    backfill_4h_days: int = 365
    backfill_1d_days: int = 730
    backfill_rate_limit_buffer_percent: int = 10
    backfill_max_retries: int = 3
    backfill_retry_delay_sec: int = 30

    # === Options ===
    option_cache_ttl_sec: int = 60

    # === Market Data Health ===
    market_data_stale_threshold_sec: int = 120
    market_data_stale_check_interval_sec: int = 60
    market_data_queue_warn_percent: int = 20
    market_data_queue_critical_percent: int = 80
    market_data_health_check_interval_sec: int = 30

    # === Corporate Actions ===
    corporate_actions_fetch_schedule: str = "0 8 * * 1-5"
    corporate_actions_lookforward_days: int = 30

    # === Strategy Runner ===
    strategy_runner_check_interval_sec: int = 60
    strategy_auto_pause_error_threshold: int = 5
    strategy_evaluation_timeout_sec: int = 30
    strategy_max_concurrent_evaluations: int = 20

    # === Safety Monitor ===
    safety_monitor_check_interval_sec: int = 60
    safety_monitor_failure_alert_threshold: int = 3
    safety_monitor_global_kill_switch: bool = False

    # === Signals ===
    signal_dedup_window_bars: int = 1
    signal_expiry_seconds: int = 300
    signal_expiry_check_interval_sec: int = 60

    # === Risk (defaults, overridden by DB config) ===
    risk_default_max_position_size_percent: float = 10.0
    risk_default_max_symbol_exposure_percent: float = 20.0
    risk_default_max_strategy_exposure_percent: float = 30.0
    risk_default_max_total_exposure_percent: float = 80.0
    risk_default_max_drawdown_percent: float = 10.0
    risk_default_max_drawdown_catastrophic_percent: float = 20.0
    risk_default_max_daily_loss_percent: float = 3.0
    risk_default_min_position_value: float = 100.0
    risk_evaluation_timeout_sec: int = 5

    # === Paper Trading ===
    paper_trading_execution_mode_equities: str = "paper"
    paper_trading_execution_mode_forex: str = "simulation"
    paper_trading_broker_fallback: str = "simulation"
    paper_trading_slippage_bps_equities: int = 5
    paper_trading_slippage_bps_forex: int = 2
    paper_trading_slippage_bps_options: int = 10
    paper_trading_fee_per_trade_equities: float = 0.00
    paper_trading_fee_spread_bps_forex: int = 15
    paper_trading_fee_per_trade_options: float = 0.00
    paper_trading_default_contract_multiplier: int = 100
    paper_trading_initial_cash: float = 100000.00
    paper_trading_forex_account_pool_size: int = 4
    paper_trading_forex_capital_per_account: float = 25000.00
    forex_account_allocation_priority: str = "first_come"

    # === Forex Account Pool — Real Account Mapping ===
    oanda_pool_account_1: str = ""
    oanda_pool_account_2: str = ""
    oanda_pool_account_3: str = ""
    oanda_pool_account_4: str = ""
    oanda_pool_token_1: str = ""
    oanda_pool_token_2: str = ""
    oanda_pool_token_3: str = ""
    oanda_pool_token_4: str = ""

    # === Shadow Tracking ===
    shadow_tracking_enabled: bool = True
    shadow_tracking_forex_only: bool = True

    # === Portfolio ===
    portfolio_mark_to_market_interval_sec: int = 60
    portfolio_snapshot_interval_sec: int = 300
    portfolio_risk_free_rate: float = 0.05

    # === Observability ===
    event_queue_max_size: int = 50000
    event_batch_write_size: int = 100
    event_batch_write_interval_sec: int = 5
    event_retention_days: int = 365
    metrics_collection_interval_sec: int = 60
    metrics_retention_days: int = 90
    alert_evaluation_interval_sec: int = 30
    alert_email_enabled: bool = False
    alert_email_recipients: str = ""
    alert_email_min_severity: str = "error"
    alert_webhook_enabled: bool = False
    alert_webhook_url: str = ""
    alert_webhook_min_severity: str = "error"

    # === Admin Seed ===
    admin_seed_password: str = ""

    # === Logging ===
    log_level: str = "INFO"
    log_format: str = "json"

    # === Request Limits ===
    max_request_body_size: int = 1_048_576  # 1MB

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance. Loaded once at startup."""
    return Settings()


async def get_settings_dep() -> Settings:
    """FastAPI dependency for injecting settings."""
    return get_settings()
