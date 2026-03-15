# Builder Output — TASK-041b

## Task
Fix Strategy Config CamelCase/Snake_Case Mismatch

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
None

## Files Modified
- `backend/app/strategies/validation.py` — Added `normalize_config_keys()` function that recursively converts camelCase dict keys to snake_case. Applied at the top of `validate()` method so all downstream validation uses snake_case.
- `backend/app/strategies/runner.py` — Applied `normalize_config_keys()` to `config_json` at the top of `evaluate_strategy()` so all config reads (entry_conditions, exit_conditions, stop_loss, take_profit, trailing_stop, entry_side, lookback_bars, trading_hours, max_hold_bars) use normalized keys.
- `backend/app/strategies/safety_monitor.py` — Applied `normalize_config_keys()` to `config_json` in the safety monitor loop so SL/TP/trailing stop checks work regardless of key format.
- `backend/app/backtesting/runner.py` — Applied `normalize_config_keys()` to `backtest_run.strategy_config` at the top of `run()` so backtest condition evaluation and exit logic use normalized keys.

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: Strategy saves successfully when frontend sends camelCase config keys — ✅ Done (normalize_config_keys converts entryConditions→entry_conditions, etc.)
2. AC2: Strategy saves successfully when config uses snake_case keys — ✅ Done (normalizer is idempotent: snake_case keys pass through unchanged)
3. AC3: Validate button returns validation results — ✅ Done (validation.py normalizes config before checking)
4. AC4: Enable button works on a valid strategy — ✅ Done (runner.py normalizes config before evaluating)
5. AC5: Backtest runner can read strategy config regardless of key format — ✅ Done (backtesting/runner.py normalizes config)
6. AC6: All config key access points normalized — ✅ Done (4 entry points: validation.validate(), runner.evaluate_strategy(), safety_monitor loop, backtesting.runner.run())
7. AC7: No frontend code modified — ✅ Done
8. AC8: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- The normalizer recursively converts all nested dict keys, not just top-level. This handles nested camelCase keys like `stopLoss.type` → `stop_loss.type` correctly.
- Lists are traversed but list items that are strings (like symbol names) are left unchanged — only dict keys are converted.
- The normalizer is idempotent: running it on already-snake_case config produces the same output.

## Ambiguities Encountered
None — task was unambiguous

## Dependencies Discovered
None

## Tests Created
None — not required by this task. Verified normalizer manually with assertion test.

## Risks or Concerns
None identified — the normalizer is pure, stateless, and idempotent.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
None — this was a targeted bug fix.
