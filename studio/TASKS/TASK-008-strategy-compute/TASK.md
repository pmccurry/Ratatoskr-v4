# TASK-008 — Strategy: Indicator Library, Condition Engine, and Formula Parser

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the computational core of the strategy module: the full indicator
library, the condition evaluation engine, and the formula expression parser.

After this task:
- All ~25 MVP indicators are implemented as pure functions
- The condition engine evaluates condition groups (AND/OR with nesting)
  against computed indicator values
- The formula parser tokenizes, parses, and safely evaluates custom
  expressions using indicators and bar data
- Crossover detection works (crosses_above, crosses_below)
- The indicator catalog is exposed via API endpoint for the frontend
  to dynamically build the strategy builder UI
- Indicator computation is deduplicated within a single evaluation cycle

This task implements the COMPUTATIONAL ENGINE only. No strategy CRUD,
no database models (strategies table), no runner, no lifecycle management,
no safety monitor. Those come in TASK-009.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/strategy_module_spec.md — PRIMARY SPEC, sections 2 (indicator library), 3 (formula parser), 4 (condition engine)
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions
6. /studio/SPECS/market_data_module_spec.md — bar data format (OHLCVBar fields) for indicator input

## Constraints

- Do NOT create database models for strategies (no Strategy, StrategyConfig tables)
- Do NOT implement strategy CRUD, lifecycle, or runner
- Do NOT implement the safety monitor
- Do NOT implement signal generation
- Do NOT create models or logic for any other module
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- All indicator functions are pure — they take bar data in, return computed values out
- All indicator functions are stateless — full lookback window provided each call
- All financial computations use Decimal
- The formula parser must NOT support arbitrary Python execution

---

## Deliverables

### 1. Indicator Registry (backend/app/strategies/indicators/registry.py)

Central registry of all available indicators with metadata.

```python
@dataclass
class IndicatorParam:
    """Definition of a single parameter for an indicator."""
    name: str
    type: str              # "int" | "float" | "select"
    default: Any
    min: float | None = None
    max: float | None = None
    options: list[str] | None = None  # for select type

@dataclass
class IndicatorDefinition:
    """Full definition of a registered indicator."""
    key: str               # e.g., "rsi", "ema", "bbands"
    name: str              # human-readable name
    category: str          # "trend" | "momentum" | "volatility" | "volume" | "trend_strength" | "price_reference"
    params: list[IndicatorParam]
    outputs: list[str]     # e.g., ["number"] or ["upper", "middle", "lower"]
    description: str
    compute_fn: Callable   # reference to the actual computation function

class IndicatorRegistry:
    """Registry of all available indicators."""
    
    def __init__(self):
        self._indicators: dict[str, IndicatorDefinition] = {}
    
    def register(self, definition: IndicatorDefinition) -> None:
        """Register an indicator."""
    
    def get(self, key: str) -> IndicatorDefinition | None:
        """Get indicator definition by key."""
    
    def list_all(self) -> list[IndicatorDefinition]:
        """List all registered indicators."""
    
    def list_by_category(self, category: str) -> list[IndicatorDefinition]:
        """List indicators in a category."""
    
    def exists(self, key: str) -> bool:
        """Check if an indicator is registered."""
```

Create a module-level singleton instance and a function that populates it
with all MVP indicators on first access.

### 2. Indicator Computation Functions (backend/app/strategies/indicators/compute.py)

Pure functions that take bar data and parameters, return computed values.

Input format for all functions:
```python
# bars is a list of dicts or objects with: open, high, low, close, volume
# All price values are Decimal
# The list is ordered chronologically (oldest first, newest last)
```

Output format: `Decimal` for single-output indicators, `dict[str, Decimal]`
for multi-output indicators.

**Implement ALL of these:**

