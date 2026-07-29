"""Tests für scripts/ad_app_onboarding.py"""

from __future__ import annotations

import json

import pytest

from scripts.ad_app_onboarding import (
    _ps_assign_array,
    evaluate,
    hostnames_from_spns,
    main,
)

# --- Kanonische Fake-WinRM-Antworten ---------------------------------------

ACCOUNT_JSON = json.dumps(
    {
        "exists": True,
        "type": "gMSA",
        "enabled": True,
        "distinguishedName": "CN=svc-app01,OU=Service,DC=corp",
        "servicePrincipalNames": ["HTTP/app.corp:443", "HTTP/app01.corp", "HOST/app.corp"],
        "memberOf": ["CN=App-XYZ-Users,OU=Groups,DC=corp"],
    }
)

GROUPS_JSON = json.dumps(
    [
        {
            "name": "App-XYZ-Users",
            "exists": True,
            "distinguishedName": "CN=App-XYZ-Users,OU=Groups,DC=corp",
            "members": [
                {"name": "jdoe", "objectClass": "user"},
                {"name": "asmith", "objectClass": "user"},
            ],
        }
    ]
)


def _fake_run_ps(account=ACCOUNT_JSON, groups=GROUPS_JSON):
    """Liefert eine side_effect-Funktion: 1. Aufruf = Konto, weitere = Gruppen."""
    calls = {"n": 0}

    def side_effect(host, script):  # noqa: ARG001
        calls["n"] += 1
        if "Get-ADServiceAccount" in script:
            return account
        return groups

    return side_effect


# --- reine Helfer -----------------------------------------------------------


def test_hostnames_from_spns_strips_port_service_and_dedupes():
    spns = ["HTTP/app.corp:443/svc", "HTTP/app.corp", "HOST/APP01.CORP", "invalid"]
    assert hostnames_from_spns(spns) == ["app.corp", "app01.corp"]


def test_hostnames_from_spns_empty():
    assert hostnames_from_spns([]) == []


def test_ps_assign_array_quotes_and_escapes():
    # Einfache Anfuehrungszeichen werden verdoppelt (PowerShell-Escaping).
    assert _ps_assign_array("Names", ["a", "o'brien"]) == "$Names = @('a', 'o''brien')"


# --- Aufruf-Fehler ----------------------------------------------------------


def test_usage_missing_args_exits_two():
    with pytest.raises(SystemExit) as exc:
        main([])  # fehlendes --host/--account
    assert exc.value.code == 2


# --- Dump-Modus -------------------------------------------------------------


def test_dump_happy_path(monkeypatch, capsys):
    monkeypatch.setattr("scripts.ad_app_onboarding.run_ps", _fake_run_ps())
    rc = main(["--host", "adhost", "--account", "svc-app01", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["account"]["exists"] is True
    assert out["hostnames"] == ["app.corp", "app01.corp"]
    assert out["groups"][0]["name"] == "App-XYZ-Users"
    member_names = {m["name"] for m in out["groups"][0]["members"]}
    assert member_names == {"jdoe", "asmith"}


def test_dump_account_missing(monkeypatch, capsys):
    monkeypatch.setattr("scripts.ad_app_onboarding.run_ps", _fake_run_ps(account="{}"))
    rc = main(["--host", "adhost", "--account", "ghost", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["account"]["exists"] is False
    assert out["hostnames"] == []


def test_group_filter_discovers_and_reads(monkeypatch, capsys):
    def side_effect(host, script):  # noqa: ARG001
        if "Get-ADServiceAccount" in script:
            return ACCOUNT_JSON
        if "-Filter" in script:  # ad_groups_by_filter.ps1
            return json.dumps(["App-XYZ-Users"])
        return GROUPS_JSON  # ad_groups.ps1

    monkeypatch.setattr("scripts.ad_app_onboarding.run_ps", side_effect)
    rc = main(["--host", "adhost", "--account", "svc-app01", "--group-filter", "App-XYZ-*", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert [g["name"] for g in out["groups"]] == ["App-XYZ-Users"]


# --- Spec-Modus (pass/fail) -------------------------------------------------


def _write_spec(tmp_path, spec):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return str(p)


def test_spec_pass(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.ad_app_onboarding.run_ps", _fake_run_ps())
    spec = _write_spec(
        tmp_path,
        {
            "account": "svc-app01",
            "type": "gMSA",
            "hostnames": ["app.corp", "app01.corp"],
            "groups": [{"name": "App-XYZ-Users", "members": ["jdoe", "asmith"]}],
        },
    )
    rc = main(["--host", "adhost", "--account", "svc-app01", "--spec", spec])
    assert rc == 0


def test_spec_fail_missing_member(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("scripts.ad_app_onboarding.run_ps", _fake_run_ps())
    spec = _write_spec(
        tmp_path,
        {"groups": [{"name": "App-XYZ-Users", "members": ["jdoe", "not-there"]}]},
    )
    rc = main(["--host", "adhost", "--account", "svc-app01", "--json", "--spec", spec])
    assert rc == 1
    report = json.loads(capsys.readouterr().out)
    failed = [c for c in report["checks"] if not c["ok"]]
    assert any(c["target"] == "App-XYZ-Users/not-there" for c in failed)


def test_spec_fail_missing_hostname(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.ad_app_onboarding.run_ps", _fake_run_ps())
    spec = _write_spec(tmp_path, {"hostnames": ["app.corp", "missing.corp"]})
    rc = main(["--host", "adhost", "--account", "svc-app01", "--spec", spec])
    assert rc == 1


# --- evaluate() direkt ------------------------------------------------------


def test_evaluate_account_type_mismatch():
    state = {
        "account": {"identity": "svc", "exists": True, "type": "user"},
        "hostnames": [],
        "groups": [],
    }
    report = evaluate(state, {"type": "gMSA"})
    assert report["ok"] is False
    assert any(c["check"] == "account-type" and not c["ok"] for c in report["checks"])
