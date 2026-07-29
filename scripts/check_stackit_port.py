"""Prüft, ob ein bestimmter Port in einem STACKIT-Projekt freigeschaltet ist.

Liest (nur lesend, via ``lib.stackit``) alle Security Groups des Projekts und
deren Regeln und prüft, ob eine Regel den angefragten Port für das angegebene
Protokoll und die Richtung erlaubt. Eine Regel ohne Port-Range gilt als "alle
Ports", eine Regel ohne Protokoll als "alle Protokolle".

Usage:
    python check_stackit_port.py --project-id <id> --port 443
                                 [--protocol tcp] [--direction ingress] [--json]

Exit:
    0 = Port ist freigeschaltet, 1 = nicht freigeschaltet, 2 = Aufruf-Fehler

ENV:
    STACKIT_SERVICE_ACCOUNT_TOKEN  Pflicht; wird von stackit-cli erwartet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.common import EXIT_FAIL, EXIT_OK, emit, get_logger, require_env  # noqa: E402
from lib.stackit import run_stackit_query  # noqa: E402

log = get_logger("stackit.check-port")


def rule_allows(rule: dict, port: int, protocol: str, direction: str) -> bool:
    """True, wenn die Security-Group-Regel den Port/Protokoll/Richtung erlaubt."""
    if (rule.get("direction") or "").lower() != direction.lower():
        return False
    proto = (rule.get("protocol") or {}).get("name")
    if proto and proto.lower() != protocol.lower():
        return False
    port_range = rule.get("portRange") or {}
    pmin = port_range.get("min")
    pmax = port_range.get("max")
    if pmin is None and pmax is None:
        return True  # keine Port-Range => alle Ports offen
    lo = pmin if pmin is not None else 0
    hi = pmax if pmax is not None else 65535
    return lo <= port <= hi


def find_matches(project_id: str, port: int, protocol: str, direction: str) -> list[dict]:
    """Sammelt alle Regeln, die den Port freischalten."""
    groups = run_stackit_query(["security-group", "list", "--project-id", project_id])
    matches: list[dict] = []
    for g in groups:
        rules = run_stackit_query(
            ["security-group", "rule", "list", "--project-id", project_id, "--security-group-id", g["id"]]
        )
        for rule in rules:
            if rule_allows(rule, port, protocol, direction):
                matches.append(
                    {
                        "group": g.get("name", g["id"]),
                        "direction": rule.get("direction"),
                        "protocol": (rule.get("protocol") or {}).get("name", "any"),
                        "port_min": (rule.get("portRange") or {}).get("min"),
                        "port_max": (rule.get("portRange") or {}).get("max"),
                        "remote": rule.get("ipRange") or rule.get("remoteSecurityGroupId") or "any",
                    }
                )
    return matches


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project-id", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", default="tcp")
    p.add_argument("--direction", default="ingress")
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_env("STACKIT_SERVICE_ACCOUNT_TOKEN")
    matches = find_matches(args.project_id, args.port, args.protocol, args.direction)
    result = {
        "project_id": args.project_id,
        "port": args.port,
        "protocol": args.protocol,
        "direction": args.direction,
        "open": bool(matches),
        "matched_rules": matches,
    }
    emit(
        result,
        json_output=args.json_output,
        table_fn=lambda r: log.info(
            "Port %s/%s %s in Projekt %s: %s (%d passende Regel(n))",
            r["port"],
            r["protocol"],
            r["direction"],
            r["project_id"],
            "OFFEN" if r["open"] else "GESCHLOSSEN",
            len(r["matched_rules"]),
        ),
    )
    return EXIT_OK if result["open"] else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