**Trend (4):**
```python
def compute_sma(bars: list, period: int, source: str = "close") -> Decimal | None:
    """Simple Moving Average. Returns None if insufficient bars."""

def compute_ema(bars: list, period: int, source: str = "close") -> Decimal | None:
    """Exponential Moving Average.
    Multiplier = 2 / (period + 1)
    EMA = (value - prev_ema) * multiplier + prev_ema
    """

def compute_wma(bars: list, period: int, source: str = "close") -> Decimal | None:
    """Weighted Moving Average.
    Weight = position (1 for oldest, period for newest)
    WMA = sum(weight * value) / sum(weights)
    """

def compute_vwap(bars: list) -> Decimal | None:
    """Volume Weighted Average Price.
    VWAP = sum(typical_price * volume) / sum(volume)
    typical_price = (high + low + close) / 3
    """
```

**Momentum (6):**
```python
def compute_rsi(bars: list, period: int = 14, source: str = "close") -> Decimal | None:
    """Relative Strength Index.
    Avg gain = mean of gains over period
    Avg loss = mean of losses over period
    RS = avg_gain / avg_loss
    RSI = 100 - (100 / (1 + RS))
    Uses Wilder's smoothing after initial SMA.
    """

def compute_macd(bars: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, Decimal] | None:
    """MACD. Returns {"macd_line", "signal_line", "histogram"}
    macd_line = EMA(fast) - EMA(slow)
    signal_line = EMA(signal) of macd_line
    histogram = macd_line - signal_line
    """

def compute_stochastic(bars: list, k_period: int = 14, d_period: int = 3, slowing: int = 3) -> dict[str, Decimal] | None:
    """Stochastic Oscillator. Returns {"k", "d"}
    %K = SMA(slowing) of raw_k
    raw_k = (close - lowest_low(k_period)) / (highest_high(k_period) - lowest_low(k_period)) * 100
    %D = SMA(d_period) of %K
    """

def compute_cci(bars: list, period: int = 20) -> Decimal | None:
    """Commodity Channel Index.
    typical_price = (high + low + close) / 3
    CCI = (typical_price - SMA(typical_price, period)) / (0.015 * mean_deviation)
    """

def compute_mfi(bars: list, period: int = 14) -> Decimal | None:
    """Money Flow Index.
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume
    MFI = 100 - (100 / (1 + positive_flow / negative_flow))
    """

def compute_williams_r(bars: list, period: int = 14) -> Decimal | None:
    """Williams %R.
    %R = (highest_high - close) / (highest_high - lowest_low) * -100
    """
```

**Volatility (3):**
```python
def compute_bbands(bars: list, period: int = 20, std_dev: float = 2.0) -> dict[str, Decimal] | None:
    """Bollinger Bands. Returns {"upper", "middle", "lower"}
    middle = SMA(period)
    upper = middle + (std_dev * standard_deviation)
    lower = middle - (std_dev * standard_deviation)
    """

def compute_atr(bars: list, period: int = 14) -> Decimal | None:
    """Average True Range.
    true_range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    ATR = Wilder's smoothing of true_range over period
    """

def compute_keltner(bars: list, period: int = 20, atr_multiplier: float = 1.5) -> dict[str, Decimal] | None:
    """Keltner Channels. Returns {"upper", "middle", "lower"}
    middle = EMA(period)
    upper = middle + (atr_multiplier * ATR(period))
    lower = middle - (atr_multiplier * ATR(period))
    """
```

**Volume (3):**
```python
def compute_volume(bars: list) -> Decimal | None:
    """Raw bar volume. Returns latest bar's volume."""

def compute_volume_sma(bars: list, period: int = 20) -> Decimal | None:
    """SMA of volume."""

def compute_obv(bars: list) -> Decimal | None:
    """On Balance Volume.
    If close > prev_close: OBV += volume
    If close < prev_close: OBV -= volume
    If close == prev_close: OBV unchanged
    """
```

