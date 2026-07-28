"""Listet alle Security-Group-Rules eines STACKIT-Projekts.

Sammelt zuerst alle Security Groups, dann pro Group die Rules - weil
`stackit security-group list` keine Rules ausgibt, sondern nur Metadaten.

Usage:
    python list_firewall_rules.py <project_id> [--json]

ENV:
    STACKIT_SERVICE_ACCOUNT_TOKEN  Pflicht; wird von stackit-cli erwartet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.common import EXIT_OK, emit, get_logger, require_env  # noqa: E402
from lib.stackit import run_json  # noqa: E402

log = get_logger("stackit.firewall")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_id")
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def render_table(rows: list[dict]) -> None:
    print(f"{'Group':30} {'Direction':10} {'Proto':6} {'Port-Range':12} {'Remote'}")
    print("-" * 80)
    for r in rows:
        port = f"{r.get('port_min', '-')}-{r.get('port_max', '-')}"
        print(f"{r['group']:30.30} {r['direction']:10} {r['protocol']:6} {port:12} {r['remote']}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_env("STACKIT_SERVICE_ACCOUNT_TOKEN")

    groups = run_json(["security-group", "list", "--project-id", args.project_id])
    rows: list[dict] = []
    for g in groups:
        rules = run_json(
            ["security-group", "rule", "list", "--project-id", args.project_id, "--security-group-id", g["id"]]
        )
        for rule in rules:
            rows.append(
                {
                    "group": g.get("name", g["id"]),
                    "direction": rule.get("direction", "?"),
                    "protocol": (rule.get("protocol") or {}).get("name", "any"),
                    "port_min": (rule.get("portRange") or {}).get("min"),
                    "port_max": (rule.get("portRange") or {}).get("max"),
                    "remote": rule.get("remoteIpRange") or rule.get("remoteSecurityGroupId") or "any",
                }
            )

    emit(rows, json_output=args.json_output, table_fn=render_table)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
