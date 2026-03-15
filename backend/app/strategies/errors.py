"""Strategy module domain errors."""

from app.common.errors import DomainError


class StrategyNotFoundError(DomainError):
    def __init__(self, strategy_id: str = ""):
        super().__init__(
            code="STRATEGY_NOT_FOUND",
            message=f"Strategy not found: {strategy_id}" if strategy_id else "Strategy not found",
        )


class StrategyInvalidConfigError(DomainError):
    def __init__(self, message: str = "Invalid strategy configuration", details: dict | None = None):
        super().__init__(
            code="STRATEGY_INVALID_CONFIG",
            message=message,
            details=details,
        )


class StrategyEvaluationError(DomainError):
    def __init__(self, message: str = "Strategy evaluation failed", details: dict | None = None):
        super().__init__(
            code="STRATEGY_EVALUATION_ERROR",
            message=message,
            details=details,
        )


class FormulaParseError(DomainError):
    def __init__(self, message: str = "Formula parse error", details: dict | None = None):
        super().__init__(
            code="STRATEGY_FORMULA_PARSE_ERROR",
            message=message,
            details=details,
        )


class FormulaValidationError(DomainError):
    def __init__(self, message: str = "Formula validation failed", details: dict | None = None):
        super().__init__(
            code="STRATEGY_FORMULA_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class IndicatorNotFoundError(DomainError):
    def __init__(self, indicator_key: str = ""):
        super().__init__(
            code="STRATEGY_INDICATOR_NOT_FOUND",
            message=f"Indicator not found: {indicator_key}" if indicator_key else "Indicator not found",
        )


class InvalidConditionError(DomainError):
    def __init__(self, message: str = "Invalid condition", details: dict | None = None):
        super().__init__(
            code="STRATEGY_INVALID_CONDITION",
            message=message,
            details=details,
        )
