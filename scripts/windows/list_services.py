"""list_services.py - Listet alle laufenden Windows-Services. Usage: python list_services.py <host>"""

from __future__ import annotations

import sys

from _winrm import run_ps

PS = "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName | ConvertTo-Json"


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        sys.stderr.write("Usage: list_services.py <host>\n")
        return 2
    sys.stdout.write(run_ps(argv[0], PS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
