"""Tests für scripts/list_stackit_servers.py"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.list_stackit_servers import main


def _fake_run_json(args):
    """Simuliert lib.stackit.run_json: server list eines Projekts."""
    assert args[:2] == ["server", "list"]
    return [
        {"id": "s-1", "name": "web", "status": "ACTIVE", "machineType": "g1.1"},
        {"id": "s-2", "name": "db", "status": "STOPPED", "machineType": "c1.2"},
    ]


def test_table_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("scripts.list_stackit_servers.run_json", side_effect=_fake_run_json):
        rc = main(["proj-1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "web" in out
    assert "g1.1" in out


def test_json_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("scripts.list_stackit_servers.run_json", side_effect=_fake_run_json):
        rc = main(["proj-1", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["id"] == "s-1"
    assert data[1]["machine_type"] == "c1.2"


def test_requires_env(monkeypatch):
    monkeypatch.delenv("STACKIT_SERVICE_ACCOUNT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(["proj-1"])
    assert exc.value.code == 2
