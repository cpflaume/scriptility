"""Liest AD-Onboarding-Voraussetzungen einer Applikation (on-prem Active Directory).

Vor dem Onboarding einer Applikation muessen deren Service-/gMSA-Konto samt
SPNs (aus denen die Hostnamen abgeleitet werden) sowie die Zugriffs-Gruppen
inkl. ihrer Mitglieder existieren. Dieses Skript liest diesen Ist-Zustand per
LDAP(S) direkt vom Domain Controller (Simple Bind mit User + Passwort); ein
Windows-Jump-Host oder RSAT-PowerShell ist nicht mehr noetig. Es wird nur
gelesen, nie geschrieben.

Modi:
  - Standard: reiner Dump des Ist-Zustands (Konto, Hostnamen, Gruppen+Mitglieder).
  - Mit --spec <datei.json>: zusaetzlicher Soll-/Ist-Abgleich (pass/fail).

Voraussetzungen (Details: docs/REQUIREMENTS.md, Abschnitt 'ad-app-onboarding'):
  - ENV AD_USER/AD_PASSWORD (LDAP-Simple-Bind); optional AD_PORT/AD_USE_SSL/
    AD_TLS_VERIFY/AD_CA_BUNDLE/AD_BASE_DN (siehe scripts/lib/ad.py und .env.example).
  - --host ist ein per LDAP(S) erreichbarer Domain Controller (Default Port 636).
  - AD_USER hat Lese-Rechte in der AD (Konten, Gruppen, Mitgliedschaften) — ein
    normaler Domaenen-Benutzer genuegt in der Regel.
  - --spec erwartet eine lokal lesbare JSON-Datei mit dem Soll-Zustand.

Usage:
    python ad_app_onboarding.py --host <adhost> --account <sam> [--group NAME ...]
        [--group-filter <pattern>] [--spec <datei.json>] [--json]

Exit:
    0  ok (Dump, bzw. alle Voraussetzungen im Spec-Modus erfuellt)
    1  im Spec-Modus: mind. eine Voraussetzung nicht erfuellt
    2  Aufruf-/Verbindungsfehler
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.ad import (  # noqa: E402
    RECURSIVE_MEMBER_RULE,
    base_dn,
    connect,
    escape_filter,
    escape_filter_wildcard,
    search,
)
from lib.common import EXIT_FAIL, EXIT_OK, emit, get_logger  # noqa: E402

log = get_logger("ad.onboarding")

# Attribute, die wir vom Konto lesen (read-only).
ACCOUNT_ATTRS = [
    "sAMAccountName",
    "objectClass",
    "userAccountControl",
    "distinguishedName",
    "servicePrincipalName",
    "memberOf",
]
# ACCOUNTDISABLE-Bit im userAccountControl.
UAC_ACCOUNTDISABLE = 0x2


def _as_list(value) -> list:
    """Normalisiert ldap3-Attributwerte (Skalar oder Liste) auf eine Liste."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _first(value):
    """Erster Wert eines ldap3-Attributs, oder None."""
    values = _as_list(value)
    return values[0] if values else None


def _leaf_class(object_classes: list[str]) -> str | None:
    """Strukturelle Leaf-Klasse (AD-objectClass ist allgemein->spezifisch sortiert)."""
    classes = _as_list(object_classes)
    return str(classes[-1]) if classes else None


def _cn_from_dn(dn: str) -> str:
    """Extrahiert den CN aus einem DistinguishedName (CN=Foo,OU=... -> Foo)."""
    first = dn.split(",", 1)[0]
    if "=" in first:
        return first.split("=", 1)[1]
    return first


def hostnames_from_spns(spns: list[str]) -> list[str]:
    """Leitet Hostnamen aus SPNs ab (HTTP/app.corp:443/svc -> app.corp), dedupliziert."""
    hosts: list[str] = []
    seen: set[str] = set()
    for spn in spns:
        if "/" not in spn:
            continue
        host = spn.split("/", 1)[1]  # Teil nach dem Dienst
        host = host.split("/", 1)[0]  # evtl. /servicename abschneiden
        host = host.split(":", 1)[0]  # evtl. :port abschneiden
        host = host.strip().lower()
        if host and host not in seen:
            seen.add(host)
            hosts.append(host)
    return hosts


