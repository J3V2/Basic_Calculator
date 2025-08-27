# tests/test_undo.py
from decimal import Decimal
import calculator
from expr_eval import ExpressionEvaluator

# ensure fresh state


def test_undo_assignment_and_calc():
    state = {"ans": None, "vars": {}, "history": [],
             "memory": 0.0, "mode": "float", "_undo": []}
    ok, msg, state = calculator.process_input(
        "x = 5", state, calculator.evaluator)
    assert ok
    assert state["vars"]["x"] == 5
    ok, msg, state = calculator.process_input(
        "2 + 3", state, calculator.evaluator)
    assert ok
    assert state["ans"] == 5
    # undo last calc
    ok, msg = calculator.undo(state)
    assert ok
    # undo assignment
    ok, msg = calculator.undo(state)
    assert ok
    assert "x" not in state["vars"]
