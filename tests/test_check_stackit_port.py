"""Tests für scripts/check_stackit_port.py"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.check_stackit_port import main, rule_allows


def _fake_query(args):
    """Simuliert lib.stackit.run_stackit_query: security-group list + rule list."""
    if args[0] == "security-group" and "rule" not in args:
        return [{"id": "sg-1", "name": "web"}]
    return [
        {
            "direction": "ingress",
            "protocol": {"name": "tcp"},
            "portRange": {"min": 443, "max": 443},
            "ipRange": "0.0.0.0/0",
        },
        {
            "direction": "ingress",
            "protocol": {"name": "tcp"},
            "portRange": {"min": 80, "max": 80},
        },
    ]


def test_port_open(monkeypatch, capsys):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("scripts.check_stackit_port.run_stackit_query", side_effect=_fake_query):
        rc = main(["--project-id", "p", "--port", "443", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["open"] is True
    assert data["matched_rules"][0]["group"] == "web"
    assert data["matched_rules"][0]["remote"] == "0.0.0.0/0"


def test_port_closed(monkeypatch):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("scripts.check_stackit_port.run_stackit_query", side_effect=_fake_query):
        rc = main(["--project-id", "p", "--port", "22"])
    assert rc == 1


def test_wrong_protocol_closed(monkeypatch):
    monkeypatch.setenv("STACKIT_SERVICE_ACCOUNT_TOKEN", "x")
    with patch("scripts.check_stackit_port.run_stackit_query", side_effect=_fake_query):
        rc = main(["--project-id", "p", "--port", "443", "--protocol", "udp"])
    assert rc == 1


def test_requires_env(monkeypatch):
    monkeypatch.delenv("STACKIT_SERVICE_ACCOUNT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(["--project-id", "p", "--port", "443"])
    assert exc.value.code == 2


def test_rule_allows_any_port_any_proto():
    rule = {"direction": "ingress", "protocol": None, "portRange": None}
    assert rule_allows(rule, 8080, "tcp", "ingress") is True


def test_rule_allows_respects_direction():
    rule = {"direction": "egress", "protocol": {"name": "tcp"}, "portRange": {"min": 443, "max": 443}}
    assert rule_allows(rule, 443, "tcp", "ingress") is False
