"""check_port.py - TCP-Erreichbarkeitscheck mit optionalem JSON-Output.

Usage:
    python check_port.py --host 10.0.0.1 --port 443 [--timeout 3] [--json]

Exit:
    0 = erreichbar, 1 = nicht erreichbar, 2 = Aufruf-Fehler
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.common import EXIT_FAIL, EXIT_OK, emit, get_logger  # noqa: E402

log = get_logger("check_port")


def check_port(host: str, port: int, timeout: float) -> dict:
    """Versucht TCP-Connect; liefert strukturiertes Ergebnis."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = {"host": host, "port": port, "timeout": timeout, "open": False, "error": None}
    try:
        sock.connect((host, port))
        result["open"] = True
    except (TimeoutError, OSError) as exc:
        result["error"] = str(exc)
    finally:
        sock.close()
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--timeout", default=3.0, type=float)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = check_port(args.host, args.port, args.timeout)
    emit(
        result,
        json_output=args.json_output,
        table_fn=lambda r: log.info("%s:%s open=%s", r["host"], r["port"], r["open"]),
    )
    return EXIT_OK if result["open"] else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
