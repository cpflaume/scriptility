"""scheduled_tasks.py - Listet aktive Scheduled Tasks. Usage: python scheduled_tasks.py <host>"""

from __future__ import annotations

import sys

from _winrm import run_ps

PS = (
    "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | "
    "Select-Object TaskName, TaskPath, State | ConvertTo-Json"
)


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        sys.stderr.write("Usage: scheduled_tasks.py <host>\n")
        return 2
    sys.stdout.write(run_ps(argv[0], PS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
