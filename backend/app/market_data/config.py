"""Market data module configuration."""

from app.common.config import get_settings


class MarketDataConfig:
    """Market data module configuration.

    Extracts market-data-specific settings from the global Settings object.
    """

    def __init__(self):
        s = get_settings()
        # Broker credentials
        self.alpaca_api_key = s.alpaca_api_key
        self.alpaca_api_secret = s.alpaca_api_secret
        self.alpaca_base_url = s.alpaca_base_url
        self.alpaca_data_ws_url = s.alpaca_data_ws_url
        self.oanda_access_token = s.oanda_access_token
        self.oanda_account_id = s.oanda_account_id
        self.oanda_base_url = s.oanda_base_url
        self.oanda_stream_url = s.oanda_stream_url
        # Universe filter
        self.equities_min_volume = s.universe_filter_equities_min_volume
        self.equities_min_price = s.universe_filter_equities_min_price
        self.equities_exchanges = s.universe_filter_equities_exchanges
        # WebSocket
        self.ws_reconnect_initial_delay = s.ws_reconnect_initial_delay_sec
        self.ws_reconnect_max_delay = s.ws_reconnect_max_delay_sec
        self.ws_reconnect_backoff_multiplier = s.ws_reconnect_backoff_multiplier
        self.ws_heartbeat_interval = s.ws_heartbeat_interval_sec
        self.ws_stale_threshold = s.ws_stale_data_threshold_sec
        self.ws_bar_queue_max_size = s.ws_bar_queue_max_size
        # Bar storage
        self.bar_batch_write_size = s.bar_batch_write_size
        self.bar_batch_write_interval = s.bar_batch_write_interval_sec
        # Backfill
        self.backfill_1m_days = s.backfill_1m_days
        self.backfill_1h_days = s.backfill_1h_days
        self.backfill_4h_days = s.backfill_4h_days
        self.backfill_1d_days = s.backfill_1d_days
        self.backfill_rate_limit_buffer = s.backfill_rate_limit_buffer_percent
        self.backfill_max_retries = s.backfill_max_retries
        self.backfill_retry_delay = s.backfill_retry_delay_sec
        # Options
        self.option_cache_ttl = s.option_cache_ttl_sec
        # Health
        self.stale_threshold = s.market_data_stale_threshold_sec
        self.stale_check_interval = s.market_data_stale_check_interval_sec
        self.queue_warn_percent = s.market_data_queue_warn_percent
        self.queue_critical_percent = s.market_data_queue_critical_percent
        self.health_check_interval = s.market_data_health_check_interval_sec
        # Corporate actions
        self.corporate_actions_lookforward_days = s.corporate_actions_lookforward_days


def get_market_data_config() -> MarketDataConfig:
    """Create and return a MarketDataConfig instance."""
    return MarketDataConfig()
