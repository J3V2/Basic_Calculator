# tests/test_expr_eval.py
import pytest
from expr_eval import ExpressionEvaluator

ev = ExpressionEvaluator()


def test_simple():
    assert ev.eval("2+3") == 5


def test_precedence():
    assert ev.eval("2 + 3 * 4 - (1 / 2)") == 2 + 3*4 - (1/2)


def test_unary_and_power():
    assert ev.eval("-3 + 2**3") == -3 + 8


def test_modulo():
    assert ev.eval("10 % 3") == 1


def test_div_zero():
    with pytest.raises(ZeroDivisionError):
        ev.eval("1/0")


def test_invalid_token():
    with pytest.raises(ValueError):
        ev.eval("__import__('os').system('ls')")


def test_ans_usage():
    assert ev.eval("ans + 2", ans=10) == 12


def test_caret_alias():
    assert ev.eval("2 ^ 3") == 8


def test_sin_pi_over_2():
    assert ev.eval("sin(pi/2)") == 1.0


def test_sqrt_and_log():
    assert ev.eval("sqrt(16)") == 4
    assert pytest.approx(ev.eval("log(e)"), rel=1e-12) == 1.0


def test_invalid_function():
    with pytest.raises(ValueError):
        ev.eval("open('file')")


def test_attribute_not_allowed():
    with pytest.raises(ValueError):
        ev.eval("__import__('os').system('ls')")


def test_bad_arg_count():
    with pytest.raises(TypeError):  # or ValueError depending how you validate
        ev.eval("sqrt(1,2)")