def _absent_account(identity: str) -> dict:
    return {
        "identity": identity,
        "exists": False,
        "type": None,
        "enabled": None,
        "distinguishedName": None,
        "servicePrincipalNames": [],
        "memberOf": [],
    }


def fetch_account(conn, identity: str) -> dict:
    """Liest das Service-/gMSA- bzw. User-Konto der Applikation via LDAP."""
    esc = escape_filter(identity)
    flt = (
        "(&(|(objectClass=user)(objectClass=msDS-GroupManagedServiceAccount))"
        f"(sAMAccountName={esc}))"
    )
    entries = search(conn, base_dn(conn), flt, ACCOUNT_ATTRS)
    if not entries:
        return _absent_account(identity)
    attrs = entries[0]["attrs"]
    classes = [str(c).lower() for c in _as_list(attrs.get("objectClass"))]
    acc_type = "gMSA" if "msds-groupmanagedserviceaccount" in classes else "user"
    uac = int(_first(attrs.get("userAccountControl")) or 0)
    return {
        "identity": identity,
        "exists": True,
        "type": acc_type,
        "enabled": not (uac & UAC_ACCOUNTDISABLE),
        "distinguishedName": _first(attrs.get("distinguishedName")) or entries[0]["dn"],
        "servicePrincipalNames": [str(s) for s in _as_list(attrs.get("servicePrincipalName"))],
        "memberOf": [str(m) for m in _as_list(attrs.get("memberOf"))],
    }


def _fetch_group_members(conn, group_dn: str) -> list[dict]:
    """Rekursive Mitglieder einer Gruppe via LDAP_MATCHING_RULE_IN_CHAIN."""
    flt = f"(memberOf:{RECURSIVE_MEMBER_RULE}:={escape_filter(group_dn)})"
    entries = search(conn, base_dn(conn), flt, ["sAMAccountName", "objectClass"])
    members = []
    for e in entries:
        attrs = e["attrs"]
        members.append(
            {
                "name": _first(attrs.get("sAMAccountName")),
                "objectClass": _leaf_class(attrs.get("objectClass")),
            }
        )
    return members


def fetch_groups(conn, names: list[str]) -> list[dict]:
    """Liest Gruppen inkl. rekursiver Mitglieder via LDAP."""
    out: list[dict] = []
    for name in names:
        esc = escape_filter(name)
        flt = f"(&(objectClass=group)(|(sAMAccountName={esc})(cn={esc})))"
        entries = search(conn, base_dn(conn), flt, ["cn", "distinguishedName"])
        if not entries:
            out.append({"name": name, "exists": False, "distinguishedName": None, "members": []})
            continue
        dn = _first(entries[0]["attrs"].get("distinguishedName")) or entries[0]["dn"]
        cn = _first(entries[0]["attrs"].get("cn")) or name
        out.append(
            {
                "name": str(cn),
                "exists": True,
                "distinguishedName": dn,
                "members": _fetch_group_members(conn, dn),
            }
        )
    return out


