#!/usr/bin/env python3
"""Regeneriert den AUTO-GENERATED-Block in Taskfile.yml aus scripts/*.{sh,py}.

Vorhandene Einträge mit angepassten desc/cmds werden idempotent neu erzeugt:
desc-Zeilen werden behalten, wenn sich der Task-Name nicht ändert; cmds werden
immer neu erzeugt, damit Pfade konsistent bleiben.

Skripte unter scripts/lib/ und Dotfiles werden ignoriert.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

START_MARKER = "# >>> AUTO-GENERATED SCRIPTS"
END_MARKER = "# <<< END AUTO-GENERATED <<<"

ROOT = Path(__file__).resolve().parents[2]
TASKFILE = ROOT / "Taskfile.yml"
SCRIPTS = ROOT / "scripts"


def discover_scripts() -> list[tuple[str, str, str]]:
    """Liefert (task_name, runner, script_path) für jedes registrierbare Skript.

    Bei Stem-Kollisionen (foo.sh + foo.py) wird das Python-Skript als '<stem>-py'
    registriert; der bash-Variante gehört der Basisname.
    """
    files = [
        p
        for p in sorted(SCRIPTS.iterdir())
        if p.is_file() and not p.name.startswith((".", "_", "__")) and p.suffix in {".sh", ".py"}
    ]
    stems = {p.stem for p in files if p.suffix == ".sh"}
    out: list[tuple[str, str, str]] = []
    for p in files:
        if p.suffix == ".sh":
            runner = "bash"
            task_name = p.stem.replace("_", "-")
        else:
            runner = "uv run python"
            base = p.stem.replace("_", "-")
            task_name = f"{base}-py" if p.stem in stems else base
        out.append((task_name, runner, f"scripts/{p.name}"))
    out.sort(key=lambda t: t[0])
    return out


def parse_existing_descs(block: str) -> dict[str, str]:
    """Extrahiert vorhandene desc-Zeilen pro Task-Name aus dem alten Block."""
    descs: dict[str, str] = {}
    current: str | None = None
    for line in block.splitlines():
        m = re.match(r"^  ([a-z][a-z0-9-]*):\s*$", line)
        if m:
            current = m.group(1)
            continue
        if current and line.lstrip().startswith("desc:"):
            descs[current] = line.split("desc:", 1)[1].strip()
            current = None
    return descs


def render_block(scripts: list[tuple[str, str, str]], descs: dict[str, str]) -> str:
    lines: list[str] = []
    for task_name, runner, script_path in scripts:
        desc = descs.get(task_name, f"'TODO: Beschreibung. Usage: task {task_name} -- <args>'")
        lines.append(f"  {task_name}:")
        lines.append(f"    desc: {desc}")
        lines.append(f"    cmds: ['{runner} {script_path} {{{{.CLI_ARGS}}}}']")
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def replace_block(content: str, new_block: str) -> str:
    pattern = re.compile(
        r"(" + re.escape(START_MARKER) + r"[^\n]*\n)(.*?)(  " + re.escape(END_MARKER) + r")",
        re.DOTALL,
    )
    if not pattern.search(content):
        sys.stderr.write(f"Marker fehlen in {TASKFILE}\n")
        sys.exit(1)
    return pattern.sub(lambda m: m.group(1) + new_block + "\n  " + END_MARKER, content)


def main() -> int:
    content = TASKFILE.read_text()
    m = re.search(
        re.escape(START_MARKER) + r"[^\n]*\n(.*?)  " + re.escape(END_MARKER),
        content,
        re.DOTALL,
    )
    old_block = m.group(1) if m else ""
    descs = parse_existing_descs(old_block)
    scripts = discover_scripts()
    new_block = render_block(scripts, descs)
    new_content = replace_block(content, new_block)
    if new_content != content:
        TASKFILE.write_text(new_content)
        sys.stderr.write(f"Aktualisiert: {TASKFILE.relative_to(ROOT)} ({len(scripts)} Skripte)\n")
    else:
        sys.stderr.write("Keine Änderungen.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
