"""Tests für scripts/ad_app_onboarding.py (LDAP-Pfad, gemockt)."""

from __future__ import annotations

import json

import pytest

from scripts.ad_app_onboarding import (
    evaluate,
    fetch_account,
    hostnames_from_spns,
    main,
)

# --- Kanonische Fake-LDAP-Einträge -----------------------------------------

ACCOUNT_ENTRY = {
    "dn": "CN=svc-app01,OU=Service,DC=corp",
    "attrs": {
        "sAMAccountName": ["svc-app01"],
        # gMSA: enthält die spezifische Klasse -> type == 'gMSA'.
        "objectClass": ["top", "computer", "msDS-GroupManagedServiceAccount"],
        "userAccountControl": [4096],  # ACCOUNTDISABLE-Bit nicht gesetzt -> enabled
        "distinguishedName": ["CN=svc-app01,OU=Service,DC=corp"],
        "servicePrincipalName": ["HTTP/app.corp:443", "HTTP/app01.corp", "HOST/app.corp"],
        "memberOf": ["CN=App-XYZ-Users,OU=Groups,DC=corp"],
    },
}

GROUP_ENTRY = {
    "dn": "CN=App-XYZ-Users,OU=Groups,DC=corp",
    "attrs": {
        "cn": ["App-XYZ-Users"],
        "distinguishedName": ["CN=App-XYZ-Users,OU=Groups,DC=corp"],
    },
}

MEMBER_ENTRIES = [
    {"dn": "CN=jdoe,DC=corp", "attrs": {"sAMAccountName": ["jdoe"], "objectClass": ["top", "person", "user"]}},
    {"dn": "CN=asmith,DC=corp", "attrs": {"sAMAccountName": ["asmith"], "objectClass": ["top", "person", "user"]}},
]

RULE = "1.2.840.113556.1.4.1941"


def _fake_search(*, account=ACCOUNT_ENTRY, group=GROUP_ENTRY, members=MEMBER_ENTRIES, filter_groups=None):
    """Baut eine search()-Ersatzfunktion, die anhand des LDAP-Filters dispatcht."""

    def search(conn, base, search_filter, attributes):  # noqa: ARG001
        if RULE in search_filter:  # rekursive Mitglieder
            return list(members)
        if "msDS-GroupManagedServiceAccount" in search_filter:  # Konto
            return [account] if account is not None else []
        if "objectClass=group" in search_filter and "sAMAccountName=" in search_filter:  # Gruppe by name
            return [group] if group is not None else []
        if "objectClass=group" in search_filter:  # --group-filter (cn-Wildcard)
            return list(filter_groups or [])
        return []

    return search


@pytest.fixture
def patch_ldap(monkeypatch):
    """Neutralisiert connect()/base_dn() und erlaubt, search() zu setzen."""
    monkeypatch.setattr("scripts.ad_app_onboarding.connect", lambda _host: object())
    monkeypatch.setattr("scripts.ad_app_onboarding.base_dn", lambda _conn: "DC=corp")

    def set_search(fn):
        monkeypatch.setattr("scripts.ad_app_onboarding.search", fn)

    return set_search


# --- reine Helfer -----------------------------------------------------------


def test_hostnames_from_spns_strips_port_service_and_dedupes():
    spns = ["HTTP/app.corp:443/svc", "HTTP/app.corp", "HOST/APP01.CORP", "invalid"]
    assert hostnames_from_spns(spns) == ["app.corp", "app01.corp"]


def test_hostnames_from_spns_empty():
    assert hostnames_from_spns([]) == []


def test_fetch_account_maps_type_and_enabled(patch_ldap):
    patch_ldap(_fake_search())
    acc = fetch_account(object(), "svc-app01")
    assert acc["exists"] is True
    assert acc["type"] == "gMSA"
    assert acc["enabled"] is True
    assert acc["servicePrincipalNames"][0] == "HTTP/app.corp:443"


def test_fetch_account_disabled_bit(patch_ldap):
    entry = json.loads(json.dumps(ACCOUNT_ENTRY))  # deep copy
    entry["attrs"]["userAccountControl"] = [514]  # 0x2 gesetzt -> disabled
    entry["attrs"]["objectClass"] = ["top", "person", "user"]  # kein gMSA -> type user
    patch_ldap(_fake_search(account=entry))
    acc = fetch_account(object(), "jdoe")
    assert acc["type"] == "user"
    assert acc["enabled"] is False


# --- Aufruf-Fehler ----------------------------------------------------------


def test_usage_missing_args_exits_two():
    with pytest.raises(SystemExit) as exc:
        main([])  # fehlendes --host/--account
    assert exc.value.code == 2


# --- Dump-Modus -------------------------------------------------------------


def test_dump_happy_path(patch_ldap, capsys):
    patch_ldap(_fake_search())
    rc = main(["--host", "dc01", "--account", "svc-app01", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["account"]["exists"] is True
    assert out["hostnames"] == ["app.corp", "app01.corp"]
    assert out["groups"][0]["name"] == "App-XYZ-Users"
    member_names = {m["name"] for m in out["groups"][0]["members"]}
    assert member_names == {"jdoe", "asmith"}


def test_dump_account_missing(patch_ldap, capsys):
    patch_ldap(_fake_search(account=None))
    rc = main(["--host", "dc01", "--account", "ghost", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["account"]["exists"] is False
    assert out["hostnames"] == []


def test_group_filter_discovers_and_reads(patch_ldap, capsys):
    patch_ldap(_fake_search(filter_groups=[GROUP_ENTRY]))
    rc = main(["--host", "dc01", "--account", "svc-app01", "--group-filter", "App-XYZ-*", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert [g["name"] for g in out["groups"]] == ["App-XYZ-Users"]


# --- Spec-Modus (pass/fail) -------------------------------------------------


def _write_spec(tmp_path, spec):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return str(p)


def test_spec_pass(patch_ldap, tmp_path):
    patch_ldap(_fake_search())
    spec = _write_spec(
        tmp_path,
        {
            "account": "svc-app01",
            "type": "gMSA",
            "hostnames": ["app.corp", "app01.corp"],
            "groups": [{"name": "App-XYZ-Users", "members": ["jdoe", "asmith"]}],
        },
    )
    rc = main(["--host", "dc01", "--account", "svc-app01", "--spec", spec])
    assert rc == 0


def test_spec_fail_missing_member(patch_ldap, tmp_path, capsys):
    patch_ldap(_fake_search())
    spec = _write_spec(
        tmp_path,
        {"groups": [{"name": "App-XYZ-Users", "members": ["jdoe", "not-there"]}]},
    )
    rc = main(["--host", "dc01", "--account", "svc-app01", "--json", "--spec", spec])
    assert rc == 1
    report = json.loads(capsys.readouterr().out)
    failed = [c for c in report["checks"] if not c["ok"]]
    assert any(c["target"] == "App-XYZ-Users/not-there" for c in failed)


def test_spec_fail_missing_hostname(patch_ldap, tmp_path):
    patch_ldap(_fake_search())
    spec = _write_spec(tmp_path, {"hostnames": ["app.corp", "missing.corp"]})
    rc = main(["--host", "dc01", "--account", "svc-app01", "--spec", spec])
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
