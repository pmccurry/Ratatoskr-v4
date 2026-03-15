"""Risk service — evaluation pipeline, kill switch, config, overview."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.risk.checks.base import CheckOutcome, RiskCheck, RiskContext
from app.risk.errors import (
    KillSwitchAlreadyActiveError,
    KillSwitchNotActiveError,
    RiskDecisionNotFoundError,
)
from app.risk.models import KillSwitch, RiskConfig, RiskConfigAudit, RiskDecision
from app.risk.monitoring.daily_loss import DailyLossMonitor
from app.risk.monitoring.drawdown import DrawdownMonitor
from app.risk.monitoring.exposure import ExposureCalculator
from app.risk.repository import (
    KillSwitchRepository,
    RiskConfigAuditRepository,
    RiskConfigRepository,
    RiskDecisionRepository,
)
from app.signals.models import Signal

logger = logging.getLogger(__name__)

_EXIT_SIGNAL_TYPES = {"exit", "scale_out"}


class RiskService:
    """Risk evaluation pipeline and management."""

    def __init__(self, checks: list[RiskCheck]):
        self._checks = checks
        self._decision_repo = RiskDecisionRepository()
        self._ks_repo = KillSwitchRepository()
        self._config_repo = RiskConfigRepository()
        self._audit_repo = RiskConfigAuditRepository()
        self._drawdown = DrawdownMonitor()
        self._daily_loss = DailyLossMonitor()
        self._exposure = ExposureCalculator()

    # --- Evaluation Pipeline ---

    async def evaluate_signal(self, db: AsyncSession, signal: Signal) -> RiskDecision:
        """Evaluate a single signal through risk checks."""
        now = datetime.now(timezone.utc)

        # Load strategy
        from app.strategies.repository import StrategyConfigRepository, StrategyRepository

        strategy = await StrategyRepository().get_by_id(db, signal.strategy_id)
        if not strategy:
            # Strategy deleted between signal creation and risk eval
            decision = await self._create_decision(
                db,
                signal.id,
                "rejected",
                [],
                "strategy_enable",
                "strategy_not_found",
                f"Strategy {signal.strategy_id} not found",
                None,
                {},
                now,
            )
            await self._update_signal_status(db, signal.id, "risk_rejected")
            return decision

        active_config = await StrategyConfigRepository().get_active(db, strategy.id)
        strategy_config = active_config.config_json if active_config else {}

        context = await self._build_context(db, signal, strategy, strategy_config)

        # Exit signals get fast path
        if signal.signal_type in _EXIT_SIGNAL_TYPES:
            return await self._evaluate_exit_fast_path(db, signal, context, now)

        # Run checks in order
        checks_passed: list[str] = []
        all_modifications: dict = {}

        for check in self._checks:
            if not check.applies_to_exits and signal.signal_type in _EXIT_SIGNAL_TYPES:
                continue

            result = await check.evaluate(signal, context)

            if result.outcome == CheckOutcome.REJECT:
                decision = await self._create_decision(
                    db,
                    signal.id,
                    "rejected",
                    checks_passed,
                    check.name,
                    result.reason_code,
                    result.reason_text,
                    None,
                    self._build_portfolio_snapshot(context),
                    now,
                )
                await self._update_signal_status(db, signal.id, "risk_rejected")
                logger.info(
                    "Signal %s rejected by %s: %s",
                    signal.id,
                    check.name,
                    result.reason_code,
                )
                return decision

            if result.outcome == CheckOutcome.MODIFY:
                checks_passed.append(check.name)
                if result.modifications:
                    all_modifications.update(result.modifications)
                continue

            # PASS
            checks_passed.append(check.name)

        # All checks passed (possibly with modifications)
        if all_modifications:
            status = "modified"
            signal_status = "risk_modified"
        else:
            status = "approved"
            signal_status = "risk_approved"

        decision = await self._create_decision(
            db,
            signal.id,
            status,
            checks_passed,
            None,
            status,
            f"Signal {status} after all risk checks",
            all_modifications if all_modifications else None,
            self._build_portfolio_snapshot(context),
            now,
        )
        await self._update_signal_status(db, signal.id, signal_status)
        logger.info("Signal %s %s", signal.id, signal_status)
        return decision

    async def evaluate_pending_signals(self, db: AsyncSession) -> dict:
        """Evaluate all pending signals."""
        from app.signals.startup import get_signal_service

        signal_service = get_signal_service()
        pending = await signal_service.get_pending_signals(db)

        evaluated = 0
        approved = 0
        rejected = 0
        modified = 0

        for signal in pending:
            try:
                decision = await self.evaluate_signal(db, signal)
                evaluated += 1
                if decision.status == "approved":
                    approved += 1
                elif decision.status == "rejected":
                    rejected += 1
                elif decision.status == "modified":
                    modified += 1
            except Exception as e:
                logger.error("Risk evaluation error for signal %s: %s", signal.id, e)

        return {
            "evaluated": evaluated,
            "approved": approved,
            "rejected": rejected,
            "modified": modified,
        }

    async def _build_context(
        self,
        db: AsyncSession,
        signal: Signal,
        strategy: object,
        strategy_config: dict,
    ) -> RiskContext:
        """Build the shared evaluation context."""
        risk_config = await self.get_risk_config(db)

        # Kill switch state
        global_ks = await self._ks_repo.get_global(db)
        strategy_ks = await self._ks_repo.get_for_strategy(db, signal.strategy_id)

        # Exposure data (stubbed until TASK-013)
        exposure_data = await self._exposure.get_exposure(db, risk_config)
        portfolio_equity = exposure_data["portfolio_equity"]

        # Drawdown (stubbed until TASK-013)
        drawdown_data = await self._drawdown.get_current_drawdown(db, risk_config)

        # Daily loss (stubbed until TASK-013)
        daily_loss_data = await self._daily_loss.get_daily_loss(
            db, risk_config, portfolio_equity
        )

        # Current price for the signal's symbol
        current_price = None
        try:
            from app.market_data.service import MarketDataService

            current_price = await MarketDataService().get_latest_close(db, signal.symbol)
        except Exception:
            pass

        # Compute proposed position value from signal data
        proposed_position_value = Decimal("0")
        if current_price and current_price > 0:
            signal_qty = getattr(signal, "requested_qty", None)
            if signal_qty is None:
                # Estimate from strategy config position sizing
                sizing = strategy_config.get("position_sizing", {})
                method = sizing.get("method", "fixed_qty")
                value = Decimal(str(sizing.get("value", "100")))
                if method == "fixed_qty":
                    signal_qty = value
                elif method == "fixed_dollar":
                    signal_qty = value / current_price if current_price > 0 else Decimal("0")
                elif method == "percent_equity":
                    signal_qty = (portfolio_equity * value / Decimal("100")) / current_price if current_price > 0 else Decimal("0")
                else:
                    signal_qty = value
            contract_multiplier = Decimal(str(getattr(signal, "contract_multiplier", 1) or 1))
            proposed_position_value = Decimal(str(signal_qty)) * current_price * contract_multiplier

        return RiskContext(
            risk_config=risk_config,
            strategy=strategy,
            strategy_config=strategy_config,
            portfolio_equity=portfolio_equity,
            portfolio_cash=await self._get_portfolio_cash(db, strategy),
            peak_equity=drawdown_data["peak_equity"],
            current_drawdown_percent=drawdown_data["drawdown_percent"],
            daily_realized_loss=daily_loss_data["current_loss"],
            symbol_exposure=exposure_data["by_symbol"],
            strategy_exposure=exposure_data["by_strategy"],
            total_exposure=exposure_data["total_value"],
            open_positions_count=await self._get_positions_count(db, signal.strategy_id),
            strategy_positions_count=await self._get_positions_count(db, signal.strategy_id),
            current_price=current_price,
            proposed_position_value=proposed_position_value,
            kill_switch_global=global_ks.is_active if global_ks else False,
            kill_switch_strategy=strategy_ks.is_active if strategy_ks else False,
        )

    async def _evaluate_exit_fast_path(
        self,
        db: AsyncSession,
        signal: Signal,
        context: RiskContext,
        now: datetime,
    ) -> RiskDecision:
        """Fast path for exit signals. Almost always approves."""
        checks_passed = ["exit_fast_path"]
        modifications: dict | None = None

        # Only run checks that apply to exits
        for check in self._checks:
            if not check.applies_to_exits:
                continue
            result = await check.evaluate(signal, context)
            if result.outcome == CheckOutcome.MODIFY and result.modifications:
                if modifications is None:
                    modifications = {}
                modifications.update(result.modifications)
            checks_passed.append(check.name)

        status = "modified" if modifications else "approved"
        signal_status = "risk_modified" if modifications else "risk_approved"

        decision = await self._create_decision(
            db,
            signal.id,
            status,
            checks_passed,
            None,
            "exit_approved",
            "Exit signals receive expedited approval",
            modifications,
            self._build_portfolio_snapshot(context),
            now,
        )
        await self._update_signal_status(db, signal.id, signal_status)
        logger.info("Signal %s exit %s", signal.id, signal_status)
        return decision

    async def _create_decision(
        self,
        db: AsyncSession,
        signal_id: UUID,
        status: str,
        checks_passed: list[str],
        failed_check: str | None,
        reason_code: str,
        reason_text: str,
        modifications: dict | None,
        portfolio_snapshot: dict,
        ts: datetime,
    ) -> RiskDecision:
        decision = RiskDecision(
            signal_id=signal_id,
            status=status,
            checks_passed=checks_passed,
            failed_check=failed_check,
            reason_code=reason_code,
            reason_text=reason_text,
            modifications_json=modifications,
            portfolio_state_snapshot=portfolio_snapshot,
            ts=ts,
        )
        result = await self._decision_repo.create(db, decision)

        # Emit audit event for risk decision
        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                emoji = {"approved": "✅", "rejected": "❌", "modified": "⚙️"}.get(status, "🔍")
                severity = "warning" if status == "rejected" else "info"
                await emitter.emit(
                    event_type="risk.evaluation.completed",
                    category="risk",
                    severity=severity,
                    source_module="risk",
                    summary=f"{emoji} Risk {status}: {reason_text}",
                    entity_type="risk_decision",
                    entity_id=result.id,
                    details={
                        "signal_id": str(signal_id),
                        "status": status,
                        "checks_passed": checks_passed,
                        "failed_check": failed_check,
                        "reason_code": reason_code,
                    },
                )
        except Exception:
            pass

        return result

    async def _update_signal_status(
        self, db: AsyncSession, signal_id: UUID, new_status: str
    ) -> None:
        from app.signals.startup import get_signal_service

        signal_service = get_signal_service()
        await signal_service.update_signal_status(db, signal_id, new_status)

    def _build_portfolio_snapshot(self, context: RiskContext) -> dict:
        return {
            "equity": str(context.portfolio_equity),
            "cash": str(context.portfolio_cash),
            "total_exposure_percent": str(
                context.total_exposure / context.portfolio_equity * 100
                if context.portfolio_equity > 0
                else Decimal("0")
            ),
            "drawdown_percent": str(context.current_drawdown_percent),
            "daily_pnl": str(-context.daily_realized_loss),
            "peak_equity": str(context.peak_equity),
            "open_positions_count": context.open_positions_count,
        }

    # --- Kill Switch ---

    async def activate_kill_switch(
        self,
        db: AsyncSession,
        scope: str,
        strategy_id: UUID | None,
        activated_by: str,
        reason: str | None,
    ) -> KillSwitch:
        now = datetime.now(timezone.utc)

        if scope == "global":
            existing = await self._ks_repo.get_global(db)
        else:
            existing = await self._ks_repo.get_for_strategy(db, strategy_id)

        if existing and existing.is_active:
            raise KillSwitchAlreadyActiveError(scope)

        ks = KillSwitch(
            scope=scope,
            strategy_id=strategy_id if scope == "strategy" else None,
            is_active=True,
            activated_by=activated_by,
            activated_at=now,
            deactivated_at=None,
            reason=reason,
        )
        result = await self._ks_repo.upsert(db, ks)
        logger.info(
            "Kill switch activated: scope=%s, by=%s, reason=%s",
            scope,
            activated_by,
            reason,
        )

        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="risk.kill_switch.activated",
                    category="risk",
                    severity="critical",
                    source_module="risk",
                    summary=f"🛑 Kill switch activated: {scope} by {activated_by}: {reason}",
                    entity_type="kill_switch",
                    entity_id=result.id,
                    strategy_id=strategy_id,
                    details={
                        "scope": scope,
                        "activated_by": activated_by,
                        "reason": reason,
                        "strategy_id": str(strategy_id) if strategy_id else None,
                    },
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        return result

    async def deactivate_kill_switch(
        self,
        db: AsyncSession,
        scope: str,
        strategy_id: UUID | None,
    ) -> KillSwitch:
        now = datetime.now(timezone.utc)

        if scope == "global":
            existing = await self._ks_repo.get_global(db)
        else:
            existing = await self._ks_repo.get_for_strategy(db, strategy_id)

        if not existing or not existing.is_active:
            raise KillSwitchNotActiveError(scope)

        existing.is_active = False
        existing.deactivated_at = now
        await db.flush()
        logger.info("Kill switch deactivated: scope=%s", scope)

        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="risk.kill_switch.deactivated",
                    category="risk",
                    severity="info",
                    source_module="risk",
                    summary=f"✅ Kill switch deactivated: {scope} by system",
                    entity_type="kill_switch",
                    entity_id=existing.id,
                    strategy_id=strategy_id,
                    details={
                        "scope": scope,
                        "strategy_id": str(strategy_id) if strategy_id else None,
                    },
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        return existing

    async def get_kill_switch_status(self, db: AsyncSession) -> dict:
        global_ks = await self._ks_repo.get_global(db)
        active_switches = await self._ks_repo.get_all_active(db)

        strategies = []
        for ks in active_switches:
            if ks.scope == "strategy" and ks.strategy_id:
                strategies.append(
                    {
                        "strategy_id": str(ks.strategy_id),
                        "is_active": ks.is_active,
                        "reason": ks.reason,
                    }
                )

        return {
            "global_active": global_ks.is_active if global_ks else False,
            "strategies": strategies,
        }

    # --- Risk Config ---

    async def get_risk_config(self, db: AsyncSession) -> RiskConfig:
        config = await self._config_repo.get_active(db)
        if not config:
            config = await self._config_repo.seed_defaults(db)
        return config

    async def update_risk_config(
        self,
        db: AsyncSession,
        updates: dict,
        changed_by: str,
    ) -> RiskConfig:
        config = await self.get_risk_config(db)
        now = datetime.now(timezone.utc)

        for field_name, new_value in updates.items():
            if new_value is not None and hasattr(config, field_name):
                old_value = getattr(config, field_name)
                if old_value != new_value:
                    setattr(config, field_name, new_value)
                    audit = RiskConfigAudit(
                        field_changed=field_name,
                        old_value=str(old_value) if old_value is not None else "",
                        new_value=str(new_value),
                        changed_by=changed_by,
                        changed_at=now,
                    )
                    await self._audit_repo.create(db, audit)

        config.updated_by = changed_by
        await db.flush()
        logger.info("Risk config updated by %s", changed_by)

        try:
            from app.observability.startup import get_event_emitter
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    event_type="risk.config.changed",
                    category="risk",
                    severity="info",
                    source_module="risk",
                    summary="⚙️ Risk config updated",
                    entity_type="risk_config",
                    entity_id=config.id,
                    details={
                        "changed_by": changed_by,
                        "fields_updated": list(updates.keys()),
                    },
                )
        except Exception:
            pass  # Event emission never disrupts trading pipeline

        return config

    async def get_config_audit(
        self,
        db: AsyncSession,
        page: int,
        page_size: int,
    ) -> tuple[list[RiskConfigAudit], int]:
        return await self._audit_repo.get_history(db, page=page, page_size=page_size)

    # --- Risk Overview ---

    async def get_overview(self, db: AsyncSession) -> dict:
        risk_config = await self.get_risk_config(db)
        ks_status = await self.get_kill_switch_status(db)
        drawdown = await self._drawdown.get_current_drawdown(db, risk_config)
        exposure_data = await self._exposure.get_exposure(db, risk_config)
        daily_loss = await self._daily_loss.get_daily_loss(
            db, risk_config, exposure_data["portfolio_equity"]
        )
        recent = await self._decision_repo.get_recent(db, limit=10)

        recent_decisions = []
        for d in recent:
            recent_decisions.append(
                {
                    "id": str(d.id),
                    "signal_id": str(d.signal_id),
                    "status": d.status,
                    "reason_code": d.reason_code,
                    "ts": d.ts.isoformat(),
                }
            )

        # Build exposure lists
        portfolio_equity = exposure_data["portfolio_equity"]
        symbol_list = []
        for sym, val in exposure_data["by_symbol"].items():
            pct = (
                val / portfolio_equity * 100
                if portfolio_equity > 0
                else Decimal("0")
            )
            symbol_list.append(
                {
                    "symbol": sym,
                    "current_percent": str(pct),
                    "limit_percent": str(risk_config.max_symbol_exposure_percent),
                }
            )

        strategy_list = []
        for sid, val in exposure_data["by_strategy"].items():
            pct = (
                val / portfolio_equity * 100
                if portfolio_equity > 0
                else Decimal("0")
            )
            strategy_list.append(
                {
                    "strategy_id": sid,
                    "current_percent": str(pct),
                    "limit_percent": str(risk_config.max_strategy_exposure_percent),
                }
            )

        total_pct = exposure_data["total_percent"]

        return {
            "kill_switch": ks_status,
            "drawdown": drawdown,
            "daily_loss": daily_loss,
            "total_exposure": {
                "current_percent": str(total_pct),
                "limit_percent": str(risk_config.max_total_exposure_percent),
            },
            "symbol_exposure": symbol_list,
            "strategy_exposure": strategy_list,
            "recent_decisions": recent_decisions,
        }

    # --- Exposure ---

    async def get_exposure(self, db: AsyncSession) -> dict:
        risk_config = await self.get_risk_config(db)
        return await self._exposure.get_exposure(db, risk_config)

    # --- Drawdown ---

    async def get_drawdown(self, db: AsyncSession) -> dict:
        risk_config = await self.get_risk_config(db)
        drawdown = await self._drawdown.get_current_drawdown(db, risk_config)

        # Auto-activate kill switch on catastrophic drawdown
        if drawdown["threshold_status"] == "catastrophic":
            global_ks = await self._ks_repo.get_global(db)
            if not global_ks or not global_ks.is_active:
                await self.activate_kill_switch(
                    db,
                    "global",
                    None,
                    "system",
                    f"Catastrophic drawdown: {drawdown['drawdown_percent']:.1f}%",
                )

        return drawdown

    async def reset_peak_equity(self, db: AsyncSession, admin_user: str) -> None:
        await self._drawdown.reset_peak_equity(db, admin_user)

    # --- Decisions ---

    async def get_decision(self, db: AsyncSession, decision_id: UUID) -> RiskDecision:
        decision = await self._decision_repo.get_by_id(db, decision_id)
        if not decision:
            raise RiskDecisionNotFoundError(str(decision_id))
        return decision

    async def list_decisions(
        self,
        db: AsyncSession,
        status: str | None = None,
        reason_code: str | None = None,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RiskDecision], int]:
        return await self._decision_repo.get_filtered(
            db,
            status=status,
            reason_code=reason_code,
            date_start=date_start,
            date_end=date_end,
            page=page,
            page_size=page_size,
        )

    # --- Portfolio helpers ---

    async def _get_portfolio_cash(self, db: AsyncSession, strategy: object) -> Decimal:
        """Get portfolio cash balance from portfolio module."""
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                user_id = getattr(strategy, "user_id", None)
                if user_id:
                    return await portfolio_service.get_total_cash(db, user_id)
        except Exception:
            pass
        # Fallback to equity (conservative estimate)
        return await self._exposure._get_portfolio_equity(db)

    async def _get_positions_count(self, db: AsyncSession, strategy_id: UUID) -> int:
        """Get open position count for a strategy from portfolio module."""
        try:
            from app.portfolio.startup import get_portfolio_service
            portfolio_service = get_portfolio_service()
            if portfolio_service:
                return await portfolio_service.get_positions_count(db, strategy_id)
        except Exception:
            pass
        return 0
