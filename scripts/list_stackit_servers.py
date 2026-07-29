"""Listet alle STACKIT-Compute-Server eines Projekts mit Status.

Alle stackit-Aufrufe laufen über den Read-Only-Guard aus ``lib.stackit`` — es
wird garantiert nichts verändert. Standardausgabe ist eine Tabelle nach stdout;
``--json`` liefert die Rohstruktur maschinenlesbar. Logs gehen nach stderr.

Usage:
    python list_stackit_servers.py <project_id> [--json]

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

log = get_logger("stackit.servers")


def collect_servers(project_id: str) -> list[dict]:
    servers = run_json(["server", "list", "--project-id", project_id])
    return [
        {
            "id": s.get("id", ""),
            "name": s.get("name", ""),
            "status": s.get("status", ""),
            "machine_type": s.get("machineType", ""),
        }
        for s in servers
    ]


def render_table(rows: list[dict]) -> None:
    print(f"{'ID':38} {'Name':24} {'Status':12} {'Machine-Type'}")
    print("-" * 90)
    for r in rows:
        print(f"{r['id']:38.38} {r['name']:24.24} {r['status']:12.12} {r['machine_type']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_id")
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_env("STACKIT_SERVICE_ACCOUNT_TOKEN")
    rows = collect_servers(args.project_id)
    log.info("%d Server in Projekt %s gefunden", len(rows), args.project_id)
    emit(rows, json_output=args.json_output, table_fn=render_table)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
