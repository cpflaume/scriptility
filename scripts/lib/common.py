"""Shared helpers for Python scripts."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

# Einheitliche Exit-Codes für alle Skripte.
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


def get_logger(name: str) -> logging.Logger:
    """Logger mit einheitlichem Format. Level via LOG_LEVEL env (default INFO)."""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    return logging.getLogger(name)


def require_env(*names: str) -> dict[str, str]:
    """Liefert dict der ENV-Variablen oder beendet mit EXIT_USAGE."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        sys.stderr.write(f"Fehlende Umgebungsvariablen: {', '.join(missing)}\n")
        sys.exit(EXIT_USAGE)
    return {n: os.environ[n] for n in names}


def emit(data: Any, *, json_output: bool, table_fn=None) -> None:
    """Schreibt Ergebnis nach stdout - JSON oder via table_fn (callable)."""
    if json_output:
        json.dump(data, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    elif table_fn is not None:
        table_fn(data)
    else:
        sys.stdout.write(str(data) + "\n")
