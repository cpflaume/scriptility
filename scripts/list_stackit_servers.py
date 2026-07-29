"""Listet alle STACKIT-Compute-Server eines Projekts inkl. Detail-Infos.

Pro Server werden (rein lesend, via ``lib.stackit``) angereichert: Status &
Power-State (RUNNING/STOPPED), OS/Image, Flavor (vCPU/RAM) sowie private und
öffentliche IPs. Standardausgabe ist eine kompakte Tabelle nach stdout;
``--json`` liefert alle Felder maschinenlesbar. Logs gehen nach stderr.

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
from lib.stackit import ServerEnricher, run_json  # noqa: E402

log = get_logger("stackit.servers")


def collect_servers(project_id: str) -> list[dict]:
    enricher = ServerEnricher()
    servers = run_json(["server", "list", "--project-id", project_id])
    return [enricher.enrich(s, project_id) for s in servers]


def render_table(rows: list[dict]) -> None:
    header = (
        f"{'Name':22} {'Power':9} {'OS':18} {'vCPU':>4} {'RAM/GB':>6} "
        f"{'Private-IP':16} {'Public-IP':16} {'Machine-Type'}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        os_label = " ".join(x for x in (r["os_distro"], r["os_version"]) if x) or r["os"] or "-"
        print(
            f"{r['name']:22.22} {r['power_status']:9.9} {os_label:18.18} "
            f"{str(r['vcpus'] if r['vcpus'] is not None else '-'):>4} "
            f"{str(r['ram_gb'] if r['ram_gb'] is not None else '-'):>6} "
            f"{(r['private_ips'] or '-'):16.16} {(r['public_ips'] or '-'):16.16} {r['machine_type']}"
        )


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
