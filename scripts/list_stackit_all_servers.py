"""Listet alle STACKIT-Compute-Server über **alle** Projekte hinweg als CSV.

Ermittelt zuerst alle Projekte des Service Accounts (``stackit project list``),
dann pro Projekt die Server (``stackit server list``). Alle Aufrufe laufen über
den Read-Only-Guard aus ``lib.stackit`` — es wird garantiert nichts verändert.

Standardausgabe ist CSV nach stdout (pipebar); ``--json`` liefert dieselbe
Struktur maschinenlesbar. Logs gehen nach stderr.

Usage:
    python list_stackit_all_servers.py [--json]

ENV:
    STACKIT_SERVICE_ACCOUNT_TOKEN  Pflicht; wird von stackit-cli erwartet.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.common import EXIT_OK, emit, get_logger, require_env  # noqa: E402
from lib.stackit import run_json  # noqa: E402

log = get_logger("stackit.all-servers")

FIELDS = [
    "project_id",
    "project_name",
    "server_id",
    "server_name",
    "status",
    "machine_type",
    "availability_zone",
]


def collect_servers() -> list[dict]:
    """Sammelt alle Server über alle Projekte des Service Accounts."""
    projects = run_json(["project", "list"])
    rows: list[dict] = []
    for p in projects:
        pid = p.get("projectId") or p.get("id")
        if not pid:
            log.warning("Projekt ohne ID übersprungen: %s", p)
            continue
        pname = p.get("name", "")
        servers = run_json(["server", "list", "--project-id", pid])
        for s in servers:
            rows.append(
                {
                    "project_id": pid,
                    "project_name": pname,
                    "server_id": s.get("id", ""),
                    "server_name": s.get("name", ""),
                    "status": s.get("status", ""),
                    "machine_type": s.get("machineType", ""),
                    "availability_zone": s.get("availabilityZone", ""),
                }
            )
    return rows


def render_csv(rows: list[dict]) -> None:
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_env("STACKIT_SERVICE_ACCOUNT_TOKEN")
    rows = collect_servers()
    log.info("%d Server über alle Projekte gefunden", len(rows))
    emit(rows, json_output=args.json_output, table_fn=render_csv)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