**Trend Strength (3):**
```python
def compute_adx(bars: list, period: int = 14) -> Decimal | None:
    """Average Directional Index. Uses Wilder's smoothing."""

def compute_plus_di(bars: list, period: int = 14) -> Decimal | None:
    """Plus Directional Indicator (+DI)."""

def compute_minus_di(bars: list, period: int = 14) -> Decimal | None:
    """Minus Directional Indicator (-DI)."""
```

**Price Reference (7):**
```python
def compute_close(bars: list) -> Decimal | None:
def compute_open(bars: list) -> Decimal | None:
def compute_high(bars: list) -> Decimal | None:
def compute_low(bars: list) -> Decimal | None:
def compute_prev_close(bars: list) -> Decimal | None:
def compute_prev_high(bars: list) -> Decimal | None:
def compute_prev_low(bars: list) -> Decimal | None:
```

**Helper for derived price sources:**
```python
def get_source_value(bar: dict, source: str) -> Decimal:
    """Extract a price source from a bar.
    source: "close" | "open" | "high" | "low" | "hl2" | "hlc3" | "ohlc4"
    hl2  = (high + low) / 2
    hlc3 = (high + low + close) / 3
    ohlc4 = (open + high + low + close) / 4
    """
```

**Important implementation notes:**
- All computations use `Decimal` arithmetic
- Functions return `None` when there are insufficient bars for the lookback
- Functions must never raise exceptions on bad data — return `None` instead
- Each function should document its minimum required bar count

### 3. Indicator Initialization (backend/app/strategies/indicators/__init__.py)

Import and register all indicators:

```python
from app.strategies.indicators.registry import IndicatorRegistry, IndicatorDefinition, IndicatorParam
from app.strategies.indicators.compute import *

# Create the global registry
registry = IndicatorRegistry()

# Register all indicators
registry.register(IndicatorDefinition(
    key="sma",
    name="Simple Moving Average",
    category="trend",
    params=[
        IndicatorParam("period", "int", default=20, min=2, max=500),
        IndicatorParam("source", "select", default="close", options=["close", "open", "high", "low", "hl2", "hlc3", "ohlc4"]),
    ],
    outputs=["number"],
    description="Average of the last N bars",
    compute_fn=compute_sma,
))
# ... register all other indicators

def get_registry() -> IndicatorRegistry:
    return registry
```

### 4. Indicator Schemas (backend/app/strategies/indicators/schemas.py)

Pydantic schemas for the indicator API endpoint response:

```python
class IndicatorParamSchema(BaseModel):
    name: str
    type: str
    default: Any
    min: float | None
    max: float | None
    options: list[str] | None

class IndicatorDefinitionSchema(BaseModel):
    key: str
    name: str
    category: str
    params: list[IndicatorParamSchema]
    outputs: list[str]
    description: str
```

Use camelCase aliases for JSON.

### 5. Condition Engine (backend/app/strategies/conditions/engine.py)

Evaluates condition groups against computed indicator values.

