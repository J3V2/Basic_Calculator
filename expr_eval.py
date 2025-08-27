# expr_eval.py
import ast
import operator as _op
import math
from typing import Union, Optional, Dict
from decimal import Decimal, InvalidOperation

Number = Union[int, float, Decimal]

# AST operator map (works with Decimal if inputs are Decimal)
_BIN_OPS = {
    ast.Add: _op.add,
    ast.Sub: _op.sub,
    ast.Mult: _op.mul,
    ast.Div: _op.truediv,
    ast.Mod: _op.mod,
    ast.Pow: _op.pow,
}

_UNARY_OPS = {
    ast.UAdd: lambda x: +x,
    ast.USub: lambda x: -x,
}

# default whitelist of allowed names (functions and constants) for float mode
DEFAULT_ALLOWED_NAMES = {
    'pi': math.pi,
    'e': math.e,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sqrt': math.sqrt,
    'log': math.log,
    'log10': math.log10,
    'exp': math.exp,
    'floor': math.floor,
    'ceil': math.ceil,
    'abs': abs,
}


class ExpressionEvaluator:
    """
    Safe evaluator for arithmetic expressions. Features:
      - supports numeric literals, binary ops + - * / % **, unary +/-,
      - safe calls to whitelisted functions (float mode),
      - supports variables mapping and 'ans' token,
      - optional decimal mode (Decimal arithmetic) — in decimal mode functions are disabled.
    """

    def __init__(self, allow_ans: bool = True, allowed_names: Optional[Dict[str, object]] = None):
        self.allow_ans = bool(allow_ans)
        # use a copy so callers can add plugins safely
        self.allowed_names = (allowed_names.copy() if allowed_names is not None
                              else DEFAULT_ALLOWED_NAMES.copy())

    def register_names(self, mapping: Dict[str, object]):
        """Add or override allowed names (plugins can call this)."""
        self.allowed_names.update(mapping)

    def eval(self, expression: str, ans: Optional[Number] = None,
             variables: Optional[Dict[str, Number]] = None, decimal: bool = False) -> Number:
        """
        Evaluate expression string.
        - ans: optional numeric value to substitute for 'ans'
        - variables: dict name->numeric used for Name resolution
        - decimal: True -> use Decimal arithmetic (disables function calls)
        """
        if expression is None:
            raise ValueError("No expression provided")
        expression = expression.replace("^", "**")
        try:
            node = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid expression: {e}")

        vars_map = variables or {}
        return self._eval_node(node.body, ans, vars_map, decimal)

    def _to_number(self, value, decimal: bool) -> Number:
        """Convert Python literal to target numeric type when decimal=True."""
        if decimal:
            # Convert ints/floats to Decimal using string to avoid float binary issues
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int,)):
                return Decimal(value)
            if isinstance(value, float):
                return Decimal(str(value))
        return value

    def _eval_node(self, node: ast.AST, ans: Optional[Number],
                   variables: Dict[str, Number], decimal: bool) -> Number:
        # Binary
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, ans, variables, decimal)
            right = self._eval_node(node.right, ans, variables, decimal)
            # convert to Decimal if needed
            left = self._to_number(left, decimal)
            right = self._to_number(right, decimal)
            func = _BIN_OPS.get(type(node.op))
            if func is None:
                raise ValueError(
                    f"Unsupported binary operator: {type(node.op).__name__}")
            try:
                return func(left, right)
            except ZeroDivisionError:
                raise
            except Exception as e:
                raise ValueError(f"Error in binary operation: {e}")

        # Unary
        if isinstance(node, ast.UnaryOp):
            val = self._eval_node(node.operand, ans, variables, decimal)
            val = self._to_number(val, decimal)
            func = _UNARY_OPS.get(type(node.op))
            if func is None:
                raise ValueError(
                    f"Unsupported unary operator: {type(node.op).__name__}")
            return func(val)

        # Call (functions) — only allowed in float mode
        if isinstance(node, ast.Call):
            if decimal:
                raise ValueError("Function calls are disabled in decimal mode")
            # only simple names allowed as function (no attributes)
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are allowed")
            fname = node.func.id
            if fname not in self.allowed_names or not callable(self.allowed_names[fname]):
                raise ValueError(f"Function '{fname}' is not allowed")
            args = [self._eval_node(a, ans, variables, decimal)
                    for a in node.args]
            return self.allowed_names[fname](*args)

        # Constant
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return self._to_number(node.value, decimal)
            raise ValueError("Only numeric literals are allowed")

        # # For old Python: ast.Num
        # if isinstance(node, ast.Num):  # type: ignore[name-defined]
        #     # type: ignore[attr-defined]
        #     return self._to_number(node.n, decimal)

        # Name: variables take precedence, then ans, then allowed_names
        if isinstance(node, ast.Name):
            if node.id == "ans" and self.allow_ans:
                if ans is None:
                    raise ValueError(
                        "No previous answer available (ans is None)")
                return self._to_number(ans, decimal)
            if node.id in variables:
                val = variables[node.id]
                if not isinstance(val, (int, float, Decimal)):
                    raise ValueError(
                        f"Variable '{node.id}' does not hold a numeric value")
                return self._to_number(val, decimal)
            if node.id in self.allowed_names:
                return self.allowed_names[node.id]
            raise ValueError(f"Use of name '{node.id}' is not allowed")

        # Anything else is disallowed
        raise ValueError(
            f"Unsupported expression element: {type(node).__name__}")
