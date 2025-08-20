# # tests/test_core.py
# from calc_core import operator, pretty_number, format_result
# import pytest


# def test_add():
#     assert operator(2, 3, "+") == 5


# def test_div_zero():
#     with pytest.raises(ZeroDivisionError):
#         operator(5, 0, "/")


# def test_power_syntax():
#     assert operator(2, 3, "**") == 8
#     assert operator(2, 3, "^") == 8


# def test_pretty_number():
#     assert pretty_number(3.0) == 3
#     assert pretty_number(3.2) == 3.2


# def test_format_result():
#     assert format_result(2, 3, "+", 5) == "2 + 3 = 5"
