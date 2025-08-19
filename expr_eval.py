# expr_eval.py
import ast
import operator as _op
import math
from typing import Union, Optional

Number = Union[int, float]

# map AST operator types to Python functions
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

# default whitelist of allowed names (functions and constants)
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
    Safe evaluator for arithmetic expressions.
    Allowed: numeric literals (int, float), binary ops + - * / % **, unary +/-, parentheses,
    safe calls to whitelisted functions (from DEFAULT_ALLOWED_NAMES), and the name 'ans' (optional).
    """

    def __init__(self, allow_ans: bool = True, allowed_names: Optional[dict] = None):
        self.allow_ans = bool(allow_ans)
        # copy so callers can mutate their dict without affecting the class-level mapping
        self.allowed_names = (allowed_names.copy() if allowed_names is not None
                              else DEFAULT_ALLOWED_NAMES.copy())

    def eval(self, expression: str, ans: Optional[Number] = None) -> Number:
        if expression is None:
            raise ValueError("No expression provided")
        # friendly: allow '^' as exponent operator
        expression = expression.replace("^", "**")

        # parse to AST (mode='eval' ensures a single expression)
        try:
            node = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid expression: {e}")

        return self._eval_node(node.body, ans)

    def _eval_node(self, node: ast.AST, ans: Optional[Number]) -> Number:
        # Binary operations
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, ans)
            right = self._eval_node(node.right, ans)
            op_type = type(node.op)
            func = _BIN_OPS.get(op_type)
            if func is None:
                raise ValueError(
                    f"Unsupported binary operator: {op_type.__name__}")
            return func(left, right)

        # Unary operations + and -
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, ans)
            op_type = type(node.op)
            func = _UNARY_OPS.get(op_type)
            if func is None:
                raise ValueError(
                    f"Unsupported unary operator: {op_type.__name__}")
            return func(operand)

        # Function calls (sin(...), sqrt(...), etc.)
        if isinstance(node, ast.Call):
            # only allow direct names like sin(...)
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are allowed")
            fname = node.func.id
            if fname not in self.allowed_names or not callable(self.allowed_names[fname]):
                raise ValueError(f"Function '{fname}' is not allowed")
            # evaluate positional args only (no keywords)
            args = [self._eval_node(a, ans) for a in node.args]
            # let underlying function raise TypeError for wrong arity
            return self.allowed_names[fname](*args)

        # Numeric literal (Python 3.8+: ast.Constant)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric literals are allowed")

        # # For older Pythons (Num node)
        # if isinstance(node, ast.Num):  # type: ignore[name-defined]
        #     return node.n  # type: ignore[attr-defined]

        # Names: allow 'ans' (if enabled) and allowed constants (or function objects
        # if someone references them without calling them — calling them is done via ast.Call)
        if isinstance(node, ast.Name):
            if node.id == "ans" and self.allow_ans:
                if ans is None:
                    raise ValueError(
                        "No previous answer available (ans is None)")
                return ans
            if node.id in self.allowed_names:
                return self.allowed_names[node.id]
            raise ValueError(f"Use of name '{node.id}' is not allowed")

        # Disallow everything else
        raise ValueError(
            f"Unsupported expression element: {type(node).__name__}")
