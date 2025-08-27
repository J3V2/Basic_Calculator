# tests/test_cli.py
import sys
import subprocess
from pathlib import Path
import tempfile

PY = sys.executable
ROOT = Path(__file__).resolve().parents[1]


def run_cmd(args, check=False):
    return subprocess.run([PY, str(ROOT / "calculator.py")] + args,
                          capture_output=True, text=True, check=check)


def test_expr_flag_simple():
    r = run_cmd(["--expr", "2+3*4"])
    assert r.returncode == 0
    # Output should contain the evaluated expression or result text
    assert "14" in r.stdout or "14" in r.stderr


def test_file_flag(tmp_path):
    f = tmp_path / "batch.txt"
    f.write_text("2+2\n# comment\n3*4\n")
    r = run_cmd(["--file", str(f)])
    assert r.returncode == 0
    assert "4" in r.stdout
    assert "12" in r.stdout
