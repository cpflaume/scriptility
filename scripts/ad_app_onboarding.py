"""Liest AD-Onboarding-Voraussetzungen einer Applikation (on-prem Active Directory).

Vor dem Onboarding einer Applikation muessen deren Service-/gMSA-Konto samt
SPNs (aus denen die Hostnamen abgeleitet werden) sowie die Zugriffs-Gruppen
inkl. ihrer Mitglieder existieren. Dieses Skript liest diesen Ist-Zustand ueber
PowerShell (Get-AD*) via WinRM.

Modi:
  - Standard: reiner Dump des Ist-Zustands (Konto, Hostnamen, Gruppen+Mitglieder).
  - Mit --spec <datei.json>: zusaetzlicher Soll-/Ist-Abgleich (pass/fail).

Der --host-Zielrechner braucht das RSAT-Modul 'ActiveDirectory' (Domain-Member
Admin-/Jump-Host oder ein DC). Credentials via WIN_USER/WIN_PASSWORD (siehe
scripts/lib/winrm.py).

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
from lib.common import EXIT_FAIL, EXIT_OK, emit, get_logger  # noqa: E402
from lib.winrm import run_ps  # noqa: E402

log = get_logger("ad.onboarding")


def _ps_quote(value: str) -> str:
    """Escaped einen String fuer ein einfach-gequotetes PowerShell-Literal."""
    return value.replace("'", "''")


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


def fetch_account(host: str, identity: str) -> dict:
    """Liest das Service-/gMSA- bzw. User-Konto der Applikation via WinRM."""
    ident = _ps_quote(identity)
    ps = f"""Import-Module ActiveDirectory
$id = '{ident}'
$props = 'ServicePrincipalNames','Enabled','MemberOf'
$type = 'gMSA'
$a = Get-ADServiceAccount -Identity $id -Properties $props -ErrorAction SilentlyContinue
if (-not $a) {{
    $a = Get-ADUser -Identity $id -Properties $props -ErrorAction SilentlyContinue
    $type = 'user'
}}
if (-not $a) {{ Write-Output '{{}}'; exit 0 }}
[pscustomobject]@{{
    exists = $true
    type = $type
    enabled = [bool]$a.Enabled
    distinguishedName = $a.DistinguishedName
    servicePrincipalNames = @($a.ServicePrincipalNames)
    memberOf = @($a.MemberOf)
}} | ConvertTo-Json -Depth 4"""
    raw = run_ps(host, ps)
    data = json.loads(raw) if raw.strip() else {}
    if not data or not data.get("exists"):
        return {
            "identity": identity,
            "exists": False,
            "type": None,
            "enabled": None,
            "distinguishedName": None,
            "servicePrincipalNames": [],
            "memberOf": [],
        }
    data.setdefault("identity", identity)
    data["servicePrincipalNames"] = list(data.get("servicePrincipalNames") or [])
    data["memberOf"] = list(data.get("memberOf") or [])
    return data


def fetch_groups(host: str, names: list[str]) -> list[dict]:
    """Liest Gruppen inkl. rekursiver Mitglieder via WinRM."""
    if not names:
        return []
    ps_array = ", ".join(f"'{_ps_quote(n)}'" for n in names)
    ps = f"""Import-Module ActiveDirectory
$names = @({ps_array})
$out = foreach ($n in $names) {{
    $g = Get-ADGroup -Identity $n -ErrorAction SilentlyContinue
    if (-not $g) {{
        [pscustomobject]@{{ name = $n; exists = $false; distinguishedName = $null; members = @() }}
        continue
    }}
    $members = foreach ($m in (Get-ADGroupMember -Identity $g -Recursive -ErrorAction SilentlyContinue)) {{
        [pscustomobject]@{{ name = $m.SamAccountName; objectClass = $m.objectClass }}
    }}
    [pscustomobject]@{{
        name = $g.Name
        exists = $true
        distinguishedName = $g.DistinguishedName
        members = @($members)
    }}
}}
@($out) | ConvertTo-Json -Depth 5"""
    raw = run_ps(host, ps)
    data = json.loads(raw) if raw.strip() else []
    if isinstance(data, dict):
        data = [data]
    for g in data:
        members = g.get("members") or []
        if isinstance(members, dict):
            members = [members]
        g["members"] = members
    return data


def load_spec(path: str) -> dict:
    """Laedt eine JSON-Spec mit Soll-Zustand."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _discover_groups(host: str, pattern: str) -> list[str]:
    """Findet Gruppennamen ueber einen AD-Name-Filter (Get-ADGroup -Filter)."""
    pat = _ps_quote(pattern)
    ps = (
        "Import-Module ActiveDirectory\n"
        f"@(Get-ADGroup -Filter \"Name -like '{pat}'\" | Select-Object -ExpandProperty Name) | ConvertTo-Json"
    )
    raw = run_ps(host, ps)
    data = json.loads(raw) if raw.strip() else []
    if isinstance(data, str):
        data = [data]
    return list(data)


def resolve_group_names(args: argparse.Namespace, spec: dict | None, account: dict) -> list[str]:
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
        for g in _discover_groups(args.host, args.group_filter):
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
    p.add_argument("--host", required=True, help="AD-Host mit RSAT-Modul ActiveDirectory")
    p.add_argument("--account", required=True, help="SamAccountName des Service-/gMSA-Kontos")
    p.add_argument("--group", action="append", help="Zugriffs-Gruppe (mehrfach moeglich)")
    p.add_argument("--group-filter", dest="group_filter", help="AD-Name-Filter, z.B. 'App-XYZ-*'")
    p.add_argument("--spec", help="JSON-Datei mit Soll-Zustand -> pass/fail-Modus")
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spec = load_spec(args.spec) if args.spec else None

    account = fetch_account(args.host, args.account)
    group_names = resolve_group_names(args, spec, account)
    groups = fetch_groups(args.host, group_names)
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
