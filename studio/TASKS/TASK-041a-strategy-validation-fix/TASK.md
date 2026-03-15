# TASK-041a — Fix Strategy Validation Symbols Format

## Goal

Fix the 500 error when saving a strategy. The validator crashes because `_validate_completeness` expects `config.symbols` to be a dict with a `mode` key, but the frontend sends it as a plain list.

## Problem

```
AttributeError: 'list' object has no attribute 'get'
```

At `backend/app/strategies/validation.py` line ~100, the code calls `symbols.get("mode")` but `symbols` is a list like `["EUR_USD", "GBP_USD"]`, not a dict like `{"mode": "specific", "symbols": ["EUR_USD"]}`.

## Fix

1. In `validation.py`, find every place that accesses `symbols` as a dict and handle both formats:

```python
# Handle both list and dict formats
raw_symbols = config.get("symbols", [])
if isinstance(raw_symbols, list):
    symbol_list = raw_symbols
    mode = "specific"
elif isinstance(raw_symbols, dict):
    mode = raw_symbols.get("mode", "specific")
    symbol_list = raw_symbols.get("symbols", [])
else:
    symbol_list = []
    mode = "specific"
```

2. **Search the entire strategies module** for any other code that assumes `symbols` is a dict — `grep -rn "symbols.get\|symbols\[" backend/app/strategies/`. Fix all occurrences.

3. Also check: `runner.py`, `service.py`, `schemas.py` — anywhere that reads strategy config symbols.

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Saving a strategy with symbols as a list does not return 500 |
| AC2 | Saving a strategy with symbols as a dict still works (backward compatible) |
| AC3 | Validate and Enable buttons work after save |
| AC4 | No other files assume symbols is a dict (grep verified) |
| AC5 | No frontend code modified |
| AC6 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |
