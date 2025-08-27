# calculator.py
import argparse
import ast
import csv
import datetime
import json
import os
import pathlib
import keyword
import re
import sys
from decimal import Decimal
from typing import Dict

from expr_eval import ExpressionEvaluator

# Session persistence path
SESSION_PATH = os.path.join(
    pathlib.Path.home(), ".basic_calculator", "session.json")
os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)

NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

# initialize evaluator and possibly load plugins
evaluator = ExpressionEvaluator(allow_ans=True)


def load_plugins(plugins_dir="plugins"):
    """Load plugin modules from 'plugins' directory. Each plugin should define register(mapping)."""
    if not os.path.isdir(plugins_dir):
        return
    sys.path.insert(0, plugins_dir)
    for fname in os.listdir(plugins_dir):
        if not fname.endswith(".py"):
            continue
        modname = fname[:-3]
        try:
            mod = __import__(modname)
            if hasattr(mod, "register") and callable(mod.register):
                mod.register(evaluator.allowed_names)
                print(f"[plugin] registered {modname}")
        except Exception as e:
            print(f"[plugin] failed to load {modname}: {e}")
    sys.path.pop(0)


def save_session(state: dict, path=SESSION_PATH):
    """Serialize state (convert Decimal to str)."""
    s = {
        "ans": str(state["ans"]) if isinstance(state.get("ans"), Decimal) else state.get("ans"),
        "vars": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in state["vars"].items()},
        "history": [
            {"expr": h["expr"], "result": (str(h["result"]) if isinstance(h["result"], Decimal) else h["result"]),
             "time": h["time"]} for h in state["history"]
        ],
        "memory": (str(state["memory"]) if isinstance(state["memory"], Decimal) else state["memory"]),
        "mode": state["mode"]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


def load_session(path=SESSION_PATH) -> dict:
    if not os.path.exists(path):
        return {"ans": None, "vars": {}, "history": [], "memory": 0.0, "mode": "float", "_undo": []}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    def maybe_decimal(x):
        try:
            return Decimal(x)
        except Exception:
            return x
    vars_parsed = {}
    for k, v in raw.get("vars", {}).items():
        vars_parsed[k] = maybe_decimal(v)
    hist = []
    for h in raw.get("history", []):
        res = maybe_decimal(h.get("result"))
        hist.append(
            {"expr": h.get("expr"), "result": res, "time": h.get("time")})
    mem = maybe_decimal(raw.get("memory", 0.0))
    ans = maybe_decimal(raw.get("ans"))
    mode = raw.get("mode", "float")
    return {"ans": ans, "vars": vars_parsed, "history": hist, "memory": mem, "mode": mode, "_undo": []}


def export_history_csv(state: dict, filename: str):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "expr", "result", "time"])
        for i, h in enumerate(state["history"], 1):
            writer.writerow([i, h["expr"], h["result"], h["time"]])


def is_valid_name(name: str, deny: set):
    if not NAME_RE.match(name):
        return False, "Variable names must start with a letter or underscore and contain only letters, digits, or underscores."
    if keyword.iskeyword(name):
        return False, f"'{name}' is a Python keyword and cannot be used as a variable name."
    if name in deny:
        return False, f"'{name}' is reserved and cannot be used as a variable name."
    return True, ""


# Undo helpers: we store deltas so undo is cheap
def push_undo(state: dict, kind: str, payload: dict):
    # payload is feature-specific
    state["_undo"].append({"kind": kind, "payload": payload})
    # limit undo depth
    if len(state["_undo"]) > 100:
        state["_undo"].pop(0)


def undo(state: dict):
    if not state["_undo"]:
        return False, "Nothing to undo."
    last = state["_undo"].pop()
    kind = last["kind"]
    p = last["payload"]
    if kind == "assign":
        name = p["name"]
        if p["existed"]:
            state["vars"][name] = p["old"]
        else:
            state["vars"].pop(name, None)
        # remove last history entry if it was the assignment
        if state["history"] and state["history"][-1].get("expr") == p.get("line"):
            state["history"].pop()
        return True, f"Reverted assignment '{name}'."
    if kind == "calc":
        state["ans"] = p["old_ans"]
        # remove last history
        if state["history"]:
            state["history"].pop()
        return True, "Reverted last calculation."
    if kind == "memory":
        state["memory"] = p["old"]
        return True, "Memory restored."
    return False, "Unknown undo kind."


def process_input(raw: str, state: dict, evaluator: ExpressionEvaluator):
    raw = raw.strip()
    if not raw:
        return True, None, state

    # commands
    cmd = raw.lower()
    if cmd in ("q", "exit"):
        raise SystemExit("Goodbye!")
    if cmd == "history":
        if not state["history"]:
            return True, "No history yet.", state
        return True, "\n".join(f"{i+1}: {h['expr']} = {h['result']}" for i, h in enumerate(state["history"])), state
    if cmd == "clear":
        state["history"].clear()
        state["vars"].clear()
        state["ans"] = None
        state["memory"] = Decimal(0) if state["mode"] == "decimal" else 0.0
        state["_undo"].clear()
        return True, "History and variables cleared. ans & memory reset.", state
    if cmd == "help":
        names = sorted(list(evaluator.allowed_names.keys()))
        info = ("Commands: history, clear, export history <file>, undo, help, mode <float|decimal>, "
                "m+ m- mr mc, save, load, q/exit\nAllowed functions/constants (float mode):\n" + ", ".join(names))
        return True, info, state

    # memory commands (m+, m-, mr, mc)
    if cmd in ("m+", "mem+", "memory+"):
        if state["ans"] is None:
            return False, "No current ans to add to memory.", state
        push_undo(state, "memory", {"old": state["memory"]})
        if state["mode"] == "decimal":
            state["memory"] = (state["memory"] if isinstance(
                state["memory"], Decimal) else Decimal(state["memory"])) + Decimal(str(state["ans"]))
        else:
            state["memory"] = float(state["memory"]) + float(state["ans"])
        return True, f"Memory = {state['memory']}", state
    if cmd in ("m-", "mem-", "memory-"):
        if state["ans"] is None:
            return False, "No current ans to subtract from memory.", state
        push_undo(state, "memory", {"old": state["memory"]})
        if state["mode"] == "decimal":
            state["memory"] = (state["memory"] if isinstance(
                state["memory"], Decimal) else Decimal(state["memory"])) - Decimal(str(state["ans"]))
        else:
            state["memory"] = float(state["memory"]) - float(state["ans"])
        return True, f"Memory = {state['memory']}", state
    if cmd in ("mr", "memory", "recall"):
        return True, f"Memory = {state['memory']}", state
    if cmd in ("mc",):
        push_undo(state, "memory", {"old": state["memory"]})
        state["memory"] = Decimal(0) if state["mode"] == "decimal" else 0.0
        return True, "Memory cleared.", state

    # export history
    if cmd.startswith("export history"):
        parts = raw.split(None, 2)
        if len(parts) < 3:
            return False, "Usage: export history <filename.csv>", state
        filename = parts[2].strip()
        try:
            export_history_csv(state, filename)
        except Exception as e:
            return False, f"Failed to write file: {e}", state
        return True, f"History exported to {filename}", state

    # mode switch
    if cmd.startswith("mode "):
        _, m = raw.split(None, 1)
        m = m.strip().lower()
        if m not in ("float", "decimal"):
            return False, "Mode must be 'float' or 'decimal'.", state
        state["mode"] = m
        return True, f"Mode set to {m}. (Note: functions disabled in decimal mode)", state

    # undo
    if cmd == "undo":
        ok, msg = undo(state)
        return ok, msg, state

    # save/load (manual)
    if cmd == "save":
        save_session(state)
        return True, f"Session saved to {SESSION_PATH}", state
    if cmd == "load":
        loaded = load_session()
        state.update(loaded)
        return True, "Session loaded.", state

    # assignment detection: try AST exec and check for Assign
    try:
        node = ast.parse(raw, mode="exec")
    except SyntaxError:
        node = None

    if node is not None and len(node.body) == 1 and isinstance(node.body[0], ast.Assign):
        assign = node.body[0]
        if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
            return False, "Only simple assignments 'name = expr' are allowed.", state
        name = assign.targets[0].id
        deny = set(evaluator.allowed_names.keys()) | {"ans"}
        ok, msg = is_valid_name(name, deny)
        if not ok:
            return False, msg, state
        rhs = raw.split("=", 1)[1].strip()
        try:
            val = evaluator.eval(rhs, ans=state["ans"], variables=state["vars"], decimal=(
                state["mode"] == "decimal"))
        except Exception as e:
            return False, f"Error evaluating RHS: {e}", state
        if not isinstance(val, (int, float, Decimal)):
            return False, "Assigned value must be numeric", state
        existed = name in state["vars"]
        old = state["vars"].get(name)
        push_undo(state, "assign", {
                  "name": name, "existed": existed, "old": old, "line": raw})
        state["vars"][name] = val
        state["ans"] = val
        entry = {"expr": raw, "result": val,
                 "time": datetime.datetime.now(datetime.UTC).isoformat()}
        state["history"].append(entry)
        return True, f"{name} = {val}", state

    # not assignment: evaluate expression using evaluator
    try:
        val = evaluator.eval(raw, ans=state["ans"], variables=state["vars"], decimal=(
            state["mode"] == "decimal"))
    except Exception as e:
        return False, f"Error: {e}", state

    # record calc delta for undo
    old_ans = state["ans"]
    push_undo(state, "calc", {"old_ans": old_ans})
    state["ans"] = val
    entry = {"expr": raw, "result": val,
             "time": datetime.datetime.now(datetime.UTC).isoformat()}
    state["history"].append(entry)
    return True, f"{raw} = {val}", state


