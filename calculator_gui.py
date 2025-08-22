# gui_calculator.py
import tkinter as tk
from tkinter import messagebox, scrolledtext
from expr_eval import ExpressionEvaluator

evaluator = ExpressionEvaluator(allow_ans=True)


class CalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basic Calculator")
        self.geometry("420x600")
        self.minsize(360, 480)

        self.ans = None
        self.history = []

        self._build_ui()
        self._bind_keys()

    def _build_ui(self):
        # Entry for expression
        self.entry_var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self.entry_var,
                         font=("Consolas", 16))
        entry.grid(row=0, column=0, columnspan=4,
                   sticky="nsew", padx=8, pady=8)
        entry.focus_set()
        self.entry = entry

        # Result label
        self.result_var = tk.StringVar(value="Ready")
        lbl = tk.Label(self, textvariable=self.result_var,
                       anchor="e", font=("Consolas", 14))
        lbl.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=8)

        # Button grid
        btn_texts = [
            ["Ans", "(", ")", "C"],
            ["sin(", "cos(", "tan(", "⌫"],
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "%", "+"],
            ["pi", "e", "^", "="],
            ["sqrt(", "log(", "history", "clear"],
        ]
        for r, row in enumerate(btn_texts, start=2):
            for c, text in enumerate(row):
                def cmd(t=text): return self._on_button(t)
                b = tk.Button(self, text=text, command=cmd, font=("Arial", 12))
                b.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

        # Grid weight so it resizes
        for i in range(4):
            self.columnconfigure(i, weight=1)
        for i in range(2, 2 + len(btn_texts)):
            self.rowconfigure(i, weight=1)

    def _bind_keys(self):
        self.bind("<Return>", lambda e: self.evaluate())
        self.bind("<KP_Enter>", lambda e: self.evaluate())
        self.bind("<Escape>", lambda e: self._on_button("C"))
        self.bind("<BackSpace>", lambda e: self._on_button("⌫"))
        self.bind("<Control-l>", lambda e: self._on_button("clear"))

    def _on_button(self, token):
        token = str(token)
        if token == "C":
            self.entry_var.set("")
            self.result_var.set("Ready")
            return
        if token == "⌫":
            s = self.entry_var.get()
            self.entry_var.set(s[:-1])
            return
        if token == "=":
            self.evaluate()
            return
        if token == "history":
            self.show_history()
            return
        if token == "clear":
            self.history.clear()
            self.ans = None
            self.entry_var.set("")
            self.result_var.set("Cleared")
            return

        # insert token at cursor
        entry = self.entry
        try:
            idx = entry.index(tk.INSERT)
            entry.insert(idx, token)
        except Exception:
            entry.insert(tk.END, token)

    def _pretty(self, v):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v

    def evaluate(self):
        expr = self.entry_var.get().strip()
        if not expr:
            self.result_var.set("Enter an expression")
            return
        try:
            val = evaluator.eval(expr, ans=self.ans, variables={})
        except Exception as e:
            self.result_var.set(f"Error: {e}")
            return
        self.ans = val
        pretty = self._pretty(val)
        self.result_var.set(str(pretty))
        # put the result in entry for chaining
        self.entry_var.set(str(pretty))
        # add to history
        line = f"{expr} = {pretty}"
        self.history.append(line)

    def show_history(self):
        win = tk.Toplevel(self)
        win.title("History")
        txt = scrolledtext.ScrolledText(win, width=60, height=20, wrap=tk.WORD)
        txt.pack(expand=True, fill=tk.BOTH)
        if not self.history:
            txt.insert(tk.END, "No history yet.")
        else:
            txt.insert(tk.END, "\n".join(
                f"{i+1}: {line}" for i, line in enumerate(self.history)))
        txt.configure(state="disabled")
        # add a close button
        tk.Button(win, text="Close", command=win.destroy).pack(pady=6)


def main():
    try:
        app = CalcApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to start GUI: {e}")


if __name__ == "__main__":
    main()
