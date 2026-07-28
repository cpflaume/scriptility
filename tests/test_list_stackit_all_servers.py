"""Tests für scripts/list_stackit_all_servers.py"""

from __future__ import annotations

import csv
import io
import json
from unittest.mock import patch

import pytest

from scripts.list_stackit_all_servers import main


def _fake_run_json(args):
    """Simuliert lib.stackit.run_json: project list + server list pro Projekt."""
    if args[0] == "project":
        return [{"projectId": "p-1", "name": "alpha"}, {"projectId": "p-2", "name": "beta"}]
    pid = args[args.index("--project-id") + 1]
    if pid == "p-1":
        return [
            {
                "id": "s-1",
                "name": "web",
                "status": "ACTIVE",
                "machineType": "g1.1",
                "availabilityZone": "eu01-1",
            }
        ]
    return []


def test_csv_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("scripts.list_stackit_all_servers.run_json", side_effect=_fake_run_json):
        rc = main([])
    assert rc == 0
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert len(rows) == 1
    assert rows[0]["project_name"] == "alpha"
    assert rows[0]["server_name"] == "web"
    assert rows[0]["machine_type"] == "g1.1"


def test_json_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("scripts.list_stackit_all_servers.run_json", side_effect=_fake_run_json):
        rc = main(["--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["project_id"] == "p-1"
    assert data[0]["availability_zone"] == "eu01-1"


def test_requires_env(monkeypatch):
    monkeypatch.delenv("STACKIT_SERVICE_ACCOUNT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
