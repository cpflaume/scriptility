"""Tests für scripts/stackit/list_firewall_rules.py"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.stackit.list_firewall_rules import main


def _fake_stackit(args, **_kwargs):
    """Mock-Implementierung von subprocess.run, die stackit-CLI simuliert."""

    class _Res:
        returncode = 0
        stderr = ""

    if "rule" in args:
        _Res.stdout = json.dumps(
            [
                {
                    "direction": "ingress",
                    "protocol": {"name": "tcp"},
                    "portRange": {"min": 443, "max": 443},
                    "remoteIpRange": "0.0.0.0/0",
                }
            ]
        )
    else:
        _Res.stdout = json.dumps([{"id": "sg-1", "name": "web"}])
    return _Res()


def test_main_renders_rules(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("subprocess.run", side_effect=_fake_stackit):
        rc = main(["proj-1", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["group"] == "web"
    assert out[0]["protocol"] == "tcp"
    assert out[0]["port_min"] == 443


def test_main_requires_env(monkeypatch):
    monkeypatch.delenv("STACKIT_SERVICE_ACCOUNT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(["proj-1"])
    assert exc.value.code == 2
