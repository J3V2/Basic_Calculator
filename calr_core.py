# calc_core.py
# def operator(a, b, op):
#     op = op.strip()
#     if op == "+":
#         return a + b
#     if op == "-":
#         return a - b
#     if op == "*":
#         return a * b
#     if op == "/":
#         if b == 0:
#             raise ZeroDivisionError("division by zero")
#         return a / b
#     if op == "%":
#         if b == 0:
#             raise ZeroDivisionError("modulo by zero")
#         return a % b
#     if op in ("**", "^"):
#         return a ** b
#     raise ValueError(f"Invalid operator: {op}")


# def pretty_number(x):
#     if isinstance(x, float) and x.is_integer():
#         return int(x)
#     return x


def format_result(a, b, op, result):
    return f"{pretty_number(a)} {op} {pretty_number(b)} = {pretty_number(result)}"
