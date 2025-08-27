# tests/test_state_persistence.py
import json
from decimal import Decimal
import tempfile
from pathlib import Path
import calculator


def test_save_load_roundtrip(tmp_path):
    state = {
        "ans": Decimal("1.1"),
        "vars": {"x": Decimal("2.0")},
        "history": [{"expr": "1+0.1", "result": Decimal("1.1"), "time": "t"}],
        "memory": Decimal("0"),
        "mode": "decimal",
        "_undo": []
    }
    f = tmp_path / "session.json"
    # use calculator.save_session/load_session helpers
    calculator.save_session(state, path=str(f))
    loaded = calculator.load_session(path=str(f))
    assert loaded["mode"] == "decimal"
    # ans and memory could be Decimal (string->Decimal)
    assert str(loaded["ans"]) == str(state["ans"])
    assert str(loaded["vars"]["x"]) == str(state["vars"]["x"])