```python
class ConditionEngine:
    """Evaluates condition groups against bar data.
    
    Usage:
        engine = ConditionEngine(registry, formula_parser)
        result = engine.evaluate(condition_group, bars)
        # result: bool
    """
    
    def __init__(self, registry: IndicatorRegistry, formula_parser: FormulaParser):
        self._registry = registry
        self._parser = formula_parser
        self._cache: dict[str, Any] = {}  # indicator computation cache
    
    def evaluate(self, condition_group: dict, bars: list[dict]) -> bool:
        """Evaluate a condition group against bar data.
        
        1. Clear the computation cache (fresh per evaluation cycle)
        2. Recursively evaluate the condition group
        3. Return True if conditions are met, False otherwise
        """
    
    def _evaluate_group(self, group: dict, bars: list[dict]) -> bool:
        """Evaluate a condition group with AND/OR logic.
        
        group = {
            "logic": "and" | "or",
            "conditions": [condition | nested_group]
        }
        
        For "and": all conditions must be True
        For "or": at least one condition must be True
        
        Items in conditions list can be:
        - A condition dict (has "left", "operator", "right")
        - A nested group dict (has "logic", "conditions")
        """
    
    def _evaluate_condition(self, condition: dict, bars: list[dict]) -> bool:
        """Evaluate a single condition.
        
        condition = {
            "left": {"type": "indicator" | "formula", ...},
            "operator": str,
            "right": {"type": "value" | "indicator" | "formula" | "range", ...}
        }
        
        Steps:
        1. Resolve left side to a value (or series for crossover)
        2. Resolve right side to a value (or series, or range)
        3. Apply the operator
        4. Return bool
        """
    
    def _resolve_operand(self, operand: dict, bars: list[dict]) -> Decimal | None:
        """Resolve an operand to a numeric value.
        
        - type "indicator": compute from catalog (with caching)
        - type "formula": evaluate through formula parser
        - type "value": return the literal value as Decimal
        """
    
    def _resolve_series(self, operand: dict, bars: list[dict]) -> tuple[Decimal | None, Decimal | None]:
        """Resolve an operand to (current_value, previous_value).
        
        Needed for crossover operators.
        For indicators: compute on bars and bars[:-1]
        For formulas: evaluate on bars and bars[:-1]
        For values: (value, value) — constants don't change
        """
    
    def _compute_indicator(self, key: str, params: dict, output: str | None,
                           bars: list[dict]) -> Decimal | None:
        """Compute an indicator with caching.
        
        Cache key: (indicator_key, frozenset(params.items()), output)
        If cached, return cached value.
        If not, compute, extract output if multi-output, cache, return.
        """
    
    def _apply_operator(self, operator: str, left: Any, right: Any) -> bool:
        """Apply a comparison operator.
        
        Comparison operators (left and right are Decimal):
          greater_than, less_than, greater_than_or_equal,
          less_than_or_equal, equal
        
        Crossover operators (left and right are (current, previous) tuples):
          crosses_above, crosses_below
        
        Range operators (right is {"min": N, "max": N}):
          between, outside
        
        Returns False if either operand is None (insufficient data).
        """
```

### 6. Condition Schemas (backend/app/strategies/conditions/schemas.py)

Pydantic schemas for conditions used in strategy config validation:

```python
class OperandSchema(BaseModel):
    """Left or right side of a condition."""
    type: str  # "indicator" | "formula" | "value" | "range"
    indicator: str | None = None
    params: dict | None = None
    output: str | None = None
    expression: str | None = None
    value: Decimal | None = None
    min: Decimal | None = None  # for range type
    max: Decimal | None = None  # for range type

class ConditionSchema(BaseModel):
    """A single condition."""
    left: OperandSchema
    operator: str  # one of the supported operators
    right: OperandSchema

class ConditionGroupSchema(BaseModel):
    """A group of conditions with AND/OR logic."""
    logic: str  # "and" | "or"
    conditions: list[ConditionSchema | 'ConditionGroupSchema']
```

Use validators to ensure:
- operator is in the allowed set
- logic is "and" or "or"
- range type has min and max
- indicator type has indicator field
- formula type has expression field
- value type has value field

### 7. Formula Parser (backend/app/strategies/formulas/parser.py)

Safe expression parser that evaluates mathematical expressions
using indicators and bar data.

