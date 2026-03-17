# TASK-041d — Fix Strategy Save Payload & Exit Validation

## Goal

Fix two issues preventing strategy creation and editing:
1. Frontend sends config fields at the top level instead of nested under a `config` key
2. Validator doesn't recognize risk_management.stop_loss/take_profit as valid exit mechanisms

## Problem 1 — Missing `config` wrapper

The API expects:
```json
{
  "key": "sma_crossover",
  "name": "SMA Crossover",
  "market": "forex",
  "description": "",
  "config": {
    "timeframe": "5m",
    "entryConditions": {...},
    "exitConditions": {...},
    "riskManagement": {...},
    "positionSizing": {...},
    "symbols": ["EUR_USD"],
    "schedule": {...}
  }
}
```

But the frontend sends config fields directly in the body (no `config` key). Pydantic returns:
```json
{"type": "missing", "loc": ["body", "config"], "msg": "Field required"}
```

**Fix:** Find the frontend save/create function (likely in `StrategyBuilder.tsx`, `StrategyForm.tsx`, or the strategy API module) and ensure it wraps the config fields under a `config` key when calling `POST /api/v1/strategies` or `PUT /api/v1/strategies/{id}/config`.

Check both:
- **Create:** `POST /api/v1/strategies` — body needs `{ key, name, market, description, config: {...} }`
- **Update config:** `PUT /api/v1/strategies/{id}/config` — body needs `{ config: {...} }` (check what the backend schema expects)

## Problem 2 — Exit validation ignores risk_management SL/TP

The validator says "At least one exit mechanism required (exit conditions, stop loss, or take profit)" even when the user has configured stop_loss and take_profit in the Risk Management section.

**Root cause:** The `_validate_completeness` check in `validation.py` only checks for `exit_conditions` but doesn't check `risk_management.stop_loss` or `risk_management.take_profit`.

**Fix:** In the exit mechanism validation, also check the risk_management section:

```python
# BEFORE:
exit_conditions = config.get("exit_conditions", {})
has_exit = bool(exit_conditions.get("conditions"))
if not has_exit:
    errors.append({"field": "exit", "message": "At least one exit mechanism required"})

# AFTER:
exit_conditions = config.get("exit_conditions", {})
risk_mgmt = config.get("risk_management", {})
has_exit_conditions = bool(exit_conditions.get("conditions"))
has_stop_loss = bool(risk_mgmt.get("stop_loss", {}).get("value"))
has_take_profit = bool(risk_mgmt.get("take_profit", {}).get("value"))
has_exit = has_exit_conditions or has_stop_loss or has_take_profit

if not has_exit:
    errors.append({"field": "exit", "message": "At least one exit mechanism required (exit conditions, stop loss, or take profit)"})
```

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `POST /api/v1/strategies` succeeds when frontend sends strategy with all sections filled |
| AC2 | Config is properly nested under `config` key in the request body |
| AC3 | Strategy with only risk_management SL/TP (no exit conditions) passes validation |
| AC4 | Strategy with only exit conditions (no SL/TP) still passes validation |
| AC5 | Strategy with both exit conditions and SL/TP passes validation |
| AC6 | Strategy with neither exit conditions nor SL/TP fails validation with clear error |
| AC7 | Updating an existing strategy's config works (`PUT /strategies/{id}/config`) |
| AC8 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Modify

| File | What Changes |
|------|-------------|
| Frontend strategy save function | Wrap config under `config` key in request body |
| `backend/app/strategies/validation.py` | Check risk_management for SL/TP as valid exit mechanism |

## Builder Notes

- **Find the save function:** Search frontend for `POST.*strategies` or the axios/fetch call that creates a strategy. It's likely in a feature module like `features/strategies/`, a page component, or an API utility file.
- **Check both create and update paths.** The create (`POST /strategies`) and update (`PUT /strategies/{id}/config`) may have different payload structures.
- **The camelCase normalizer handles key conversion.** The backend's `normalize_config_keys()` from TASK-041b converts `riskManagement` → `risk_management`, so the validation check should use snake_case keys.
