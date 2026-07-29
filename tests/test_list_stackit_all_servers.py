"""Tests für scripts/list_stackit_all_servers.py"""

from __future__ import annotations

import csv
import io
import json
from unittest.mock import patch

import pytest

from scripts.list_stackit_all_servers import main

_PROJECTS = [{"projectId": "p-1", "name": "alpha"}]
_IMAGES = [
    {
        "id": "img-win",
        "name": "Windows Server 2022",
        "config": {
            "operatingSystem": "windows",
            "operatingSystemDistro": "windows",
            "operatingSystemVersion": "2022",
        },
    }
]
_MACHINE_TYPES = [{"name": "g1.4", "vcpus": 4, "ram": 8192, "disk": 40}]
_SERVERS = [
    {
        "id": "s-1",
        "name": "win",
        "status": "ACTIVE",
        "powerStatus": "RUNNING",
        "machineType": "g1.4",
        "imageId": "img-win",
        "availabilityZone": "eu01-1",
        "nics": [{"ipv4": "10.0.0.9", "publicIp": "5.6.7.8"}],
    }
]


def _fake_subprocess(cmd, **_kwargs):
    args = cmd[1:-2]

    class _Res:
        returncode = 0
        stderr = ""

    if args[0] == "project":
        _Res.stdout = json.dumps(_PROJECTS)
    elif "machine-type" in args:
        _Res.stdout = json.dumps(_MACHINE_TYPES)
    elif args[0] == "image":
        _Res.stdout = json.dumps(_IMAGES)
    elif args[0] == "server":
        _Res.stdout = json.dumps(_SERVERS)
    else:
        _Res.stdout = "[]"
    return _Res()


def test_csv_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("subprocess.run", side_effect=_fake_subprocess):
        rc = main([])
    assert rc == 0
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert len(rows) == 1
    row = rows[0]
    assert row["project_name"] == "alpha"
    assert row["name"] == "win"
    assert row["power_status"] == "RUNNING"
    assert row["os"] == "windows"
    assert row["os_version"] == "2022"
    assert row["vcpus"] == "4"
    assert row["ram_gb"] == "8.0"
    assert row["public_ips"] == "5.6.7.8"


def test_json_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("subprocess.run", side_effect=_fake_subprocess):
        rc = main(["--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["project_id"] == "p-1"
    assert data[0]["availability_zone"] == "eu01-1"
    assert data[0]["private_ips"] == "10.0.0.9"


def test_requires_env(monkeypatch):
    monkeypatch.delenv("STACKIT_SERVICE_ACCOUNT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
