"""Risk module domain errors."""

from app.common.errors import DomainError


class RiskEvaluationError(DomainError):
    def __init__(self, message: str = "Risk evaluation error", details: dict | None = None):
        super().__init__(code="RISK_EVALUATION_ERROR", message=message, details=details)


class RiskConfigNotFoundError(DomainError):
    def __init__(self):
        super().__init__(code="RISK_CONFIG_NOT_FOUND", message="Risk configuration not found")


class KillSwitchAlreadyActiveError(DomainError):
    def __init__(self, scope: str = "global"):
        super().__init__(
            code="RISK_KILL_SWITCH_ALREADY_ACTIVE",
            message=f"Kill switch ({scope}) is already active",
            details={"scope": scope},
        )


class KillSwitchNotActiveError(DomainError):
    def __init__(self, scope: str = "global"):
        super().__init__(
            code="RISK_KILL_SWITCH_NOT_ACTIVE",
            message=f"Kill switch ({scope}) is not active",
            details={"scope": scope},
        )


class RiskDecisionNotFoundError(DomainError):
    def __init__(self, decision_id: str = ""):
        super().__init__(
            code="RISK_DECISION_NOT_FOUND",
            message=f"Risk decision not found: {decision_id}" if decision_id else "Risk decision not found",
        )
