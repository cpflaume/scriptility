"""Zentrale, **nur lesende** Anbindung an die STACKIT-CLI.

Alle Python-Skripte, die stackit aufrufen, gehen über diesen Helfer. Er setzt
eine Read-Only-Garantie durch (Default-Deny): ein Aufruf wird nur ausgeführt,
wenn sein Command-Pfad exakt einem der in ``ALLOWED_READ_COMMANDS``
freigeschalteten Lese-Kommandos entspricht. Alles andere — mutierende,
unbekannte oder verschleierte Commands — wird abgelehnt, *bevor* stackit
startet. Bewusst eine Allowlist exakter Kommandos statt einer Verb-Heuristik:
so kann weder ein neues/unbekanntes Verb noch ein positionales Argument, das
wie ``list`` aussieht, die Prüfung austricksen.

Wichtig: Dieser Guard ist eine Client-seitige Schutzschicht, **keine
Autorisierungsgrenze**. Die eigentliche Absicherung ist ein Service Account mit
ausschließlich lesenden Rechten (STACKIT-IAM) — dann kann selbst ein Bypass
dieses Moduls nichts verändern.

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

# Genau diese Read-Command-Pfade darf dieses Projekt ausführen. Der Command-Pfad
# eines Aufrufs (Resource + Verb, ohne Flags und ohne positionale IDs) muss mit
# genau einem dieser Prefixe beginnen — sonst wird blockiert. Neue Lese-Kommandos
# hier bewusst (und reviewbar) freischalten; nur `list`/`describe`-Endpunkte.
ALLOWED_READ_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("project", "list"),
    ("server", "list"),
    ("server", "machine-type", "list"),
    ("image", "describe"),
    ("security-group", "list"),
    ("security-group", "rule", "list"),
)

# Sentinel: run_stackit_query soll bei Fehler abbrechen, statt einen Default
# zurückzugeben.
_RAISE = object()


class MutatingCommandError(RuntimeError):
    """Ausgelöst, wenn ein nicht freigeschalteter (potenziell mutierender) Command versucht wird."""


def _command_tokens(args: list[str]) -> list[str]:
    """Command-Pfad eines stackit-Aufrufs: alle Tokens bis zum ersten Flag.

    Damit werden Resource-Pfad + Verb (+ ggf. positionale ID) erfasst, aber
    Flag-Werte (``--project-id <wert>``) ausgeklammert — die könnten sonst
    zufällig wie ein Command-Bestandteil aussehen.
    """
    tokens: list[str] = []
    for tok in args:
        if tok.startswith("-"):
            break
        tokens.append(tok)
    return tokens


def _starts_with(tokens: list[str], prefix: tuple[str, ...]) -> bool:
    return len(tokens) >= len(prefix) and tuple(tokens[: len(prefix)]) == prefix


def assert_read_only(args: list[str]) -> None:
    """Erlaubt nur freigeschaltete Lese-Kommandos; wirft sonst MutatingCommandError.

    Geprüft wird der Command-Pfad (alles bis zum ersten Flag): er muss mit genau
    einem Eintrag aus ``ALLOWED_READ_COMMANDS`` beginnen. Eine positionale ID
    hinter dem Verb (z. B. ``image describe <id>``) ist erlaubt; ein anderes oder
    zusätzliches Verb davor nicht.
    """
    tokens = _command_tokens(args)
    if not any(_starts_with(tokens, allowed) for allowed in ALLOWED_READ_COMMANDS):
        allowed = "; ".join("stackit " + " ".join(cmd) for cmd in ALLOWED_READ_COMMANDS)
        raise MutatingCommandError(
            f"Blockiert: 'stackit {' '.join(args)}' ist kein freigeschalteter Lese-Command. "
            f"Erlaubt (Read-Only): {allowed}. Neue Lese-Kommandos in ALLOWED_READ_COMMANDS ergänzen."
        )


def run_stackit_query(args: list[str], *, default: object = _RAISE) -> list | dict:
    """Führt eine **lesende** Abfrage gegen die STACKIT-API (via CLI) aus.

    Der Command wird zuerst gegen die Read-Only-Allowlist geprüft; alles, was
    nicht freigeschaltet ist, wird abgelehnt, bevor stackit gestartet wird.
    ``--output-format json`` wird automatisch angehängt und die Ausgabe geparst.

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
