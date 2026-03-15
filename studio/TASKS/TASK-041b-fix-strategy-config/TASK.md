# TASK-041b — Fix Strategy Config CamelCase/Snake_Case Mismatch

## Goal

Fix the 400 error when saving a strategy. The frontend sends config keys in camelCase (`entryConditions`, `exitConditions`, `positionSizing`, `riskManagement`) but the backend validator checks for snake_case (`entry_conditions`, `exit_conditions`, `position_sizing`, `risk_management`).

## Problem

Frontend sends:
```json
{
  "config": {
    "entryConditions": { "logic": "and", "conditions": [...] },
    "exitConditions": { "logic": "and", "conditions": [...] },
    "positionSizing": { "method": "percent_equity", "value": 5 },
    "riskManagement": { "stopLoss": {...}, "takeProfit": {...} },
    "symbols": ["EUR_USD"],
    "timeframe": "5m"
  }
}
```

Validator checks:
```python
config.get("entry_conditions")  # Returns None — key is "entryConditions"
config.get("position_sizing")   # Returns None — key is "positionSizing"
```

Result: All validation checks fail with "required field missing" errors.

## Fix

**Option A (recommended):** Add a camelCase-to-snake_case normalizer at the top of the validation flow. Before any validation runs, convert all config keys:

```python
def _normalize_config_keys(config: dict) -> dict:
    """Convert camelCase keys to snake_case for internal processing."""
    import re
    def to_snake(name):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    
    normalized = {}
    for key, value in config.items():
        snake_key = to_snake(key)
        normalized[snake_key] = value
    return normalized
```

Call this at the entry point of validation, and also in the runner where it reads config fields.

**Option B:** Make the validator check for both key formats:

```python
entry = config.get("entry_conditions") or config.get("entryConditions")
```

Option A is cleaner — normalize once, then all downstream code uses snake_case.

## Scope

Search **all files in the strategies module** that read config dict keys. The mismatch affects:

1. `backend/app/strategies/validation.py` — `_validate_completeness`, `_validate_entry_conditions`, `_validate_exit`, `_validate_position_sizing`, `_validate_symbols`
2. `backend/app/strategies/runner.py` — reads config for evaluation
3. `backend/app/backtesting/runner.py` — reads strategy_config for backtest execution
4. Any other file that does `config.get("entry_conditions")` or similar

**grep for these keys across the backend:**
```bash
grep -rn "entry_conditions\|exit_conditions\|position_sizing\|risk_management" backend/app/strategies/ backend/app/backtesting/
```

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Strategy saves successfully when frontend sends camelCase config keys |
| AC2 | Strategy saves successfully when config uses snake_case keys (backward compatible) |
| AC3 | Validate button returns validation results (not 500 or crash) |
| AC4 | Enable button works on a valid strategy |
| AC5 | Backtest runner can read strategy config regardless of key format |
| AC6 | All config key access points normalized (grep verified) |
| AC7 | No frontend code modified |
| AC8 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |
