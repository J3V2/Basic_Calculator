# calculator_gui.py
"""
Full-feature GUI for Basic Calculator.
Requires: expr_eval.py (ExpressionEvaluator)
Saves session to ~/.basic_calculator/session.json
Exports default to ~/.basic_calculator/exports/
"""

import os
import sys
import ast
import csv
import datetime
import json
import pathlib
import keyword
import re
from decimal import Decimal
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from tkinter.scrolledtext import ScrolledText
from expr_eval import ExpressionEvaluator

# ------------------------
# Paths / session / exports
# ------------------------
HOME_DIR = pathlib.Path.home()
SESSION_DIR = HOME_DIR / ".basic_calculator"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SESSION_PATH = SESSION_DIR / "session.json"

# Exports directory inside session folder (keeps project root clean)
EXPORTS_DIR = SESSION_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------
# Globals & evaluator
# ------------------------
NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
evaluator = ExpressionEvaluator(allow_ans=True)


# ------------------------
# Plugin loader
# ------------------------
def load_plugins(plugins_dir="plugins"):
    """Load plugin modules from 'plugins' directory. Each plugin should define register(mapping)."""
    plugins_path = pathlib.Path(plugins_dir)
    if not plugins_path.exists():
        return
    sys.path.insert(0, str(plugins_path.resolve()))
    for p in plugins_path.glob("*.py"):
        try:
            modname = p.stem
            mod = __import__(modname)
            if hasattr(mod, "register") and callable(mod.register):
                mod.register(evaluator.allowed_names)
                print(f"[plugin] registered {modname}")
        except Exception as e:
            print(f"[plugin] failed to load {p.name}: {e}")
    sys.path.pop(0)


# ------------------------
# Session persistence
# ------------------------
def save_session(state, path=SESSION_PATH):
    """Serialize state (convert Decimal to str)"""
    out = {
        "ans": str(state["ans"]) if isinstance(state.get("ans"), Decimal) else state.get("ans"),
        "vars": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in state["vars"].items()},
        "history": [
            {
                "expr": h["expr"],
                "result": (str(h["result"]) if isinstance(h["result"], Decimal) else h["result"]),
                "time": h["time"],
            }
            for h in state["history"]
        ],
        "memory": (str(state["memory"]) if isinstance(state["memory"], Decimal) else state["memory"]),
        "mode": state["mode"],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def load_session(path=SESSION_PATH):
    """Load session JSON and convert numeric strings back to Decimal when possible"""
    if not path.exists():
        return {"ans": None, "vars": {}, "history": [], "memory": 0.0, "mode": "float", "_undo": []}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    def maybe_decimal(x):
        try:
            return Decimal(x)
        except Exception:
            return x

    vars_parsed = {k: maybe_decimal(v) for k, v in raw.get("vars", {}).items()}
    hist = []
    for h in raw.get("history", []):
        hist.append({"expr": h.get("expr"), "result": maybe_decimal(
            h.get("result")), "time": h.get("time")})
    mem = maybe_decimal(raw.get("memory", 0.0))
    ans = maybe_decimal(raw.get("ans"))
    mode = raw.get("mode", "float")
    return {"ans": ans, "vars": vars_parsed, "history": hist, "memory": mem, "mode": mode, "_undo": []}


# ------------------------
# Export helper
# ------------------------
def export_history_csv(state, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "expr", "result", "time"])
        for i, h in enumerate(state["history"], 1):
            w.writerow([i, h["expr"], h["result"], h["time"]])


def auto_export_history(state, base_dir=EXPORTS_DIR, prefix="history"):
    """
    Auto-export history to a timestamped CSV in base_dir.
    Returns the path written. Raises on error.
    """
    base_dir = pathlib.Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H-%M-%S")
    base_name = f"{prefix}_{ts}.csv"
    path = base_dir / base_name
    counter = 1
    while path.exists():
        path = base_dir / f"{prefix}_{ts}_{counter}.csv"
        counter += 1
    export_history_csv(state, str(path))
    return str(path)


# ------------------------
# Utilities
# ------------------------
def is_valid_name(name, deny):
    if not NAME_RE.match(name):
        return False, "Variable names must start with a letter/underscore and contain letters/digits/underscore."
    if keyword.iskeyword(name):
        return False, "Name is a Python keyword."
    if name in deny:
        return False, f"'{name}' is reserved."
    return True, ""


# Undo stack: store small deltas to revert quickly
def push_undo(state, kind, payload):
    state["_undo"].append({"kind": kind, "payload": payload})
    if len(state["_undo"]) > 200:
        state["_undo"].pop(0)


def undo(state):
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
        if state["history"] and state["history"][-1].get("expr") == p.get("line"):
            state["history"].pop()
        return True, f"Reverted assignment '{name}'."
    if kind == "calc":
        state["ans"] = p["old_ans"]
        if state["history"]:
            state["history"].pop()
        return True, "Reverted last calculation."
    if kind == "memory":
        state["memory"] = p["old"]
        return True, "Memory restored."
    return False, "Unknown undo kind."


# ------------------------
# GUI application
# ------------------------
class CalculatorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basic Calculator")
        self.geometry("480x640")
        self.minsize(360, 480)

        # state
        self.state = load_session()
        # ensure _undo exists
        if "_undo" not in self.state:
            self.state["_undo"] = []
        # load plugins (if any)
        load_plugins()

        # build UI
        self._build_ui()
        self._bind_keys()
        self._refresh_result_display()

    def _build_ui(self):
        # Top entry & result
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=8, pady=8)

        self.expr_var = tk.StringVar()
        self.entry = ttk.Entry(
            top_frame, textvariable=self.expr_var, font=("Consolas", 16))
        self.entry.pack(fill="x", padx=4, pady=4)
        self.entry.focus_set()

        self.result_var = tk.StringVar(value="Ready")
        self.result_label = ttk.Label(
            top_frame, textvariable=self.result_var, anchor="e", font=("Consolas", 14))
        self.result_label.pack(fill="x", padx=4, pady=(0, 6))

        # Buttons grid
        btn_frame = ttk.Frame(self)
        btn_frame.pack(expand=True, fill="both", padx=8, pady=8)

        # define buttons layout (rows of labels)
        rows = [
            ["Ans", "(", ")", "C", "⌫"],
            ["sin(", "cos(", "tan(", "sqrt(", "log("],
            ["7", "8", "9", "/", "%"],
            ["4", "5", "6", "*", "^"],
            ["1", "2", "3", "-", "M+"],
            ["0", ".", "=", "+", "M-"],
            ["history", "export", "undo", "mode", "MR/MC"]
        ]

        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                # capture label in default arg so closure works correctly
                cmd = (lambda t=label: self._on_button(t))
                b = ttk.Button(btn_frame, text=label, command=cmd)
                b.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

        # make grid expandable
        cols = max(len(row) for row in rows)
        for c in range(cols):
            btn_frame.columnconfigure(c, weight=1)
        for r in range(len(rows)):
            btn_frame.rowconfigure(r, weight=1)

        # bottom: status and history quick view button + auto export
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=6)
        self.mode_label = ttk.Label(bottom, text=f"Mode: {self.state['mode']}")
        self.mode_label.pack(side="left")

        # Auto Export button (saves to EXPORTS_DIR with timestamp) and Show History
        ttk.Button(bottom, text="Auto Export",
                   command=self._auto_export).pack(side="right", padx=4)
        ttk.Button(bottom, text="Show History",
                   command=self.show_history_window).pack(side="right")

    def _bind_keys(self):
        self.bind("<Return>", lambda e: self._on_button("="))
        self.bind("<KP_Enter>", lambda e: self._on_button("="))
        self.bind("<Escape>", lambda e: self._on_button("C"))
        self.bind("<BackSpace>", lambda e: self._on_button("⌫"))
        self.bind("<Control-s>", lambda e: self._on_save())
        self.bind("<Control-l>", lambda e: self._on_load())

    def _pretty(self, v):
        if isinstance(v, Decimal) and v == v.to_integral():
            return int(v)
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v

    def _refresh_result_display(self):
        if self.state["ans"] is None:
            self.result_var.set("Ready")
        else:
            self.result_var.set(str(self._pretty(self.state["ans"])))
        self.mode_label.config(text=f"Mode: {self.state['mode']}")

    def _on_button(self, token):
        # core actions for buttons
        if token == "C":
            self.expr_var.set("")
            self.result_var.set("Ready")
            return
        if token == "⌫":
            s = self.expr_var.get()
            self.expr_var.set(s[:-1])
            return
        if token == "=":
            self._evaluate_entry()
            return
        if token == "history":
            self.show_history_window()
            return
        if token == "export":
            self._export_history()
            return
        if token == "undo":
            ok, msg = undo(self.state)
            self._refresh_result_display()
            messagebox.showinfo("Undo", msg)
            return
        if token == "mode":
            self._toggle_mode()
            return
        if token == "M+":
            self._memory_add()
            return
        if token == "M-":
            self._memory_sub()
            return
        if token == "MR/MC":
            # show recall and clear options
            self._memory_recall_clear()
            return

        # insert token at cursor
        entry = self.entry
        try:
            idx = entry.index(tk.INSERT)
            entry.insert(idx, token)
        except Exception:
            self.expr_var.set(self.expr_var.get() + token)

    def _evaluate_entry(self):
        raw = self.expr_var.get().strip()
        if not raw:
            return
        ok, msg = self._process_input_text(raw)
        if ok:
            # if msg is result or assignment info, show it
            self.expr_var.set("")  # clear input for next
            self._refresh_result_display()
            if msg:
                messagebox.showinfo("Result", str(msg))
        else:
            messagebox.showerror("Error", msg)

    # process expression or assignment or commands (a trimmed copy of the REPL logic)
    def _process_input_text(self, raw):
        cmd = raw.strip()
        if not cmd:
            return True, None
        lower = cmd.lower()

        # commands similar to REPL
        if lower == "clear":
            self.state["history"].clear()
            self.state["vars"].clear()
            self.state["ans"] = None
            self.state["memory"] = Decimal(
                0) if self.state["mode"] == "decimal" else 0.0
            self.state["_undo"].clear()
            self._refresh_result_display()
            return True, "Cleared session."
        if lower == "help":
            names = sorted(list(evaluator.allowed_names.keys()))
            return True, ("Help:\nFunctions: " + ", ".join(names) +
                          "\nCommands: clear, help, undo, export, mode, history\nMemory: M+ M- MR MC"), None

        # assignment detection via AST
        try:
            node = ast.parse(raw, mode="exec")
        except SyntaxError:
            node = None

        if node is not None and len(node.body) == 1 and isinstance(node.body[0], ast.Assign):
            assign = node.body[0]
            if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
                return False, "Only simple assignments name = expr allowed"
            name = assign.targets[0].id
            deny = set(evaluator.allowed_names.keys()) | {"ans"}
            ok, msg = is_valid_name(name, deny)
            if not ok:
                return False, msg
            rhs = raw.split("=", 1)[1].strip()
            try:
                val = evaluator.eval(rhs, ans=self.state["ans"], variables=self.state["vars"],
                                     decimal=(self.state["mode"] == "decimal"))
            except Exception as e:
                return False, f"Error evaluating RHS: {e}"
            if not isinstance(val, (int, float, Decimal)):
                return False, "Assigned value must be numeric"
            existed = name in self.state["vars"]
            old = self.state["vars"].get(name)
            push_undo(self.state, "assign", {
                      "name": name, "existed": existed, "old": old, "line": raw})
            self.state["vars"][name] = val
            self.state["ans"] = val
            self.state["history"].append(
                {"expr": raw, "result": val, "time": datetime.datetime.now(datetime.UTC).isoformat()})
            self._refresh_result_display()
            return True, f"{name} = {val}"

        # else evaluate expression
        try:
            val = evaluator.eval(raw, ans=self.state["ans"], variables=self.state["vars"],
                                 decimal=(self.state["mode"] == "decimal"))
        except Exception as e:
            return False, f"{e}"
        push_undo(self.state, "calc", {"old_ans": self.state["ans"]})
        self.state["ans"] = val
        self.state["history"].append(
            {"expr": raw, "result": val, "time": datetime.datetime.now(datetime.UTC).isoformat()})
        self._refresh_result_display()
        return True, f"{raw} = {val}"

    # memory functions
    def _memory_add(self):
        if self.state["ans"] is None:
            messagebox.showwarning("Memory", "No current ans to add.")
            return
        push_undo(self.state, "memory", {"old": self.state["memory"]})
        if self.state["mode"] == "decimal":
            cur = self.state["memory"] if isinstance(
                self.state["memory"], Decimal) else Decimal(self.state["memory"])
            self.state["memory"] = cur + Decimal(str(self.state["ans"]))
        else:
            self.state["memory"] = float(
                self.state["memory"]) + float(self.state["ans"])
        messagebox.showinfo("Memory", f"Memory = {self.state['memory']}")

    def _memory_sub(self):
        if self.state["ans"] is None:
            messagebox.showwarning("Memory", "No current ans to subtract.")
            return
        push_undo(self.state, "memory", {"old": self.state["memory"]})
        if self.state["mode"] == "decimal":
            cur = self.state["memory"] if isinstance(
                self.state["memory"], Decimal) else Decimal(self.state["memory"])
            self.state["memory"] = cur - Decimal(str(self.state["ans"]))
        else:
            self.state["memory"] = float(
                self.state["memory"]) - float(self.state["ans"])
        messagebox.showinfo("Memory", f"Memory = {self.state['memory']}")

    def _memory_recall_clear(self):
        # small dialog for recall or clear
        resp = simpledialog.askstring(
            "Memory", "Type 'mr' to recall, 'mc' to clear:")
        if not resp:
            return
        r = resp.strip().lower()
        if r == "mr":
            messagebox.showinfo("Memory", f"Memory = {self.state['memory']}")
        elif r == "mc":
            push_undo(self.state, "memory", {"old": self.state["memory"]})
            self.state["memory"] = Decimal(
                0) if self.state["mode"] == "decimal" else 0.0
            messagebox.showinfo("Memory", "Memory cleared.")
        else:
            messagebox.showwarning("Memory", "Unknown command.")

    def _toggle_mode(self):
        cur = self.state["mode"]
        new = "decimal" if cur == "float" else "float"
        self.state["mode"] = new
        self.mode_label.config(text=f"Mode: {new}")
        messagebox.showinfo(
            "Mode", f"Mode set to {new}. (Functions disabled in decimal mode)")

    def _export_history(self):
        """
        Export history using a Save As dialog.
        Default folder is EXPORTS_DIR (session-based).
        CSV if filename ends with .csv, otherwise plain text.
        """
        # default filename with timestamp
        ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H-%M-%S")
        default_name = f"history_{ts}.csv"

        fn = filedialog.asksaveasfilename(
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"),
                       ("Text files", "*.txt"), ("All files", "*.*")],
            title="Save history as..."
        )
        if not fn:
            return  # user cancelled

        try:
            if fn.lower().endswith(".csv"):
                export_history_csv(self.state, fn)
            else:
                with open(fn, "w", encoding="utf-8", newline="") as f:
                    for i, h in enumerate(self.state["history"], 1):
                        time = h.get("time", "")
                        expr = h.get("expr", "")
                        result = h.get("result", "")
                        f.write(f"{i}\t{time}\t{expr} = {result}\n")
        except Exception as e:
            messagebox.showerror("Export", f"Failed to save history: {e}")
            return

        messagebox.showinfo("Export", f"History saved to\n{fn}")

    def _auto_export(self):
        """Auto-export history to EXPORTS_DIR with a timestamped filename (no dialog)."""
        try:
            saved = auto_export_history(self.state)
        except Exception as e:
            messagebox.showerror("Auto Export", f"Failed to auto-export: {e}")
            return
        messagebox.showinfo("Auto Export", f"History auto-saved to:\n{saved}")

    def show_history_window(self):
        win = tk.Toplevel(self)
        win.title("History")
        txt = ScrolledText(win, wrap="word", width=80, height=20)
        txt.pack(fill="both", expand=True)
        for i, h in enumerate(self.state["history"], 1):
            txt.insert(
                "end", f"{i}: {h['expr']} = {h['result']}  ({h['time']})\n")
        txt.configure(state="disabled")

        # clickable reinsert: double click line to put expression back in entry
        def on_double_click(event):
            try:
                idx = txt.index("@%s,%s linestart" % (event.x, event.y))
                line = txt.get(idx, f"{idx} lineend")
                expr = line.split(":", 1)[1].split("=", 1)[0].strip()
                self.expr_var.set(expr)
                win.destroy()
            except Exception:
                pass

        txt.bind("<Double-Button-1>", on_double_click)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)

    def _on_save(self):
        try:
            save_session(self.state)
            messagebox.showinfo("Save", f"Saved to {SESSION_PATH}")
        except Exception as e:
            messagebox.showerror("Save", f"Failed to save: {e}")

    def _on_load(self):
        try:
            loaded = load_session()
            self.state.update(loaded)
            messagebox.showinfo("Load", "Session loaded.")
            self._refresh_result_display()
        except Exception as e:
            messagebox.showerror("Load", f"Failed: {e}")

    def on_closing(self):
        try:
            save_session(self.state)
        except Exception as e:
            print("Failed to save session:", e)
        self.destroy()


# ------------------------
# Entrypoint
# ------------------------
def main():
    app = CalculatorGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
