"""CLI for running Python strategy backtests.

Usage:
    cd backend
    python -m app.backtesting.cli backtest strategies/example_sma_cross.py \
        --start 2025-06-01 --end 2026-03-01 --capital 100000
"""

import argparse
import asyncio
import importlib.util
import json
import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.strategy_sdk.base import Strategy

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ratatoskr Backtest CLI")
    subparsers = parser.add_subparsers(dest="command")

    bt = subparsers.add_parser("backtest", help="Run a Python strategy backtest")
    bt.add_argument("strategy_file", help="Path to strategy .py file")
    bt.add_argument("--symbols", nargs="+", help="Override symbols")
    bt.add_argument("--timeframe", help="Override timeframe")
    bt.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    bt.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    bt.add_argument("--capital", type=float, default=100000, help="Initial capital")
    bt.add_argument("--param", nargs=2, action="append", metavar=("KEY", "VALUE"),
                    help="Override strategy parameter (can repeat)")

    args = parser.parse_args()
    if args.command == "backtest":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        asyncio.run(run_backtest(args))
    else:
        parser.print_help()


def _load_strategy_class(filepath: str) -> type:
    """Load a Strategy subclass from a .py file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    spec = importlib.util.spec_from_file_location(f"cli_strategy.{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, Strategy) and attr is not Strategy and attr.name:
            return attr

    print(f"Error: no Strategy subclass found in {filepath}", file=sys.stderr)
    sys.exit(1)


async def run_backtest(args):
    """Execute a backtest from CLI."""
    # Load strategy
    strategy_cls = _load_strategy_class(args.strategy_file)
    strategy = strategy_cls()

    symbols = args.symbols or strategy.symbols
    timeframe = args.timeframe or strategy.timeframe
    start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # Apply param overrides
    if args.param:
        from app.backtesting.python_runner import PythonBacktestRunner
        runner = PythonBacktestRunner()
        overrides = {}
        for key, value in args.param:
            try:
                overrides[key] = json.loads(value)
            except json.JSONDecodeError:
                overrides[key] = value
        runner._apply_overrides(strategy, overrides)

    print(f"Strategy: {strategy.name}")
    print(f"Symbols:  {', '.join(symbols)}")
    print(f"Period:   {args.start} to {args.end}")
    print(f"Capital:  ${args.capital:,.0f}")
    print()

    # Connect to database
    from app.common.database import get_session_factory

    factory = get_session_factory()

    # Create a minimal backtest_run-like object
    from types import SimpleNamespace
    from uuid import uuid4

    run = SimpleNamespace(
        id=uuid4(),
        symbols=symbols,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.capital,
        position_sizing={"type": "fixed", "amount": 10000},
        strategy_type="python",
        strategy_file=args.strategy_file,
        strategy_config={},
        metrics=None,
        bars_processed=None,
        total_trades=None,
    )

    # Run backtest (don't store to DB in CLI mode)
    from app.backtesting.python_runner import PythonBacktestRunner
    runner = PythonBacktestRunner()

    async with factory() as db:
        metrics = await runner.run(run, strategy, db, store_results=False)

    # Print results
    print("=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)
    for key, value in sorted(metrics.items()):
        if isinstance(value, float):
            print(f"  {key:30s} {value:>12.2f}")
        else:
            print(f"  {key:30s} {str(value):>12s}")
    print("=" * 50)


if __name__ == "__main__":
    main()
