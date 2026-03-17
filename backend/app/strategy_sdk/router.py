"""API endpoints for Python strategy management."""

from datetime import datetime, timezone
from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.common.database import get_db
from app.backtesting.schemas import PythonBacktestRequest

from .registry import list_strategies, get_strategy_class
from .runner import get_python_runner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/python-strategies", tags=["python-strategies"])


@router.get("/status/all")
async def get_runner_status(user=Depends(get_current_user)):
    """Get status of all Python strategies."""
    runner = get_python_runner()
    return {"data": runner.get_status()}


@router.get("")
async def list_python_strategies(user=Depends(get_current_user)):
    """List all discovered Python strategies."""
    return {"data": list_strategies()}


@router.get("/{name}")
async def get_python_strategy(name: str, user=Depends(get_current_user)):
    """Get details for a specific Python strategy."""
    cls = get_strategy_class(name)
    if not cls:
        raise HTTPException(404, f"Strategy '{name}' not found")
    return {"data": {
        "name": cls.name,
        "description": cls.description,
        "symbols": cls.symbols,
        "timeframe": cls.timeframe,
        "market": cls.market,
        "parameters": cls.get_parameters(),
        "type": "python",
    }}


@router.post("/{name}/start")
async def start_strategy(name: str, user=Depends(get_current_user)):
    """Start a Python strategy for paper trading."""
    cls = get_strategy_class(name)
    if not cls:
        raise HTTPException(404, f"Strategy '{name}' not found")

    runner = get_python_runner()
    await runner.start_strategy(name, None)  # TODO: pass session factory
    return {"data": {"name": name, "status": "running"}}


@router.post("/{name}/stop")
async def stop_strategy(name: str, user=Depends(get_current_user)):
    """Stop a running Python strategy."""
    runner = get_python_runner()
    await runner.stop_strategy(name)
    return {"data": {"name": name, "status": "stopped"}}


@router.post("/{name}/backtest", status_code=201)
async def backtest_python_strategy(
    name: str,
    body: PythonBacktestRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a backtest on a Python strategy."""
    from app.strategy_sdk.registry import get_strategy_class
    from app.backtesting.python_runner import PythonBacktestRunner
    from app.backtesting.models import BacktestRun
    from app.backtesting.schemas import BacktestRunResponse

    cls = get_strategy_class(name)
    if not cls:
        raise HTTPException(404, f"Strategy '{name}' not found")

    # Create fresh instance (not the singleton)
    strategy = cls()

    # Apply parameter overrides
    if body.parameter_overrides:
        runner = PythonBacktestRunner()
        try:
            runner._apply_overrides(strategy, body.parameter_overrides)
        except ValueError as e:
            raise HTTPException(400, str(e))

    symbols = body.symbols or strategy.symbols
    timeframe = body.timeframe or strategy.timeframe

    # Create backtest run record
    now = datetime.now(timezone.utc)
    run = BacktestRun(
        strategy_id=None,  # Python strategies don't have a DB strategy record
        status="running",
        strategy_type="python",
        strategy_file=name,
        strategy_config={"name": strategy.name, "parameters": strategy.get_parameters()},
        symbols=symbols,
        timeframe=timeframe,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=Decimal(str(body.initial_capital)),
        position_sizing=body.position_sizing or {"type": "fixed", "amount": 10000},
        exit_config={},
        started_at=now,
    )
    db.add(run)
    await db.flush()

    try:
        runner = PythonBacktestRunner()
        metrics = await runner.run(run, strategy, db)
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        if run.started_at:
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
    except Exception as exc:
        logger.exception("Python backtest %s failed: %s", run.id, exc)
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        if run.started_at:
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
        run.error = str(exc)

    await db.flush()

    return {"data": BacktestRunResponse.model_validate(run).model_dump(by_alias=True)}
