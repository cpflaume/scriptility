"""Listet lokale Windows-Benutzer.

Usage:
    python list_users.py --host <host> [--json]

Setzt PowerShell 5.1+ / Windows Server 2016+ (wegen Get-LocalUser) voraus.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import EXIT_OK, emit, get_logger  # noqa: E402
from windows._winrm import run_ps  # noqa: E402

log = get_logger("windows.users")

PS = "Get-LocalUser | Select-Object Name, Enabled, LastLogon | ConvertTo-Json -Depth 2"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", required=True)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def render_table(users: list[dict]) -> None:
    print(f"{'Name':30} {'Enabled':8} {'LastLogon'}")
    print("-" * 70)
    for u in users:
        print(f"{u.get('Name', ''):30.30} {str(u.get('Enabled', '')):8} {u.get('LastLogon', '')}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw = run_ps(args.host, PS)
    users = json.loads(raw) if raw.strip() else []
    if isinstance(users, dict):
        users = [users]
    emit(users, json_output=args.json_output, table_fn=render_table)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
