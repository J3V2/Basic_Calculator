# tests/test_plugins.py
import tempfile
import os
import sys
from pathlib import Path
import calculator


def test_load_sample_plugin(tmp_path, monkeypatch):
    # create a temporary plugins dir with a plugin file
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_code = """
def register(names):
    names['test_cube'] = lambda x: x**3
"""
    p = plugins_dir / "pg1.py"
    p.write_text(plugin_code)
    # call load_plugins pointing to tmp plugins dir
    calculator.load_plugins(plugins_dir=str(plugins_dir))
    # after loading, evaluator in calculator should have the name registered
    assert "test_cube" in calculator.evaluator.allowed_names
    # cleanup: remove module from sys.modules (if imported)
    if "pg1" in sys.modules:
        del sys.modules["pg1"]
