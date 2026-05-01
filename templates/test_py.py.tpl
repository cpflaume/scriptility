"""Tests für {{NAME}}.py"""

import subprocess
import sys


def test_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.{{NAME}}", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    # --help exited 0
    assert result.returncode == 0
