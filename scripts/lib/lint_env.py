#!/usr/bin/env python3
"""Verifiziert, dass jede require_env-/require_cmd-Variable in .env.example dokumentiert ist.

Ziel: ENV-Variablen mit gleichem Zweck haben in allen Skripten den **gleichen
Namen**. .env.example ist die kanonische Liste. Jeder neue ENV-Bezug muss dort
landen — sonst CI rot.

Erkennt:
- bash: `require_env VAR1 VAR2 ...`
- python: `require_env("VAR1", "VAR2", ...)`
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
ENV_EXAMPLE = ROOT / ".env.example"

# Dateien, die require_env DEFINIEREN oder DOKUMENTIEREN, nicht aufrufen.
EXCLUDE = {"lib/common.sh", "lib/common.py", "lib/lint_env.py"}

BASH_CALL = re.compile(r"\brequire_env\s+([A-Z][A-Z0-9_\s]*?)(?:$|#|;|\|\||&&)", re.MULTILINE)
PY_CALL = re.compile(r"require_env\(\s*([^)]*)\)")
PY_ARG = re.compile(r'["\']([A-Z][A-Z0-9_]*)["\']')
ENV_LINE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)


def documented_vars() -> set[str]:
    return set(ENV_LINE.findall(ENV_EXAMPLE.read_text()))


def referenced_vars() -> dict[str, list[Path]]:
    refs: dict[str, list[Path]] = {}
    for p in SCRIPTS.rglob("*"):
        if not p.is_file() or p.suffix not in {".sh", ".py"}:
            continue
        if str(p.relative_to(SCRIPTS)) in EXCLUDE:
            continue
        text = p.read_text(errors="replace")
        names: set[str] = set()
        if p.suffix == ".sh":
            for m in BASH_CALL.finditer(text):
                names.update(m.group(1).split())
        else:
            for m in PY_CALL.finditer(text):
                names.update(PY_ARG.findall(m.group(1)))
        for n in names:
            refs.setdefault(n, []).append(p.relative_to(ROOT))
    return refs


def main() -> int:
    documented = documented_vars()
    refs = referenced_vars()
    undocumented = {v: paths for v, paths in refs.items() if v not in documented}
    if undocumented:
        sys.stderr.write(
            "FEHLER: ENV-Variablen werden referenziert, sind aber nicht in .env.example dokumentiert.\n"
            "Trage sie dort ein (und in docs/REQUIREMENTS.md, falls Credentials), oder benenne sie\n"
            "auf einen bereits existierenden Namen um.\n\n"
        )
        for var in sorted(undocumented):
            paths = ", ".join(str(p) for p in undocumented[var])
            sys.stderr.write(f"  {var}  ({paths})\n")
        return 1
    sys.stderr.write(f"OK: {len(refs)} ENV-Variablen referenziert, alle in .env.example dokumentiert.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
