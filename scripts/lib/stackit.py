"""Zentrale, **nur lesende** Anbindung an die STACKIT-CLI.

Alle Python-Skripte, die stackit aufrufen, gehen über diesen Helfer. Er setzt
eine Read-Only-Garantie durch: der Command-Pfad (alles bis zum ersten Flag)
muss ein lesendes Verb (``list``/``describe``) enthalten und darf kein
mutierendes Verb (``create``/``update``/``delete``/``start``/...) enthalten.
Jeder Verstoß wird abgelehnt, *bevor* stackit gestartet wird — so kann kein
Skript versehentlich Infrastruktur verändern.

Neben dem Guard bündelt das Modul die (ebenfalls rein lesenden) IaaS-Lookups,
die mehrere Server-Skripte teilen: Image-/OS-Details, Flavor (vCPU/RAM) und
die Anreicherung eines Server-Objekts.

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

# Lesende Verben — mindestens eines muss im Command-Pfad vorkommen.
READ_VERBS = frozenset({"list", "describe"})

# Mutierende Verben — kommt eines davon vor, wird hart abgelehnt (Defense in
# Depth, auch falls versehentlich mit einem Read-Verb kombiniert).
MUTATING_VERBS = frozenset(
    {
        "create",
        "update",
        "partial-update",
        "delete",
        "set",
        "add",
        "remove",
        "attach",
        "detach",
        "enable",
        "disable",
        "start",
        "stop",
        "restart",
        "reboot",
        "deallocate",
        "resize",
        "rescue",
        "unrescue",
        "reset",
        "rotate",
        "generate",
        "import",
        "export",
        "upload",
        "activate",
        "deactivate",
        "cancel",
        "confirm",
        "move",
        "migrate",
    }
)

# Sentinel: run_json soll bei Fehler abbrechen (statt einen Default zu liefern).
_RAISE = object()


class MutatingCommandError(RuntimeError):
    """Ausgelöst, wenn ein nicht-lesender stackit-Command versucht wird."""


def _command_tokens(args: list[str]) -> list[str]:
    """Command-Pfad eines stackit-Aufrufs: alle Tokens bis zum ersten Flag.

    Damit werden Resource-Pfad + Verb (+ ggf. positionale ID) erfasst, aber
    Flag-Werte (``--project-id <wert>``) ausgeklammert — die könnten sonst
    zufällig wie ein Verb aussehen.
    """
    tokens: list[str] = []
    for tok in args:
        if tok.startswith("-"):
            break
        tokens.append(tok)
    return tokens


def assert_read_only(args: list[str]) -> None:
    """Wirft MutatingCommandError, wenn ``args`` kein rein lesender Command ist."""
    tokens = _command_tokens(args)
    if any(t in MUTATING_VERBS for t in tokens):
        raise MutatingCommandError(
            f"Blockiert: 'stackit {' '.join(args)}' enthält ein mutierendes Verb. "
            "Dieses Projekt darf STACKIT nur lesen."
        )
    if not any(t in READ_VERBS for t in tokens):
        allowed = ", ".join(sorted(READ_VERBS))
        raise MutatingCommandError(
            f"Blockiert: 'stackit {' '.join(args)}' ist kein lesender Command "
            f"(erforderlich ist eines der Verben: {allowed})."
        )


def run_json(args: list[str], *, default: object = _RAISE) -> list | dict:
    """Führt einen **lesenden** stackit-Command aus und parst dessen JSON-Ausgabe.

    Der Command wird zuerst gegen die Read-Only-Garantie geprüft; ein mutierender
    Command wird abgelehnt, bevor stackit gestartet wird. ``--output-format json``
    wird automatisch angehängt.

    Schlägt der Command fehl, wird abgebrochen (Exit 1) — außer ``default`` ist
    gesetzt, dann wird dieser Wert zurückgegeben (für best-effort-Anreicherung).
    """
    assert_read_only(args)
    cmd = ["stackit", *args, "--output-format", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        log.error("stackit %s fehlgeschlagen: %s", " ".join(args), res.stderr.strip())
        if default is _RAISE:
            sys.exit(EXIT_FAIL)
        return default  # type: ignore[return-value]
    return json.loads(res.stdout or "[]")


# ---------------------------------------------------------------------------
# IaaS-Lookups & Server-Anreicherung (weiterhin rein lesend).
# ---------------------------------------------------------------------------

# Reihenfolge der angereicherten Server-Felder (ohne Projekt-Kontext).
SERVER_FIELDS = [
    "id",
    "name",
    "status",
    "power_status",
    "machine_type",
    "flavor_description",
    "vcpus",
    "ram_gb",
    "disk_gb",
    "image_id",
    "image_name",
    "os",
    "os_distro",
    "os_version",
    "private_ips",
    "public_ips",
    "availability_zone",
]


class ServerEnricher:
    """Reichert Server rein lesend um OS-/Image-, Flavor- und IP-Details an.

    Caches werden über die gesamte Lebensdauer der Instanz gehalten, damit ein
    Lauf über viele Projekte nicht immer wieder dieselben Daten abfragt:

    - Images per ID — Image-IDs sind projektübergreifend eindeutig, ein Treffer
      aus einem anderen Projekt ist also gültig. Bei Cache-Miss wird das Image
      gezielt via ``image describe <id>`` nachgeladen.
    - Machine-Types per Projekt — ``server machine-type list`` wird je Projekt
      höchstens einmal aufgerufen; die Specs landen (per Name) im Cache.

    Fehler bei der Anreicherung werden toleriert (leere Details statt Abbruch).
    """

    def __init__(self) -> None:
        self._image_cache: dict[str, dict] = {}
        self._machine_types: dict[str, dict] = {}
        self._machine_type_projects: set[str] = set()

    def _image(self, image_id: str, project_id: str) -> dict:
        if not image_id:
            return {}
        if image_id not in self._image_cache:
            image = run_json(["image", "describe", image_id, "--project-id", project_id], default={})
            self._image_cache[image_id] = image if isinstance(image, dict) else {}
        return self._image_cache[image_id]

    def _machine_type(self, name: str | None, project_id: str) -> dict:
        if project_id not in self._machine_type_projects:
            types = run_json(["server", "machine-type", "list", "--project-id", project_id], default=[])
            if isinstance(types, list):
                for t in types:
                    if isinstance(t, dict) and t.get("name"):
                        self._machine_types.setdefault(t["name"], t)
            self._machine_type_projects.add(project_id)
        return self._machine_types.get(name, {}) if name else {}

    def enrich(self, server: dict, project_id: str) -> dict:
        nics = server.get("nics") or []
        private_ips = [n.get("ipv4") for n in nics if n.get("ipv4")]
        public_ips = [n.get("publicIp") for n in nics if n.get("publicIp")]

        machine_type = self._machine_type(server.get("machineType"), project_id)
        ram_mb = machine_type.get("ram")
        ram_gb = round(ram_mb / 1024, 1) if isinstance(ram_mb, int | float) else None

        image = self._image(server.get("imageId"), project_id)
        config = image.get("config") or {}

        return {
            "id": server.get("id", ""),
            "name": server.get("name", ""),
            "status": server.get("status", ""),
            "power_status": server.get("powerStatus", ""),
            "machine_type": server.get("machineType", ""),
            "flavor_description": machine_type.get("description", ""),
            "vcpus": machine_type.get("vcpus"),
            "ram_gb": ram_gb,
            "disk_gb": machine_type.get("disk"),
            "image_id": server.get("imageId", ""),
            "image_name": image.get("name", ""),
            "os": config.get("operatingSystem", ""),
            "os_distro": config.get("operatingSystemDistro", ""),
            "os_version": config.get("operatingSystemVersion", ""),
            "private_ips": ";".join(private_ips),
            "public_ips": ";".join(public_ips),
            "availability_zone": server.get("availabilityZone", ""),
        }
