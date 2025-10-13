# tests/test_cli_help.py
import subprocess
import sys

def test_help_exits_zero():
    r = subprocess.run([sys.executable, "monitoring1.py", "--help"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "usage" in r.stdout.lower()
