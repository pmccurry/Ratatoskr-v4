"""Strategy discovery and registration module."""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, Type

from .base import Strategy

logger = logging.getLogger(__name__)

# Global registry
_strategies: Dict[str, Type[Strategy]] = {}
_instances: Dict[str, Strategy] = {}


def discover_strategies(strategies_dir: str = None) -> Dict[str, Type[Strategy]]:
    """
    Scan the strategies/ directory and register all Strategy subclasses.

    Args:
        strategies_dir: Path to strategies folder.
                       Defaults to {repo_root}/strategies/

    Returns:
        Dict mapping strategy name -> strategy class
    """
    if strategies_dir is None:
        # Default: repo_root/strategies/
        # This file is at backend/app/strategy_sdk/registry.py
        # repo_root is 4 levels up: strategy_sdk -> app -> backend -> repo_root
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        strategies_dir = repo_root / "strategies"
    else:
        strategies_dir = Path(strategies_dir)

    if not strategies_dir.exists():
        logger.warning("Strategies directory not found: %s", strategies_dir)
        strategies_dir.mkdir(parents=True, exist_ok=True)
        return {}

    discovered = {}

    for py_file in sorted(strategies_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        try:
            # Import the module
            module_name = f"strategies.{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find Strategy subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                    and issubclass(attr, Strategy)
                    and attr is not Strategy
                    and attr.name):  # Must have a name set
                    discovered[attr.name] = attr
                    logger.info("Discovered strategy: %s (%s)", attr.name, py_file.name)

        except Exception as e:
            logger.error("Failed to load strategy from %s: %s", py_file.name, e)

    _strategies.update(discovered)
    return discovered


def get_strategy_class(name: str) -> Type[Strategy] | None:
    """Get a registered strategy class by name."""
    return _strategies.get(name)


def get_strategy_instance(name: str) -> Strategy | None:
    """Get or create a strategy instance by name."""
    if name not in _instances:
        cls = _strategies.get(name)
        if cls is None:
            return None
        _instances[name] = cls()
    return _instances[name]


def list_strategies() -> list[dict]:
    """List all registered strategies with metadata."""
    result = []
    for name, cls in _strategies.items():
        result.append({
            "name": cls.name,
            "description": cls.description,
            "symbols": cls.symbols,
            "timeframe": cls.timeframe,
            "market": cls.market,
            "parameters": cls.get_parameters(),
            "type": "python",
        })
    return result


def reset():
    """Clear all registrations (for testing)."""
    _strategies.clear()
    _instances.clear()
