"""list_users.py - Listet lokale Windows-Benutzer.

Usage: python list_users.py <host>
"""

from __future__ import annotations

import sys

from _winrm import run_ps

PS = "Get-LocalUser | Select-Object Name, Enabled, LastLogon | ConvertTo-Json -Depth 2"


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        sys.stderr.write("Usage: list_users.py <host>\n")
        return 2
    sys.stdout.write(run_ps(argv[0], PS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
