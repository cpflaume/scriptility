"""{{NAME}}.py - TODO: kurze Beschreibung.

Usage:
    python {{NAME}}.py --foo bar [--json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from lib.common import EXIT_OK, emit, get_logger  # noqa: E402

log = get_logger("{{NAME}}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--foo", required=True)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    result = {"foo": args.foo}
    emit(result, json_output=args.json_output, table_fn=lambda r: log.info("%s", r))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
