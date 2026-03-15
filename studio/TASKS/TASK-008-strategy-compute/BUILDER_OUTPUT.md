# Builder Output — TASK-008

## Task
Strategy: Indicator Library, Condition Engine, and Formula Parser

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created

backend/app/strategies/indicators/registry.py
backend/app/strategies/indicators/compute.py
backend/app/strategies/indicators/schemas.py
backend/app/strategies/conditions/engine.py
backend/app/strategies/conditions/schemas.py
backend/app/strategies/formulas/parser.py
backend/app/strategies/formulas/schemas.py
backend/app/strategies/errors.py
backend/app/strategies/config.py

## Files Modified

backend/app/strategies/indicators/__init__.py — replaced empty file with full indicator registration (26 indicators, get_registry())
backend/app/strategies/router.py — replaced empty stub with GET /strategies/indicators and POST /strategies/formulas/validate endpoints
backend/app/common/errors.py — added 6 strategy error codes to _ERROR_STATUS_MAP (STRATEGY_INVALID_CONFIG, STRATEGY_EVALUATION_ERROR, STRATEGY_FORMULA_PARSE_ERROR, STRATEGY_FORMULA_VALIDATION_ERROR, STRATEGY_INDICATOR_NOT_FOUND, STRATEGY_INVALID_CONDITION)

## Files Deleted
None

## Acceptance Criteria Status