```python
class FormulaParser:
    """Parses and evaluates formula expressions.
    
    Supports:
    - Numbers: 42, 3.14
    - Arithmetic: +, -, *, /, %
    - Comparison: >, <, >=, <=, ==, !=
    - Logic: and, or, not
    - Grouping: ()
    - Functions: sma(), ema(), rsi(), etc. (all registered indicators)
    - Bar fields: open, high, low, close, volume
    - History: prev(expr), prev(expr, N)
    - Math: abs(), min(), max()
    - Crossover: crosses_above(a, b), crosses_below(a, b)
    
    Does NOT support:
    - Variable assignment
    - Loops, imports, function definitions
    - String operations (beyond symbol names in quotes)
    - Any Python builtins
    """
    
    def __init__(self, registry: IndicatorRegistry):
        self._registry = registry
        self._allowed_functions: set[str] = set()
        self._build_function_whitelist()
    
    def evaluate(self, expression: str, bars: list[dict]) -> Decimal | None:
        """Parse and evaluate an expression against bar data.
        
        Steps:
        1. Tokenize the expression
        2. Parse into AST
        3. Evaluate the AST against bar data
        4. Return the result as Decimal
        
        Returns None if evaluation fails (insufficient data, etc.)
        Never raises an exception for bad data — returns None.
        """
    
    def validate(self, expression: str) -> list[str]:
        """Validate an expression without evaluating it.
        
        Returns a list of error messages. Empty list = valid.
        
        Checks:
        - Syntax is valid (parentheses balanced, operators valid)
        - All function names are in the whitelist
        - Argument counts are correct
        - No forbidden constructs
        """
```

**Implementation approach:**

The parser should use a recursive descent or Pratt parser approach.
Do NOT use `eval()` or `exec()`. Do NOT use `ast.literal_eval()`.
Build a proper tokenizer and parser.

```python
class Tokenizer:
    """Tokenize a formula expression into tokens."""
    
    def tokenize(self, expression: str) -> list[Token]:
        """Break expression into tokens: NUMBER, IDENTIFIER, OPERATOR, LPAREN, RPAREN, COMMA, STRING"""

class Token:
    type: str  # NUMBER, IDENTIFIER, OPERATOR, LPAREN, RPAREN, COMMA, STRING
    value: str
    position: int  # for error messages

class ASTNode:
    """Base class for AST nodes."""

class NumberNode(ASTNode):
    value: Decimal

class BinaryOpNode(ASTNode):
    operator: str
    left: ASTNode
    right: ASTNode

class UnaryOpNode(ASTNode):
    operator: str
    operand: ASTNode

class FunctionCallNode(ASTNode):
    name: str
    args: list[ASTNode]

class IdentifierNode(ASTNode):
    name: str  # bar field reference: open, high, low, close, volume

class Parser:
    """Parse tokens into an AST using operator precedence."""
    
    def parse(self, tokens: list[Token]) -> ASTNode:
        """Parse the token stream into an AST."""

class Evaluator:
    """Evaluate an AST against bar data."""
    
    def __init__(self, registry: IndicatorRegistry, bars: list[dict]):
        self._registry = registry
        self._bars = bars
        self._cache: dict = {}
    
    def evaluate(self, node: ASTNode) -> Decimal | None:
        """Recursively evaluate an AST node."""
```

### 8. Formula Schemas (backend/app/strategies/formulas/schemas.py)

```python
class FormulaValidationRequest(BaseModel):
    expression: str

class FormulaValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
```

### 9. Strategy Errors (backend/app/strategies/errors.py)

```python
class StrategyNotFoundError(DomainError):
    # code: STRATEGY_NOT_FOUND, status: 404

class StrategyInvalidConfigError(DomainError):
    # code: STRATEGY_INVALID_CONFIG, status: 400

class StrategyEvaluationError(DomainError):
    # code: STRATEGY_EVALUATION_ERROR, status: 500

class FormulaParseError(DomainError):
    # code: STRATEGY_FORMULA_PARSE_ERROR, status: 400

class FormulaValidationError(DomainError):
    # code: STRATEGY_FORMULA_VALIDATION_ERROR, status: 400

class IndicatorNotFoundError(DomainError):
    # code: STRATEGY_INDICATOR_NOT_FOUND, status: 400

class InvalidConditionError(DomainError):
    # code: STRATEGY_INVALID_CONDITION, status: 400
```

Register all in common/errors.py error-to-status mapping.

