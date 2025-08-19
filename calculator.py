# calculator.py

from calc_core import operator, format_result
from expr_eval import ExpressionEvaluator

_evaluator = ExpressionEvaluator(allow_ans=True)


def get_number(prompt, ans=None):
    while True:
        s = input(prompt).strip()
        # allow quitting while entering a number
        if s.lower() in ("q", "exit"):
            raise SystemExit("Goodbye!")
        if s.lower() == "ans":
            if ans is None:
                print("No previous answer yet.")
                continue
            return ans
        # Try plain float first (fast friendly path)
        try:
            return float(s)
        except ValueError:
            # not a plain number — try expression evaluator
            try:
                val = _evaluator.eval(s, ans=ans)
                # Convert float-like integers to int for nicer display if desired:
                return int(val) if isinstance(val, float) and val.is_integer() else val
            except Exception as e:
                print("Invalid expression:", e)
                continue


def main():
    ans = None
    history = []

    try:
        while True:
            a = get_number("Enter First Number (or 'ans'): ", ans)

            op = input(
                "Enter Operator (+ - * / ** ^ %), or 'q' to quit: ").strip()
            if op.lower() in ("q", "exit"):
                print("Goodbye!")
                break

            b = get_number("Enter Second Number (or 'ans'): ", ans)

            try:
                actual_op = "**" if op == "^" else op
                res = operator(a, b, actual_op)
            except Exception as e:
                print(f"Error: {e}")
                # continue main loop (allows user to try again)
                continue

            display_op = "^" if actual_op == "**" else actual_op
            print(format_result(a, b, display_op, res))

            ans = res
            history.append(format_result(a, b, display_op, res))

            resp = input(
                "Press Enter to continue, or type 'q' to quit: ").strip().lower()
            if resp in ("q", "exit"):
                print("Goodbye!")
                break
    except SystemExit as e:
        print(e)


if __name__ == "__main__":
    main()
