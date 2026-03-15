"""Risk check base class and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID


class CheckOutcome(Enum):
    PASS = "pass"
    REJECT = "reject"
    MODIFY = "modify"


@dataclass
class CheckResult:
    outcome: CheckOutcome
    reason_code: str = ""
    reason_text: str = ""
    modifications: dict | None = None


@dataclass
class RiskContext:
    """Shared context for risk evaluation. Loaded once, used by all checks."""

    risk_config: object  # RiskConfig model
    strategy: object  # Strategy model
    strategy_config: dict
    portfolio_equity: Decimal
    portfolio_cash: Decimal
    peak_equity: Decimal
    current_drawdown_percent: Decimal
    daily_realized_loss: Decimal
    symbol_exposure: dict  # symbol -> Decimal value
    strategy_exposure: dict  # strategy_id str -> Decimal value
    total_exposure: Decimal
    open_positions_count: int
    strategy_positions_count: int
    current_price: Decimal | None
    proposed_position_value: Decimal  # qty * price * multiplier
    kill_switch_global: bool
    kill_switch_strategy: bool


class RiskCheck(ABC):
    """Base class for all risk checks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Check name for logging and audit."""

    @property
    @abstractmethod
    def applies_to_exits(self) -> bool:
        """Whether this check runs for exit signals."""

    @abstractmethod
    async def evaluate(self, signal, context: RiskContext) -> CheckResult:
        """Evaluate the signal against this check."""
