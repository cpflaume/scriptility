"""Tests für scripts/lib/stackit.py — den Read-Only-Guard."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.lib.stackit import MutatingCommandError, assert_read_only, run_json


@pytest.mark.parametrize(
    "args",
    [
        ["project", "list"],
        ["server", "list", "--project-id", "p"],
        ["server", "describe", "--server-id", "s"],
        ["security-group", "rule", "list", "--project-id", "p", "--security-group-id", "g"],
        ["image", "list", "--all", "--project-id", "p"],
        ["server", "machine-type", "list", "--project-id", "p"],
        # describe mit positionaler ID: das Verb steht nicht am Ende des Pfads.
        ["image", "describe", "11111111-2222-3333-4444-555555555555", "--project-id", "p"],
    ],
)
def test_read_commands_allowed(args):
    assert_read_only(args)  # darf nicht werfen


@pytest.mark.parametrize(
    "args",
    [
        ["server", "create", "--name", "x"],
        ["server", "delete", "--server-id", "s"],
        ["server", "update", "--server-id", "s"],
        ["security-group", "rule", "create", "--project-id", "p"],
        ["server", "start", "--server-id", "s"],
        ["server", "delete", "s-123", "--project-id", "p"],  # mutierendes Verb vor positionaler ID
        [],  # leerer Command => default-deny
        ["--help"],  # nur Flags, kein Verb
    ],
)
def test_mutating_commands_blocked(args):
    with pytest.raises(MutatingCommandError):
        assert_read_only(args)


def test_run_json_blocks_before_subprocess():
    """Ein mutierender Command darf stackit gar nicht erst starten."""
    with patch("subprocess.run") as run:
        with pytest.raises(MutatingCommandError):
            run_json(["server", "delete", "--server-id", "s"])
        run.assert_not_called()


def test_run_json_parses_read_output():
    class _Res:
        returncode = 0
        stderr = ""
        stdout = json.dumps([{"id": "s-1"}])

    with patch("subprocess.run", return_value=_Res()):
        out = run_json(["server", "list", "--project-id", "p"])
    assert out == [{"id": "s-1"}]
