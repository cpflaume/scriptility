"""Zentrale, **nur lesende** Anbindung an die STACKIT-CLI.

Alle Python-Skripte, die stackit aufrufen, gehen über diesen Helfer. Er setzt
eine Default-Deny-Allowlist durch: nur lesende Verben (``list``, ``describe``)
dürfen ausgeführt werden. Jeder Versuch, einen mutierenden Command (``create``,
``update``, ``delete``, ...) abzusetzen, wird abgelehnt, *bevor* stackit
gestartet wird — so kann kein Skript versehentlich Infrastruktur verändern.

ENV:
    STACKIT_SERVICE_ACCOUNT_TOKEN  Pflicht; wird von stackit-cli erwartet.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import EXIT_FAIL, get_logger  # noqa: E402

log = get_logger("stackit")

# Default-Deny: ausschließlich diese Verben sind erlaubt. Alles andere gilt als
# potenziell mutierend und wird blockiert.
READ_VERBS = frozenset({"list", "describe"})


class MutatingCommandError(RuntimeError):
    """Ausgelöst, wenn ein nicht-lesender stackit-Command versucht wird."""


def _action_verb(args: list[str]) -> str | None:
    """Aktions-Verb eines stackit-Commands: letztes positionales Token vor dem ersten Flag.

    Bei stackit steht der Resource-Pfad plus Aktion immer vor den Optionen,
    z. B. ``server list --project-id X`` -> ``list`` oder
    ``security-group rule list ...`` -> ``list``.
    """
    positional: list[str] = []
    for tok in args:
        if tok.startswith("-"):
            break
        positional.append(tok)
    return positional[-1] if positional else None


def assert_read_only(args: list[str]) -> None:
    """Wirft MutatingCommandError, wenn ``args`` kein rein lesender Command ist."""
    verb = _action_verb(args)
    if verb not in READ_VERBS:
        allowed = ", ".join(sorted(READ_VERBS))
        raise MutatingCommandError(
            f"Blockiert: 'stackit {' '.join(args)}' ist kein lesender Command "
            f"(erlaubte Verben: {allowed}). Dieses Projekt darf STACKIT nur lesen."
        )


def run_json(args: list[str]) -> list | dict:
    """Führt einen **lesenden** stackit-Command aus und parst dessen JSON-Ausgabe.

    Der Command wird zuerst gegen die Read-Only-Allowlist geprüft; ein
    mutierender Command wird abgelehnt, bevor stackit gestartet wird.
    ``--output-format json`` wird automatisch angehängt.
    """
    assert_read_only(args)
    cmd = ["stackit", *args, "--output-format", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        log.error("stackit %s fehlgeschlagen: %s", " ".join(args), res.stderr.strip())
        sys.exit(EXIT_FAIL)
    return json.loads(res.stdout or "[]")
