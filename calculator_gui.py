# calculator_gui.py
import tkinter as tk
from tkinter import ttk
from expr_eval import ExpressionEvaluator

# Instantiate safe evaluator (allow use of 'ans' in expressions)
_evaluator = ExpressionEvaluator(allow_ans=True)


class CalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basic Calculator")
        self.geometry("360x520")
        self.minsize(320, 420)

        # session state
        self.ans = None
        self.vars = {}   # future use for Problem 5
        self.history = []

        self._create_widgets()
        self._layout_widgets()
        self._bind_keys()

    def _create_widgets(self):
        # Expression entry (user-editable)
        self.expr_var = tk.StringVar()
        self.entry = ttk.Entry(
            self, textvariable=self.expr_var, font=("Segoe UI", 18))
        self.entry.focus_set()

        # Result label (shows result or error)
        self.result_var = tk.StringVar()
        self.result_label = ttk.Label(
            self, textvariable=self.result_var, font=("Segoe UI", 14), anchor="e")

        # Buttons: list of (text, command)
        self.buttons = [
            ['C', '(', ')', '⌫'],
            ['7', '8', '9', '/'],
            ['4', '5', '6', '*'],
            ['1', '2', '3', '-'],
            ['0', '.', '^', '+'],
            ['history', 'ans', '%', '='],
        ]

        # create button widgets in a 2D list
        self.button_widgets = []
        for r, row in enumerate(self.buttons):
            wrow = []
            for c, label in enumerate(row):
                btn = ttk.Button(self, text=label,
                                 command=lambda L=label: self._on_button(L))
                wrow.append(btn)
            self.button_widgets.append(wrow)

    def _layout_widgets(self):
        # Use grid layout with weights to make it responsive
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        # place entry and result
        self.entry.grid(row=0, column=0, sticky="nsew", padx=8, pady=(10, 2))
        self.result_label.grid(
            row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        # configure grid inside frame
        for i in range(len(self.buttons)):
            btn_frame.rowconfigure(i, weight=1)
        for j in range(len(self.buttons[0])):
            btn_frame.columnconfigure(j, weight=1)

        # place buttons
        for r, row in enumerate(self.button_widgets):
            for c, btn in enumerate(row):
                btn.grid(in_=btn_frame, row=r, column=c,
                         sticky="nsew", padx=4, pady=4)

    def _bind_keys(self):
        # Bind keys for inserting characters
        for ch in '0123456789+-*/().%^':
            self.bind(ch, self._on_key)
            # also uppercase operators unlikely needed
        # dot
        self.bind('.', self._on_key)
        # Enter => evaluate
        self.bind("<Return>", lambda e: self._evaluate())
        # Backspace
        self.bind("<BackSpace>", lambda e: self._backspace())
        # Escape => clear
        self.bind("<Escape>", lambda e: self._clear())
        # 'h' for history quick access
        self.bind('h', lambda e: self._show_history())
        # allow ctrl+c to copy (default), ctrl+v to paste works in Entry
        # allow focus click to entry
        self.entry.bind("<FocusIn>", lambda e: self.entry.icursor(tk.END))

    # Button handler (buttons call this)
    def _on_button(self, label):
        if label == 'C':
            self._clear()
            return
        if label == '⌫':
            self._backspace()
            return
        if label == '=':
            self._evaluate()
            return
        if label == 'history':
            self._show_history()
            return
        if label == 'ans':
            if self.ans is None:
                self._set_result("No previous answer")
            else:
                # insert 'ans' at cursor
                self._insert_text('ans')
            return

        # other labels (digits, operators, ., ^, %, parentheses)
        self._insert_text(label)

    # Keyboard insertion handler
    def _on_key(self, event):
        ch = event.char
        # allow only expected characters
        if ch and ch in '0123456789+-*/().%^':
            self._insert_text(ch)
        # else ignore

    def _insert_text(self, text):
        # insert at cursor position in entry
        idx = self.entry.index(tk.INSERT)
        cur = self.expr_var.get()
        new = cur[:idx] + text + cur[idx:]
        self.expr_var.set(new)
        # move cursor after inserted text
        self.entry.icursor(idx + len(text))
        self.entry.focus_set()

    def _backspace(self):
        idx = self.entry.index(tk.INSERT)
        if idx == 0:
            return
        cur = self.expr_var.get()
        new = cur[:idx-1] + cur[idx:]
        self.expr_var.set(new)
        self.entry.icursor(idx-1)
        self.entry.focus_set()

    def _clear(self):
        self.expr_var.set('')
        self.result_var.set('')
        self.entry.focus_set()

    def _set_result(self, text):
        # show text in result label
        self.result_var.set(text)

    def _show_history(self):
        if not self.history:
            self._set_result("No history")
            return
        # show last few lines (or open a small window)
        hist_text = "\n".join(self.history[-10:])  # last 10
        # pop-up simple history window
        win = tk.Toplevel(self)
        win.title("History (last 10)")
        txt = tk.Text(win, height=12, width=40)
        txt.insert("1.0", hist_text)
        txt.configure(state="disabled")
        txt.pack(expand=True, fill="both", padx=8, pady=8)

    def _evaluate(self):
        expr = self.expr_var.get().strip()
        if not expr:
            return
        try:
            # evaluator will accept '^' because it replaces ^ with **
            val = _evaluator.eval(expr, ans=self.ans, variables=self.vars)
        except Exception as e:
            # show friendly error
            self._set_result(f"Error: {e}")
            return

        # success
        # format result: show nice representation (convert float that is integer-like)
        if isinstance(val, float) and val.is_integer():
            display_val = str(int(val))
        else:
            display_val = str(val)
        self._set_result(display_val)
        # update ans and history
        self.ans = val
        self.history.append(f"{expr} = {display_val}")
        # optionally clear expression or leave it (we keep it)
        self.entry.focus_set()


if __name__ == "__main__":
    app = CalculatorApp()
    app.mainloop()
