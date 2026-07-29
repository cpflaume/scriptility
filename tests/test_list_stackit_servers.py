"""Tests für scripts/list_stackit_servers.py"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.list_stackit_servers import main

_IMAGES = [
    {
        "id": "img-1",
        "name": "Ubuntu 22.04",
        "config": {
            "operatingSystem": "linux",
            "operatingSystemDistro": "ubuntu",
            "operatingSystemVersion": "22.04",
        },
    }
]
_MACHINE_TYPES = [{"name": "g1.2", "vcpus": 2, "ram": 4096, "disk": 20}]
_SERVERS = [
    {
        "id": "s-1",
        "name": "web",
        "status": "ACTIVE",
        "powerStatus": "RUNNING",
        "machineType": "g1.2",
        "imageId": "img-1",
        "availabilityZone": "eu01-1",
        "nics": [{"ipv4": "10.0.0.5", "publicIp": "1.2.3.4"}],
    }
]


def _fake_subprocess(cmd, **_kwargs):
    """Simuliert stackit-cli anhand des Command-Pfads (cmd ohne stackit/format)."""
    args = cmd[1:-2]

    class _Res:
        returncode = 0
        stderr = ""

    if "machine-type" in args:
        _Res.stdout = json.dumps(_MACHINE_TYPES)
    elif args[0] == "image":
        _Res.stdout = json.dumps(_IMAGES)
    elif args[0] == "server":
        _Res.stdout = json.dumps(_SERVERS)
    else:
        _Res.stdout = "[]"
    return _Res()


def test_table_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("subprocess.run", side_effect=_fake_subprocess):
        rc = main(["proj-1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "web" in out
    assert "RUNNING" in out
    assert "ubuntu" in out
    assert "1.2.3.4" in out


def test_json_output(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("subprocess.run", side_effect=_fake_subprocess):
        rc = main(["proj-1", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    r = data[0]
    assert r["id"] == "s-1"
    assert r["power_status"] == "RUNNING"
    assert r["os"] == "linux"
    assert r["os_distro"] == "ubuntu"
    assert r["image_name"] == "Ubuntu 22.04"
    assert r["vcpus"] == 2
    assert r["ram_gb"] == 4.0
    assert r["private_ips"] == "10.0.0.5"
    assert r["public_ips"] == "1.2.3.4"


def test_requires_env(monkeypatch):
    monkeypatch.delenv("STACKIT_SERVICE_ACCOUNT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(["proj-1"])
    assert exc.value.code == 2