### Indicator Library
1. IndicatorRegistry stores and retrieves indicator definitions by key — ✅ Done (register, get, list_all, list_by_category, exists methods)
2. All 26 indicators are registered (4 trend + 6 momentum + 3 volatility + 3 volume + 3 trend strength + 7 price reference) — ✅ Done (verified: len(registry.list_all()) == 26)
3. Each registration includes key, name, category, params with types/defaults/ranges, outputs, description, and compute function reference — ✅ Done (IndicatorDefinition dataclass with all fields)
4. compute_sma correctly calculates simple moving average — ✅ Done (sum of last N / N, verified)
5. compute_ema correctly calculates exponential moving average with proper multiplier — ✅ Done (multiplier = 2/(period+1), SMA seed, verified)
6. compute_rsi correctly calculates RSI with Wilder's smoothing — ✅ Done (initial SMA then Wilder's smoothed avg_gain/avg_loss, verified: all-up bars → RSI=100)
7. compute_macd returns macd_line, signal_line, and histogram — ✅ Done (EMA series approach, verified with 40 bars)
8. compute_stochastic returns k and d values — ✅ Done (raw_k → SMA slowing → %K → SMA d_period → %D)
9. compute_bbands returns upper, middle, lower bands — ✅ Done (SMA ± std_dev * σ, verified upper > middle > lower)
10. compute_atr correctly calculates average true range — ✅ Done (true_range with Wilder's smoothing)
11. compute_adx correctly calculates average directional index — ✅ Done (shared _compute_directional_movement with +DM/-DM/TR, Wilder's smoothing)
12. compute_obv correctly calculates on-balance volume — ✅ Done (cumulative: +volume on up, -volume on down)
13. All indicator functions return None when bars are insufficient (never raise) — ✅ Done (all functions wrapped in try/except, return None; verified compute_sma(bars[:5], 20) → None)
14. All indicator functions use Decimal arithmetic (not float) — ✅ Done (all Decimal(str(...)) conversions, Decimal arithmetic throughout)
15. Derived price sources (hl2, hlc3, ohlc4) work in source parameters — ✅ Done (get_source_value handles all 7 source types, verified hlc3)
16. Multi-output indicators return dict with named outputs — ✅ Done (macd → {macd_line, signal_line, histogram}, stochastic → {k, d}, bbands → {upper, middle, lower}, keltner → {upper, middle, lower})

### Condition Engine
17. ConditionEngine evaluates single conditions correctly — ✅ Done (verified: close > 100 → True)
18. ConditionEngine evaluates AND groups (all must be true) — ✅ Done (verified: close>100 AND rsi>50 → True)
19. ConditionEngine evaluates OR groups (at least one true) — ✅ Done (verified: close<50 OR rsi>50 → True)
20. ConditionEngine supports nested groups (AND containing OR, etc.) — ✅ Done (verified: AND[close>100, OR[rsi>70, close<50]] → True)
21. Comparison operators work: greater_than, less_than, greater_than_or_equal, less_than_or_equal, equal — ✅ Done (all 5 verified)
22. Crossover operators work: crosses_above, crosses_below — ✅ Done (_resolve_series computes current + previous, verified with crossing bar data)
23. Range operators work: between, outside — ✅ Done (between 120-140 → True for close=129, outside 0-50 → True for close=129)
24. Indicator computation is cached within a single evaluation cycle (deduplicated) — ✅ Done (cache_key includes indicator key, params, output, bar count; cleared per evaluate() call)
25. Conditions return False (not crash) when data is insufficient or invalid — ✅ Done (verified: sma(period=200) with 5 bars → False)

### Formula Parser
26. Tokenizer breaks expressions into correct token types — ✅ Done (NUMBER, IDENTIFIER, OPERATOR, LPAREN, RPAREN, COMMA, EOF)
27. Parser builds AST from tokens with correct operator precedence — ✅ Done (recursive descent with precedence: or < and < comparison < add/sub < mul/div)
28. Evaluator computes results from AST using bar data — ✅ Done (Evaluator class walks AST, resolves identifiers/functions/operators)
29. Indicator functions work in expressions: sma(close, 20), rsi(14), etc. — ✅ Done (smart arg mapping: identifiers matching select options → source param, numbers → numeric params)
30. Bar field references work: open, high, low, close, volume — ✅ Done (IdentifierNode resolved via get_source_value)
31. Arithmetic works: +, -, *, /, % — ✅ Done (verified: close + 1 = 130, (close - open) * 2)
32. Grouping with parentheses works — ✅ Done (LPAREN → recursive parse → RPAREN)
33. Math functions work: abs(), min(), max() — ✅ Done (verified: abs(-5)=5, max(close,open)=129)
34. validate() returns clear error messages for invalid expressions — ✅ Done (forbidden construct messages, parse error messages with position)
35. Parser does NOT use eval(), exec(), or ast.literal_eval() — ✅ Done (custom Tokenizer → Parser → Evaluator)
36. Parser rejects variable assignment, loops, imports, function definitions — ✅ Done (_FORBIDDEN set: import, exec, eval, lambda, for, while, class, def, etc.)

### API and Integration
37. GET /api/v1/strategies/indicators returns full indicator catalog — ✅ Done (returns 26 IndicatorDefinitionSchema items in data envelope)
38. POST /api/v1/strategies/formulas/validate validates and returns errors — ✅ Done (returns FormulaValidationResponse with valid bool and errors list)
39. Strategy error classes exist and are registered in common error mapping — ✅ Done (7 error classes in errors.py, 6 new codes in _ERROR_STATUS_MAP)
40. StrategyConfig extracts settings from global Settings — ✅ Done (runner_check_interval, auto_pause_error_threshold, evaluation_timeout, max_concurrent_evaluations, etc.)
41. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- Formula parser convention `sma(close, 20)` means source=close, period=20. The evaluator uses smart arg mapping: IdentifierNode args matching a select param's options are mapped as string values to that param, while numeric args are mapped positionally to int/float params. This matches standard TA formula syntax.
- Bollinger Bands standard deviation uses population variance (divide by N, not N-1), which is the standard convention for Bollinger Bands in trading.
- The `prev()` function creates a sub-evaluator with truncated bars, which is slightly less efficient than maintaining a previous-bar cache but simpler and correct.
- Crossover detection in the condition engine saves/restores the computation cache when computing previous values, to prevent cache pollution between current and previous bar evaluations.
- The `open` bar field is excluded from the forbidden constructs check (Python's `open()` builtin is in the forbidden list, but `open` as a bar field identifier is allowed).

## Ambiguities Encountered
None — task and specs were unambiguous for all deliverables.

## Dependencies Discovered
None — all dependencies were available.

## Tests Created
None — not required by this task. Verified functionality through comprehensive import checks, indicator computation tests (SMA, EMA, RSI, MACD, BBands, ATR, Stochastic, CCI, MFI, Williams %R, OBV, ADX, Keltner, all price references), formula parser tests (arithmetic, functions, bar fields, validation, safety rejection), and condition engine tests (all operators, AND/OR, nested groups, crossover, range, caching, insufficient data).

## Risks or Concerns
- The directional movement computation (_compute_directional_movement) is shared between ADX, +DI, and -DI. If called separately for each in the same evaluation, the computation runs three times. The condition engine's caching mitigates this when used through conditions, but direct calls from formulas may recompute.
- Decimal.sqrt() used in Bollinger Bands may have precision limits for very small or very large variances. In practice, price data keeps this in reasonable ranges.
- The formula parser's forbidden construct check is word-level (splits on spaces and parens). Constructs like `import` embedded in longer identifiers (e.g., `my_import_fn`) would not be caught, but would fail at the function whitelist check instead.

## Deferred Items
None — all deliverables complete.

## Recommended Next Task
TASK-009 — Strategy module: strategy CRUD, validation, lifecycle, and runner. The computational engine (indicators, conditions, formulas) is now in place.
