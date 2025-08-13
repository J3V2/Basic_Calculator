# calculator.py
from calc_core import operator, format_result


def get_number(prompt, ans=None):
    while True:
        s = input(prompt).strip()
        if s.lower() == "ans":
            if ans is None:
                print("No previous answer yet.")
                continue
            return ans
        try:
            return float(s)
        except ValueError:
            print("Enter a valid number or 'ans'.")


def main():
    ans = None
    history = []
    while True:
        a = get_number("Enter First Number (or 'ans'): ", ans)
        op = input("Enter Operator (+ - * / ** ^ %): ").strip()
        if op.lower() in ("q", "exit"):
            print("Goodbye!")
            break
        b = get_number("Enter Second Number (or 'ans'): ", ans)

        try:
            actual_op = "**" if op == "^" else op
            res = operator(a, b, actual_op)
        except Exception as e:
            print(f"Error: {e}")
            continue

        display_op = "^" if actual_op == "**" else actual_op
        print(format_result(a, b, display_op, res))
        # update session
        ans = res
        history.append(format_result(a, b, display_op, res))


if __name__ == "__main__":
    main()
