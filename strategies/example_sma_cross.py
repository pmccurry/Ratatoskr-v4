"""
Example: SMA Crossover Strategy
================================
Simple moving average crossover on forex pairs.
This is an example showing how to write a Python strategy.
"""
from app.strategy_sdk.base import Strategy


class SMACrossover(Strategy):
    name = "SMA Crossover Example"
    description = "Enters on SMA(20) crossing above/below SMA(50)"
    symbols = ["EUR_USD"]
    timeframe = "1h"
    market = "forex"

    # Configurable parameters
    fast_period = 20
    slow_period = 50

    @classmethod
    def get_parameters(cls):
        return {
            "fast_period": {"type": "int", "default": 20, "min": 5, "max": 100, "label": "Fast SMA Period"},
            "slow_period": {"type": "int", "default": 50, "min": 10, "max": 500, "label": "Slow SMA Period"},
        }

    def on_start(self):
        self.set_state("last_signal", None)

    def on_bar(self, symbol, bar, history):
        if len(history) < self.slow_period + 1:
            return []

        sma_fast = self.indicators.sma_series(history, self.fast_period)
        sma_slow = self.indicators.sma_series(history, self.slow_period)

        signals = []

        # Long signal: fast crosses above slow
        if self.indicators.crosses_above(sma_fast, sma_slow):
            if not self.has_position(symbol, "long"):
                # Close any short position first
                # (handled by signal_exit logic in the pipeline)
                entry = bar["close"]
                sl = entry - self.pips.from_pips(50, symbol)
                tp = entry + self.pips.from_pips(75, symbol)
                signals.append(self.signal(symbol, "long", entry,
                                          stop_loss=sl, take_profit=tp))
                self.set_state("last_signal", "long")

        # Short signal: fast crosses below slow
        elif self.indicators.crosses_below(sma_fast, sma_slow):
            if not self.has_position(symbol, "short"):
                entry = bar["close"]
                sl = entry + self.pips.from_pips(50, symbol)
                tp = entry - self.pips.from_pips(75, symbol)
                signals.append(self.signal(symbol, "short", entry,
                                          stop_loss=sl, take_profit=tp))
                self.set_state("last_signal", "short")

        return signals
