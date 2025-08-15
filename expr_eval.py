# expr_eval.py
import ast
import operator as _op
from typing import Union

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


class ExpressionEvaluator:
    """
    Safe evaluator for arithmetic expressions.
    Allowed: literals (int, float), binary ops + - * / % **, unary +/-, parentheses.
    Optional: allow the name 'ans' to be used in expressions (if ans is provided).
    """

    def __init__(self, allow_ans: bool = True):
        self.allow_ans = allow_ans

    def eval(self, expression: str, ans: Number | None = None) -> Number:
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

    def _eval_node(self, node: ast.AST, ans: Number | None) -> Number:
        # Expression body might be a BinOp, UnaryOp, Constant, Name, etc.
        # Binary operations
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, ans)
            right = self._eval_node(node.right, ans)
            op_type = type(node.op)
            func = _BIN_OPS.get(op_type)
            if func is None:
                raise ValueError(
                    f"Unsupported binary operator: {op_type.__name__}")
            # let Python raise ZeroDivisionError naturally for div/mod by zero
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

        # Numeric literal (Python 3.8+: ast.Constant)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric literals are allowed")

        # For older Pythons (Num node)
        if isinstance(node, ast.Num):  # type: ignore[name-defined]
            return node.n  # type: ignore[attr-defined]

        # Allow the single safe name 'ans' if requested
        if isinstance(node, ast.Name):
            if node.id == "ans" and self.allow_ans:
                if ans is None:
                    raise ValueError(
                        "No previous answer available (ans is None)")
                return ans
            raise ValueError(f"Use of name '{node.id}' is not allowed")

        # Disallow everything else (calls, attributes, list, comprehensions, etc.)
        raise ValueError(
            f"Unsupported expression element: {type(node).__name__}")
