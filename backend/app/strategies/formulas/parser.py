"""Formula expression parser — tokenizer, AST, evaluator.

Safe expression evaluation using recursive descent parsing.
Does NOT use eval(), exec(), or ast.literal_eval().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.strategies.indicators.registry import IndicatorRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

TOKEN_NUMBER = "NUMBER"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_OPERATOR = "OPERATOR"
TOKEN_LPAREN = "LPAREN"
TOKEN_RPAREN = "RPAREN"
TOKEN_COMMA = "COMMA"
TOKEN_EOF = "EOF"

_OPERATORS = {"+", "-", "*", "/", "%", ">", "<", ">=", "<=", "==", "!="}
_KEYWORDS = {"and", "or", "not", "true", "false"}
_BAR_FIELDS = {"open", "high", "low", "close", "volume"}
_MATH_FUNCTIONS = {"abs", "min", "max"}
_SPECIAL_FUNCTIONS = {"prev", "crosses_above", "crosses_below"}

# Forbidden constructs
_FORBIDDEN = {
    "import", "exec", "eval", "compile", "open", "print", "input",
    "lambda", "class", "def", "for", "while", "if", "else", "elif",
    "try", "except", "finally", "with", "yield", "return", "raise",
    "del", "global", "nonlocal", "assert", "pass", "break", "continue",
    "__", "getattr", "setattr", "delattr", "globals", "locals", "vars",
}


@dataclass
class Token:
    type: str
    value: str
    position: int


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

class Tokenizer:
    """Tokenize a formula expression into tokens."""

    def tokenize(self, expression: str) -> list[Token]:
        tokens = []
        i = 0
        n = len(expression)

        while i < n:
            ch = expression[i]

            # Whitespace
            if ch.isspace():
                i += 1
                continue

            # Numbers (integer or decimal)
            if ch.isdigit() or (ch == "." and i + 1 < n and expression[i + 1].isdigit()):
                start = i
                while i < n and (expression[i].isdigit() or expression[i] == "."):
                    i += 1
                tokens.append(Token(TOKEN_NUMBER, expression[start:i], start))
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                start = i
                while i < n and (expression[i].isalnum() or expression[i] == "_"):
                    i += 1
                word = expression[start:i]
                tokens.append(Token(TOKEN_IDENTIFIER, word, start))
                continue

            # Two-character operators
            if i + 1 < n and expression[i : i + 2] in _OPERATORS:
                tokens.append(Token(TOKEN_OPERATOR, expression[i : i + 2], i))
                i += 2
                continue

            # Single-character operators
            if ch in {"+", "-", "*", "/", "%", ">", "<"}:
                tokens.append(Token(TOKEN_OPERATOR, ch, i))
                i += 1
                continue

            # Parentheses and comma
            if ch == "(":
                tokens.append(Token(TOKEN_LPAREN, "(", i))
                i += 1
                continue
            if ch == ")":
                tokens.append(Token(TOKEN_RPAREN, ")", i))
                i += 1
                continue
            if ch == ",":
                tokens.append(Token(TOKEN_COMMA, ",", i))
                i += 1
                continue

            # Unknown character
            raise _parse_error(f"Unexpected character '{ch}'", i)

        tokens.append(Token(TOKEN_EOF, "", n))
        return tokens


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

@dataclass
class ASTNode:
    """Base class for AST nodes."""
    pass


@dataclass
class NumberNode(ASTNode):
    value: Decimal


@dataclass
class BooleanNode(ASTNode):
    value: bool


@dataclass
class BinaryOpNode(ASTNode):
    operator: str
    left: ASTNode
    right: ASTNode


@dataclass
class UnaryOpNode(ASTNode):
    operator: str
    operand: ASTNode


@dataclass
class FunctionCallNode(ASTNode):
    name: str
    args: list[ASTNode]


@dataclass
class IdentifierNode(ASTNode):
    name: str  # bar field reference: open, high, low, close, volume


# ---------------------------------------------------------------------------
# Parser (recursive descent with operator precedence)
# ---------------------------------------------------------------------------

# Operator precedence (higher = binds tighter)
_PRECEDENCE = {
    "or": 1,
    "and": 2,
    "==": 3, "!=": 3,
    ">": 4, "<": 4, ">=": 4, "<=": 4,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "%": 6,
}


class Parser:
    """Parse tokens into an AST using operator precedence."""

    def __init__(self, tokens: list[Token], allowed_functions: set[str]):
        self._tokens = tokens
        self._pos = 0
        self._allowed = allowed_functions

    def parse(self) -> ASTNode:
        node = self._parse_expression(0)
        if self._current().type != TOKEN_EOF:
            raise _parse_error(
                f"Unexpected token '{self._current().value}'",
                self._current().position,
            )
        return node

    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, token_type: str) -> Token:
        tok = self._current()
        if tok.type != token_type:
            raise _parse_error(
                f"Expected {token_type}, got {tok.type} '{tok.value}'",
                tok.position,
            )
        return self._advance()

    def _parse_expression(self, min_prec: int) -> ASTNode:
        left = self._parse_unary()

        while True:
            tok = self._current()

            # Check for keyword operators (and, or)
            if tok.type == TOKEN_IDENTIFIER and tok.value in ("and", "or"):
                op = tok.value
            elif tok.type == TOKEN_OPERATOR:
                op = tok.value
            else:
                break

            prec = _PRECEDENCE.get(op)
            if prec is None or prec < min_prec:
                break

            self._advance()
            right = self._parse_expression(prec + 1)
            left = BinaryOpNode(operator=op, left=left, right=right)

        return left

    def _parse_unary(self) -> ASTNode:
        tok = self._current()

        # Unary minus
        if tok.type == TOKEN_OPERATOR and tok.value == "-":
            self._advance()
            operand = self._parse_unary()
            return UnaryOpNode(operator="-", operand=operand)

        # Unary not
        if tok.type == TOKEN_IDENTIFIER and tok.value == "not":
            self._advance()
            operand = self._parse_unary()
            return UnaryOpNode(operator="not", operand=operand)

        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._current()

        # Number literal
        if tok.type == TOKEN_NUMBER:
            self._advance()
            return NumberNode(value=Decimal(tok.value))

        # Boolean literals
        if tok.type == TOKEN_IDENTIFIER and tok.value == "true":
            self._advance()
            return BooleanNode(value=True)
        if tok.type == TOKEN_IDENTIFIER and tok.value == "false":
            self._advance()
            return BooleanNode(value=False)

        # Identifier (bar field or function call)
        if tok.type == TOKEN_IDENTIFIER:
            name = tok.value
            self._advance()

            # Function call
            if self._current().type == TOKEN_LPAREN:
                if name not in self._allowed:
                    raise _parse_error(
                        f"Unknown function '{name}'", tok.position
                    )
                self._advance()  # consume (
                args = self._parse_args()
                self._expect(TOKEN_RPAREN)
                return FunctionCallNode(name=name, args=args)

            # Bar field reference
            if name in _BAR_FIELDS:
                return IdentifierNode(name=name)

            # Could be a constant or indicator without parens — treat as identifier
            return IdentifierNode(name=name)

        # Grouped expression
        if tok.type == TOKEN_LPAREN:
            self._advance()
            node = self._parse_expression(0)
            self._expect(TOKEN_RPAREN)
            return node

        raise _parse_error(
            f"Unexpected token '{tok.value}'", tok.position
        )

    def _parse_args(self) -> list[ASTNode]:
        args = []
        if self._current().type == TOKEN_RPAREN:
            return args

        args.append(self._parse_expression(0))
        while self._current().type == TOKEN_COMMA:
            self._advance()
            args.append(self._parse_expression(0))

        return args


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class Evaluator:
    """Evaluate an AST against bar data."""

    def __init__(self, registry: IndicatorRegistry, bars: list):
        self._registry = registry
        self._bars = bars
        self._cache: dict[str, Decimal | None] = {}

    def evaluate(self, node: ASTNode) -> Decimal | None:
        """Recursively evaluate an AST node."""
        try:
            if isinstance(node, NumberNode):
                return node.value

            if isinstance(node, BooleanNode):
                return Decimal("1") if node.value else Decimal("0")

            if isinstance(node, IdentifierNode):
                return self._resolve_identifier(node.name)

            if isinstance(node, UnaryOpNode):
                return self._eval_unary(node)

            if isinstance(node, BinaryOpNode):
                return self._eval_binary(node)

            if isinstance(node, FunctionCallNode):
                return self._eval_function(node)

            return None
        except Exception:
            return None

    def _resolve_identifier(self, name: str) -> Decimal | None:
        """Resolve a bare identifier to a value."""
        from app.strategies.indicators.compute import get_source_value

        if not self._bars:
            return None

        bar = self._bars[-1]
        if name in _BAR_FIELDS:
            return get_source_value(bar, name)

        # Check if it's a registered indicator with no params
        defn = self._registry.get(name)
        if defn:
            cache_key = name
            if cache_key in self._cache:
                return self._cache[cache_key]
            result = defn.compute_fn(self._bars)
            if isinstance(result, dict):
                result = next(iter(result.values()), None)
            self._cache[cache_key] = result
            return result

        return None

    def _eval_unary(self, node: UnaryOpNode) -> Decimal | None:
        val = self.evaluate(node.operand)
        if val is None:
            return None
        if node.operator == "-":
            return -val
        if node.operator == "not":
            return Decimal("1") if val == 0 else Decimal("0")
        return None

    def _eval_binary(self, node: BinaryOpNode) -> Decimal | None:
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        if left is None or right is None:
            return None

        op = node.operator
        try:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    return None
                return left / right
            if op == "%":
                if right == 0:
                    return None
                return left % right
            if op == ">":
                return Decimal("1") if left > right else Decimal("0")
            if op == "<":
                return Decimal("1") if left < right else Decimal("0")
            if op == ">=":
                return Decimal("1") if left >= right else Decimal("0")
            if op == "<=":
                return Decimal("1") if left <= right else Decimal("0")
            if op == "==":
                return Decimal("1") if left == right else Decimal("0")
            if op == "!=":
                return Decimal("1") if left != right else Decimal("0")
            if op == "and":
                return Decimal("1") if (left != 0 and right != 0) else Decimal("0")
            if op == "or":
                return Decimal("1") if (left != 0 or right != 0) else Decimal("0")
        except Exception:
            return None

        return None

    def _eval_function(self, node: FunctionCallNode) -> Decimal | None:
        name = node.name

        # Math functions
        if name == "abs":
            if len(node.args) != 1:
                return None
            val = self.evaluate(node.args[0])
            return abs(val) if val is not None else None

        if name == "min":
            vals = [self.evaluate(a) for a in node.args]
            vals = [v for v in vals if v is not None]
            return min(vals) if vals else None

        if name == "max":
            vals = [self.evaluate(a) for a in node.args]
            vals = [v for v in vals if v is not None]
            return max(vals) if vals else None

        # prev(expr) or prev(expr, N)
        if name == "prev":
            if not node.args or len(self._bars) < 2:
                return None
            n = 1
            if len(node.args) > 1:
                n_val = self.evaluate(node.args[1])
                n = int(n_val) if n_val is not None else 1
            if n >= len(self._bars):
                return None
            prev_bars = self._bars[:-n]
            prev_eval = Evaluator(self._registry, prev_bars)
            return prev_eval.evaluate(node.args[0])

        # crosses_above(a, b) — returns 1 if a crossed above b
        if name == "crosses_above":
            if len(node.args) != 2 or len(self._bars) < 2:
                return None
            curr_a = self.evaluate(node.args[0])
            curr_b = self.evaluate(node.args[1])
            prev_eval = Evaluator(self._registry, self._bars[:-1])
            prev_a = prev_eval.evaluate(node.args[0])
            prev_b = prev_eval.evaluate(node.args[1])
            if None in (curr_a, curr_b, prev_a, prev_b):
                return None
            crossed = prev_a <= prev_b and curr_a > curr_b
            return Decimal("1") if crossed else Decimal("0")

        # crosses_below(a, b)
        if name == "crosses_below":
            if len(node.args) != 2 or len(self._bars) < 2:
                return None
            curr_a = self.evaluate(node.args[0])
            curr_b = self.evaluate(node.args[1])
            prev_eval = Evaluator(self._registry, self._bars[:-1])
            prev_a = prev_eval.evaluate(node.args[0])
            prev_b = prev_eval.evaluate(node.args[1])
            if None in (curr_a, curr_b, prev_a, prev_b):
                return None
            crossed = prev_a >= prev_b and curr_a < curr_b
            return Decimal("1") if crossed else Decimal("0")

        # Indicator function call
        defn = self._registry.get(name)
        if defn is None:
            return None

        # Build params from args with smart matching:
        # - IdentifierNode matching a select param's options → use as that param's string value
        # - NumberNode / evaluated Decimal → map to numeric params in order
        params = {}
        numeric_args = []  # (value,) for numeric args in order
        select_params = {
            p.name: p for p in defn.params if p.type == "select"
        }
        numeric_params = [p for p in defn.params if p.type in ("int", "float")]

        for arg_node in node.args:
            # Check if it's an identifier matching a select param's options
            matched_select = False
            if isinstance(arg_node, IdentifierNode):
                for sp_name, sp in select_params.items():
                    if sp_name not in params and sp.options and arg_node.name in sp.options:
                        params[sp_name] = arg_node.name
                        matched_select = True
                        break
            if not matched_select:
                val = self.evaluate(arg_node)
                if val is not None:
                    numeric_args.append(val)

        # Map numeric args to numeric params in order
        for i, np in enumerate(numeric_params):
            if np.name not in params and i < len(numeric_args):
                if np.type == "int":
                    params[np.name] = int(numeric_args[i])
                elif np.type == "float":
                    params[np.name] = float(numeric_args[i])

        # Apply defaults for missing params
        for pdef in defn.params:
            if pdef.name not in params:
                params[pdef.name] = pdef.default

        # Cache key
        cache_key = f"{name}:{sorted(params.items())}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = defn.compute_fn(self._bars, **params)

        # Extract single value from multi-output
        if isinstance(result, dict):
            # Default to first output
            if defn.outputs and defn.outputs[0] != "number":
                result = result.get(defn.outputs[0])
            else:
                result = next(iter(result.values()), None)

        self._cache[cache_key] = result
        return result


# ---------------------------------------------------------------------------
# FormulaParser — public API
# ---------------------------------------------------------------------------

class FormulaParser:
    """Parses and evaluates formula expressions.

    Supports:
    - Numbers, arithmetic (+, -, *, /, %), comparison (>, <, >=, <=, ==, !=)
    - Logic: and, or, not
    - Grouping: ()
    - Functions: all registered indicators, abs(), min(), max()
    - Bar fields: open, high, low, close, volume
    - History: prev(expr), prev(expr, N)
    - Crossover: crosses_above(a, b), crosses_below(a, b)

    Does NOT support: variable assignment, loops, imports, function definitions,
    arbitrary Python builtins.
    """

    def __init__(self, registry: IndicatorRegistry):
        self._registry = registry
        self._allowed_functions: set[str] = set()
        self._build_function_whitelist()

    def _build_function_whitelist(self) -> None:
        """Build the set of allowed function names."""
        # All registered indicators
        for defn in self._registry.list_all():
            self._allowed_functions.add(defn.key)

        # Built-in math functions
        self._allowed_functions |= _MATH_FUNCTIONS

        # Special functions
        self._allowed_functions |= _SPECIAL_FUNCTIONS

    def evaluate(self, expression: str, bars: list) -> Decimal | None:
        """Parse and evaluate an expression against bar data.

        Returns None if evaluation fails. Never raises.
        """
        try:
            tokens = Tokenizer().tokenize(expression)
            ast = Parser(tokens, self._allowed_functions).parse()
            evaluator = Evaluator(self._registry, bars)
            return evaluator.evaluate(ast)
        except Exception:
            return None

    def validate(self, expression: str) -> list[str]:
        """Validate an expression without evaluating it.

        Returns a list of error messages. Empty list = valid.
        """
        errors = []

        if not expression or not expression.strip():
            return ["Expression is empty"]

        # Check for forbidden constructs (exclude bar fields and indicator names)
        words = set(expression.replace("(", " ").replace(")", " ").split())
        for word in words:
            lower = word.lower()
            if lower in _BAR_FIELDS or lower in self._allowed_functions:
                continue
            if lower in _FORBIDDEN:
                errors.append(f"Forbidden construct: '{word}'")
            if "__" in word:
                errors.append(f"Dunder access not allowed: '{word}'")

        if errors:
            return errors

        # Try tokenizing
        try:
            tokens = Tokenizer().tokenize(expression)
        except ValueError as e:
            return [str(e)]

        # Try parsing
        try:
            Parser(tokens, self._allowed_functions).parse()
        except ValueError as e:
            return [str(e)]

        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_error(message: str, position: int) -> ValueError:
    return ValueError(f"Parse error at position {position}: {message}")
