# tests/test_variables.py
from expr_eval import ExpressionEvaluator

ev = ExpressionEvaluator()


def test_assignment_and_usage():
    state = {'ans': None, 'vars': {}}
    # eval returns a number when variables passed in
    val = ev.eval("2 + 3", variables=state['vars'])
    assert val == 5
    state['vars']['x'] = 5
    assert ev.eval("x * 2", variables=state['vars']) == 10


def test_assign_expr_with_var():
    state = {'vars': {'x': 4}}
    assert ev.eval("x + 1", variables=state['vars']) == 5


def test_invalid_name():
    # you should test the REPL/process_input name validation function,
    # e.g., invalid: '1a = 5', reserved: 'sin = 3', 'ans = 2'
    pass