def load_spec(path: str) -> dict:
    """Laedt eine JSON-Spec mit Soll-Zustand."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _discover_groups(conn, pattern: str) -> list[str]:
    """Findet Gruppennamen ueber einen cn-Wildcard-Filter (AD 'Name -like ...')."""
    flt = f"(&(objectClass=group)(cn={escape_filter_wildcard(pattern)}))"
    entries = search(conn, base_dn(conn), flt, ["cn"])
    return [str(_first(e["attrs"].get("cn"))) for e in entries if _first(e["attrs"].get("cn"))]


def resolve_group_names(conn, args: argparse.Namespace, spec: dict | None, account: dict) -> list[str]:
    """Ermittelt die zu pruefenden Gruppen: Spec + --group + --group-filter,
    sonst Fallback auf die MemberOf-Gruppen des Kontos."""
    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    if spec:
        for g in spec.get("groups", []):
            add(g["name"])
    for g in args.group or []:
        add(g)
    if args.group_filter:
        for g in _discover_groups(conn, args.group_filter):
            add(g)

    if not names:
        for dn in account.get("memberOf", []):
            add(_cn_from_dn(dn))
    return names


def _members_lower(group: dict) -> set[str]:
    return {str(m.get("name", "")).lower() for m in group.get("members", [])}


def evaluate(state: dict, spec: dict) -> dict:
    """Gleicht Ist-Zustand gegen die Spec ab und liefert einen pass/fail-Report."""
    checks: list[dict] = []
    account = state["account"]

    checks.append(
        {
            "check": "account-exists",
            "target": account["identity"],
            "ok": bool(account["exists"]),
        }
    )
    if spec.get("type") and account["exists"]:
        checks.append(
            {
                "check": "account-type",
                "target": account["identity"],
                "expected": spec["type"],
                "actual": account["type"],
                "ok": account["type"] == spec["type"],
            }
        )

    derived = set(state["hostnames"])
    for hostname in spec.get("hostnames", []):
        checks.append(
            {
                "check": "hostname-registered",
                "target": hostname,
                "ok": hostname.lower() in derived,
            }
        )

    groups_by_name = {g["name"].lower(): g for g in state["groups"]}
    for spec_group in spec.get("groups", []):
        gname = spec_group["name"]
        actual = groups_by_name.get(gname.lower())
        exists = bool(actual and actual.get("exists"))
        checks.append({"check": "group-exists", "target": gname, "ok": exists})
        if not exists:
            for member in spec_group.get("members", []):
                checks.append({"check": "group-member", "target": f"{gname}/{member}", "ok": False})
            continue
        present = _members_lower(actual)
        for member in spec_group.get("members", []):
            checks.append(
                {
                    "check": "group-member",
                    "target": f"{gname}/{member}",
                    "ok": member.lower() in present,
                }
            )

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "account": account["identity"], "checks": checks, "state": state}


def render_state(state: dict) -> None:
    """Menschlich lesbarer Dump des Ist-Zustands nach stdout."""
    acc = state["account"]
    print(f"Account : {acc['identity']}  exists={acc['exists']} type={acc['type']} enabled={acc['enabled']}")
    print(f"SPNs    : {', '.join(acc['servicePrincipalNames']) or '-'}")
    print(f"Hosts   : {', '.join(state['hostnames']) or '-'}")
    print("Groups  :")
    if not state["groups"]:
        print("  -")
    for g in state["groups"]:
        if g.get("exists"):
            members = ", ".join(m.get("name", "") for m in g.get("members", []))
            print(f"  [x] {g['name']}: {members or '(keine Mitglieder)'}")
        else:
            print(f"  [ ] {g['name']}: FEHLT")


def render_report(report: dict) -> None:
    """Menschlich lesbarer pass/fail-Report nach stdout."""
    for c in report["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        print(f"[{mark}] {c['check']}: {c['target']}")
    ergebnis = "OK - alle Voraussetzungen erfuellt" if report["ok"] else "NICHT erfuellt"
    print(f"\nErgebnis: {ergebnis}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", required=True, help="Domain Controller (per LDAPS erreichbar)")
    p.add_argument("--account", required=True, help="SamAccountName des Service-/gMSA-Kontos")
    p.add_argument("--group", action="append", help="Zugriffs-Gruppe (mehrfach moeglich)")
    p.add_argument("--group-filter", dest="group_filter", help="AD-Name-Filter, z.B. 'App-XYZ-*'")
    p.add_argument("--spec", help="JSON-Datei mit Soll-Zustand -> pass/fail-Modus")
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spec = load_spec(args.spec) if args.spec else None

    conn = connect(args.host)
    account = fetch_account(conn, args.account)
    group_names = resolve_group_names(conn, args, spec, account)
    groups = fetch_groups(conn, group_names)
    state = {
        "account": account,
        "hostnames": hostnames_from_spns(account["servicePrincipalNames"]),
        "groups": groups,
    }

    if spec is None:
        emit(state, json_output=args.json_output, table_fn=render_state)
        return EXIT_OK

    report = evaluate(state, spec)
    emit(report, json_output=args.json_output, table_fn=render_report)
    return EXIT_OK if report["ok"] else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
