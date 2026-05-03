"""Tests für scripts/{{NAME}}.py"""

import subprocess
import sys


def test_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/{{NAME}}.py", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    # argparse exits 0 on --help
    assert result.returncode == 0
