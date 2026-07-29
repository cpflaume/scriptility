"""Zentrale, **nur lesende** Anbindung an die STACKIT-CLI.

Alle Python-Skripte, die stackit aufrufen, gehen über diesen Helfer. Er setzt
eine Read-Only-Garantie durch (Default-Deny): das **erste bekannte Verb** im
Command-Pfad muss ein lesendes Verb (``list``/``describe``) sein — sonst wird
der Aufruf abgelehnt, *bevor* stackit gestartet wird. So kann kein Skript
versehentlich Infrastruktur verändern.

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

# Lesende Verben. Gegen die STACKIT-CLI-Referenz geprüft: für Lese-Operationen
# kennt die CLI genau `list` und `describe`. (Einzelfälle wie `console`/`log`
# werden bewusst mit-blockiert — sie sind für dieses Projekt nicht nötig, und
# Über-Blocken ist die sichere Richtung.)
READ_VERBS = frozenset({"list", "describe"})

# Bekannte mutierende Verben. Diese Liste ist absichtlich NICHT die
# Sicherheitsgarantie — die liefert der Default-Deny in assert_read_only (ohne
# Lese-Verb wird ohnehin blockiert). Sie ist ein Tripwire: sie sorgt dafür,
# dass ein mutierendes Verb auch dann als *Aktion* erkannt wird, wenn danach
# ein positionales Argument folgt, das zufällig wie ein Lese-Verb aussieht
# (z. B. ein Server namens "list" bei `server create list`). Nicht erschöpfend.
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
        "restore",
        "reset",
        "rotate",
        "regenerate",
        "renew",
        "generate",
        "run",
        "execute",
        "trigger",
        "apply",
        "revoke",
        "import",
        "export",
        "upload",
        "activate",
        "deactivate",
        "scale",
        "pause",
        "resume",
        "promote",
        "failover",
        "clone",
        "cancel",
        "confirm",
        "move",
        "migrate",
    }
)

_KNOWN_VERBS = READ_VERBS | MUTATING_VERBS

# Sentinel: run_stackit_query soll bei Fehler abbrechen, statt einen Default
# zurückzugeben.
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
    """Erlaubt nur lesende stackit-Commands; wirft sonst MutatingCommandError.

    Das **erste bekannte Verb** im Command-Pfad bestimmt die Aktion. Ist es kein
    Lese-Verb — oder kommt gar kein bekanntes Verb vor — wird abgelehnt. So
    entscheidet die Aktion, nicht ein nachgestelltes positionales Argument, das
    wie ``list`` aussieht.
    """
    tokens = _command_tokens(args)
    verb = next((t for t in tokens if t in _KNOWN_VERBS), None)
    if verb is None:
        allowed = ", ".join(sorted(READ_VERBS))
        raise MutatingCommandError(
            f"Blockiert: 'stackit {' '.join(args)}' enthält kein lesendes Verb "
            f"({allowed}). Dieses Projekt darf STACKIT nur lesen."
        )
    if verb not in READ_VERBS:
        raise MutatingCommandError(
            f"Blockiert: 'stackit {' '.join(args)}' — mutierendes Verb '{verb}'. Dieses Projekt darf STACKIT nur lesen."
        )


def run_stackit_query(args: list[str], *, default: object = _RAISE) -> list | dict:
    """Führt eine **lesende** Abfrage gegen die STACKIT-API (via CLI) aus.

    Der Command wird zuerst gegen die Read-Only-Garantie geprüft; ein mutierender
    Command wird abgelehnt, bevor stackit gestartet wird. ``--output-format json``
    wird automatisch angehängt und die Ausgabe geparst.

    Schlägt die Abfrage fehl, wird abgebrochen (Exit 1) — außer ``default`` ist
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
            image = run_stackit_query(["image", "describe", image_id, "--project-id", project_id], default={})
            self._image_cache[image_id] = image if isinstance(image, dict) else {}
        return self._image_cache[image_id]

    def _machine_type(self, name: str | None, project_id: str) -> dict:
        if project_id not in self._machine_type_projects:
            types = run_stackit_query(["server", "machine-type", "list", "--project-id", project_id], default=[])
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
