"""Strategy module configuration."""

from app.common.config import get_settings


class StrategyConfig:
    """Strategy module configuration.

    Extracts strategy-specific settings from the global Settings object.
    """

    def __init__(self):
        s = get_settings()
        self.runner_check_interval = s.strategy_runner_check_interval_sec
        self.auto_pause_error_threshold = s.strategy_auto_pause_error_threshold
        self.evaluation_timeout = s.strategy_evaluation_timeout_sec
        self.max_concurrent_evaluations = s.strategy_max_concurrent_evaluations
        self.safety_monitor_check_interval = s.safety_monitor_check_interval_sec
        self.safety_monitor_failure_alert_threshold = s.safety_monitor_failure_alert_threshold
        self.global_kill_switch = s.safety_monitor_global_kill_switch


def get_strategy_config() -> StrategyConfig:
    """Create and return a StrategyConfig instance."""
    return StrategyConfig()
