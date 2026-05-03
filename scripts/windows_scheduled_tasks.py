"""Listet aktive Scheduled Tasks (State != Disabled).

Usage:
    python scheduled_tasks.py --host <host> [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.common import EXIT_OK, emit, get_logger  # noqa: E402
from lib.winrm import run_ps  # noqa: E402

log = get_logger("windows.tasks")

PS = (
    "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | "
    "Select-Object TaskName, TaskPath, State | ConvertTo-Json"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", required=True)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def render_table(tasks: list[dict]) -> None:
    print(f"{'TaskName':40} {'State':10} {'TaskPath'}")
    print("-" * 100)
    for t in tasks:
        print(f"{t.get('TaskName', ''):40.40} {str(t.get('State', '')):10} {t.get('TaskPath', '')}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw = run_ps(args.host, PS)
    tasks = json.loads(raw) if raw.strip() else []
    if isinstance(tasks, dict):
        tasks = [tasks]
    emit(tasks, json_output=args.json_output, table_fn=render_table)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