def run_repl(initial_state: dict, args):
    state = initial_state
    # load plugins (optional)
    load_plugins()
    print("Basic Calculator (type 'help' for commands).")
    try:
        while True:
            try:
                raw = input(">>> ").strip()
            except EOFError:
                break
            if not raw:
                continue
            ok, msg, state = process_input(raw, state, evaluator)
            if msg:
                print(msg)
    except SystemExit as e:
        print(e)
    finally:
        # autosave on exit
        try:
            save_session(state)
            print(f"Session saved to {SESSION_PATH}")
        except Exception as e:
            print(f"Failed to save session: {e}")


def run_expr_mode(expr: str, state: dict):
    state_local = state.copy()
    ok, msg, state_local = process_input(expr, state_local, evaluator)
    if not ok:
        print(msg)
        sys.exit(2)
    print(msg)


def run_file_mode(path: str, state: dict):
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip()
                 for l in f if l.strip() and not l.strip().startswith("#")]
    for line in lines:
        ok, msg, state = process_input(line, state, evaluator)
        if not ok:
            print(f"Error processing '{line}': {msg}")
        else:
            print(msg)
    # autosave after file processing
    save_session(state)


def main():
    parser = argparse.ArgumentParser(
        description="Basic Calculator (safe evaluator)")
    parser.add_argument("--expr", "-e", help="Evaluate expression and exit")
    parser.add_argument(
        "--file", "-f", help="Evaluate expressions from file (one per line)")
    args = parser.parse_args()

    initial_state = load_session()
    # Run a single expression and exit
    if args.expr:
        run_expr_mode(args.expr, initial_state)
        return
    if args.file:
        run_file_mode(args.file, initial_state)
        return

    run_repl(initial_state, args)


if __name__ == "__main__":
    main()
