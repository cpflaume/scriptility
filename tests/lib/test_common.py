"""Tests für scripts/lib/common.py"""

import json

import pytest

from scripts.lib import common


def test_require_env_ok(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    assert common.require_env("FOO") == {"FOO": "bar"}


def test_require_env_missing_exits(monkeypatch, capsys):
    monkeypatch.delenv("DOES_NOT_EXIST", raising=False)
    with pytest.raises(SystemExit) as exc:
        common.require_env("DOES_NOT_EXIST")
    assert exc.value.code == common.EXIT_USAGE
    assert "DOES_NOT_EXIST" in capsys.readouterr().err


def test_emit_json(capsys):
    common.emit({"a": 1}, json_output=True)
    assert json.loads(capsys.readouterr().out) == {"a": 1}


def test_emit_table_fn(capsys):
    common.emit([1, 2], json_output=False, table_fn=lambda d: print(f"got {d}"))
    assert capsys.readouterr().out.strip() == "got [1, 2]"
