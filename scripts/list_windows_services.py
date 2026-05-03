"""Listet alle laufenden Windows-Services.

Usage:
    python list_services.py --host <host> [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.common import EXIT_OK, emit, get_logger  # noqa: E402
from lib.winrm import run_ps  # noqa: E402

log = get_logger("windows.services")

PS = "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName | ConvertTo-Json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", required=True)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def render_table(services: list[dict]) -> None:
    print(f"{'Name':30} {'DisplayName'}")
    print("-" * 80)
    for s in services:
        print(f"{s.get('Name', ''):30.30} {s.get('DisplayName', '')}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw = run_ps(args.host, PS)
    services = json.loads(raw) if raw.strip() else []
    if isinstance(services, dict):
        services = [services]
    emit(services, json_output=args.json_output, table_fn=render_table)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