### 10. Strategy Router — Indicator Endpoint (backend/app/strategies/router.py)

Replace the empty strategy router stub with the indicator catalog endpoint.
This endpoint is read by the frontend to dynamically render the strategy builder.

```
GET /api/v1/strategies/indicators → list of IndicatorDefinitionSchema
                                     (requires auth)
```

Also add formula validation endpoint:
```
POST /api/v1/strategies/formulas/validate → FormulaValidationRequest body
                                             → FormulaValidationResponse
                                             (requires auth)
```

### 11. Strategy Config (backend/app/strategies/config.py)

Extract strategy-specific settings from global Settings:

```python
class StrategyConfig:
    def __init__(self):
        s = get_settings()
        self.runner_check_interval = s.strategy_runner_check_interval_sec
        self.auto_pause_error_threshold = s.strategy_auto_pause_error_threshold
        self.evaluation_timeout = s.strategy_evaluation_timeout_sec
        self.max_concurrent_evaluations = s.strategy_max_concurrent_evaluations
        self.safety_monitor_check_interval = s.safety_monitor_check_interval_sec
        self.safety_monitor_failure_alert_threshold = s.safety_monitor_failure_alert_threshold
        self.global_kill_switch = s.safety_monitor_global_kill_switch
```

---

## Acceptance Criteria

### Indicator Library
1. IndicatorRegistry stores and retrieves indicator definitions by key
2. All 26 indicators are registered (4 trend + 6 momentum + 3 volatility + 3 volume + 3 trend strength + 7 price reference)
3. Each registration includes key, name, category, params with types/defaults/ranges, outputs, description, and compute function reference
4. compute_sma correctly calculates simple moving average
5. compute_ema correctly calculates exponential moving average with proper multiplier
6. compute_rsi correctly calculates RSI with Wilder's smoothing
7. compute_macd returns macd_line, signal_line, and histogram
8. compute_stochastic returns k and d values
9. compute_bbands returns upper, middle, lower bands
10. compute_atr correctly calculates average true range
11. compute_adx correctly calculates average directional index
12. compute_obv correctly calculates on-balance volume
13. All indicator functions return None when bars are insufficient (never raise)
14. All indicator functions use Decimal arithmetic (not float)
15. Derived price sources (hl2, hlc3, ohlc4) work in source parameters
16. Multi-output indicators return dict with named outputs

### Condition Engine
17. ConditionEngine evaluates single conditions correctly
18. ConditionEngine evaluates AND groups (all must be true)
19. ConditionEngine evaluates OR groups (at least one true)
20. ConditionEngine supports nested groups (AND containing OR, etc.)
21. Comparison operators work: greater_than, less_than, greater_than_or_equal, less_than_or_equal, equal
22. Crossover operators work: crosses_above, crosses_below (using current + previous values)
23. Range operators work: between, outside
24. Indicator computation is cached within a single evaluation cycle (deduplicated)
25. Conditions return False (not crash) when data is insufficient or invalid

### Formula Parser
26. Tokenizer breaks expressions into correct token types
27. Parser builds AST from tokens with correct operator precedence
28. Evaluator computes results from AST using bar data
29. Indicator functions work in expressions: sma(close, 20), rsi(14), etc.
30. Bar field references work: open, high, low, close, volume
31. Arithmetic works: +, -, *, /, %
32. Grouping with parentheses works
33. Math functions work: abs(), min(), max()
34. validate() returns clear error messages for invalid expressions
35. Parser does NOT use eval(), exec(), or ast.literal_eval()
36. Parser rejects variable assignment, loops, imports, function definitions

### API and Integration
37. GET /api/v1/strategies/indicators returns full indicator catalog
38. POST /api/v1/strategies/formulas/validate validates and returns errors
39. Strategy error classes exist and are registered in common error mapping
40. StrategyConfig extracts settings from global Settings
41. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-008-strategy-compute/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
