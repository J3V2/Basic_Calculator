# calculator.py
import ast
import keyword
import re
from expr_eval import ExpressionEvaluator
# from calc_core import format_result  # optional: reuse formatting function

NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
# we'll also deny names that collide with allowed function names below
DENY = set(['ans'])

evaluator = ExpressionEvaluator(allow_ans=True)


def is_valid_name(name: str, deny: set):
    if not NAME_RE.match(name):
        return False, "Variable names must start with a letter or underscore and contain only letters, digits, or underscores."
    if keyword.iskeyword(name):
        return False, f"'{name}' is a Python keyword and cannot be used as a variable name."
    if name in deny:
        return False, f"'{name}' is reserved and cannot be used as a variable name."
    return True, ""


def process_input(raw: str, state: dict, evaluator: ExpressionEvaluator):
    """
    Process raw user input.
    state: dict with keys: 'ans' (number or None), 'vars' (dict), 'history' (list)
    Returns (ok: bool, message: str, state: dict)
    """
    raw = raw.strip()

    # commands
    if raw.lower() in ("q", "exit"):
        raise SystemExit("Goodbye!")
    if raw.lower() == "history":
        if not state['history']:
            return True, "No history yet.", state
        return True, "\n".join(f"{i+1}: {line}" for i, line in enumerate(state['history'])), state
    if raw.lower() == "clear":
        state['history'].clear()
        state['vars'].clear()
        state['ans'] = None
        return True, "History and variables cleared. ans reset.", state
    if raw.lower() == "help":
        names = sorted(list(evaluator.allowed_names.keys()))
        return True, "Allowed functions/constants: " + ", ".join(names) + "\nCommands: history, clear, help, q/exit", state

    # detect assignment using AST parsing (more robust than splitting on '=')
    try:
        node = ast.parse(raw, mode='exec')
    except SyntaxError:
        # maybe it's an expression; try eval below
        node = None

    if node is not None and len(node.body) == 1 and isinstance(node.body[0], ast.Assign):
        assign = node.body[0]
        # only allow single-target simple assignments: name = expr
        if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
            return False, "Only simple assignments of the form: name = expression are allowed.", state
        name = assign.targets[0].id
        # deny names that collide with allowed function names or 'ans'
        deny = set(evaluator.allowed_names.keys()) | DENY
        ok, msg = is_valid_name(name, deny)
        if not ok:
            return False, msg, state
        # Evaluate RHS by extracting source after '=' (quick, robust enough)
        rhs = raw.split("=", 1)[1].strip()
        try:
            val = evaluator.eval(
                rhs, ans=state['ans'], variables=state['vars'])
        except Exception as e:
            return False, f"Error evaluating right-hand side: {e}", state
        # store numeric variables only
        if not isinstance(val, (int, float)):
            return False, "Assigned value must be numeric", state
        state['vars'][name] = val
        line = f"{name} = {val}"
        state['history'].append(line)
        state['ans'] = val
        return True, line, state

    # otherwise, try to evaluate as an expression
    try:
        val = evaluator.eval(raw, ans=state['ans'], variables=state['vars'])
    except Exception as e:
        return False, f"Error: {e}", state

    # numeric result: update session
    state['ans'] = val
    # store a readable history line; we don't have the original operator formatting here,
    # so we append the raw expression + = result
    line = f"{raw} = {val}"
    state['history'].append(line)
    return True, line, state


def main():
    # session state
    state = {"ans": None, "vars": {}, "history": []}

    print("Welcome to Basic Calculator (expression mode). Type 'help' for allowed functions.")
    try:
        while True:
            raw = input(">>> ").strip()
            if not raw:
                continue
            ok, msg, state = process_input(raw, state, evaluator)
            # print output or error message
            print(msg)
    except SystemExit as e:
        print(e)
    except KeyboardInterrupt:
        print("\nInterrupted — Goodbye!")


if __name__ == "__main__":
    main()
