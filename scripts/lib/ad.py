"""Gemeinsame LDAP-Helfer für Active-Directory-Abfragen (read-only).

Verbindet sich per LDAP(S) direkt gegen einen Domain Controller und meldet sich
mit User + Passwort (Simple Bind) an — kein Windows-Jump-Host und kein
RSAT-PowerShell nötig. Nur lesende Suchen; dieses Modul mutiert nie AD.

ENV (siehe .env.example / docs/REQUIREMENTS.md):
  AD_USER        Bind-DN oder UPN (z.B. 'CORP\\svc-read' oder 'svc-read@corp.example')
  AD_PASSWORD    Passwort dazu
  AD_PORT        Port (default 636 für LDAPS, 389 für LDAP)
  AD_USE_SSL     "true" (default) = LDAPS | "false" = LDAP im Klartext (nur bewusst)
  AD_TLS_VERIFY  "true" (default) = Server-Zertifikat prüfen | "false" = ignorieren
  AD_CA_BUNDLE   optional: Pfad zu einer CA-Bundle-Datei (private CA)
  AD_BASE_DN     optional: Such-Basis; ohne Angabe defaultNamingContext des DC
"""

from __future__ import annotations

import os
import ssl
import sys
from pathlib import Path

import ldap3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import EXIT_USAGE, require_env  # noqa: E402

# OID LDAP_MATCHING_RULE_IN_CHAIN — löst rekursive Gruppen-Mitgliedschaft auf.
RECURSIVE_MEMBER_RULE = "1.2.840.113556.1.4.1941"


def _tls() -> ldap3.Tls:
    """TLS-Konfiguration aus den AD_*-ENV-Togglen."""
    verify = os.environ.get("AD_TLS_VERIFY", "true").lower() != "false"
    ca_bundle = os.environ.get("AD_CA_BUNDLE") or None
    if not verify:
        sys.stderr.write(
            "[WARN] AD_TLS_VERIFY=false - LDAPS-Verbindung läuft ohne Zertifikatsprüfung (MITM möglich).\n"
        )
    return ldap3.Tls(
        validate=ssl.CERT_REQUIRED if verify else ssl.CERT_NONE,
        ca_certs_file=ca_bundle,
    )


def connect(host: str) -> ldap3.Connection:
    """Öffnet eine gebundene LDAP(S)-Verbindung zum DC (Simple Bind, read-only)."""
    env = require_env("AD_USER", "AD_PASSWORD")
    use_ssl = os.environ.get("AD_USE_SSL", "true").lower() != "false"
    port = int(os.environ.get("AD_PORT", "636" if use_ssl else "389"))
    server = ldap3.Server(
        host,
        port=port,
        use_ssl=use_ssl,
        get_info=ldap3.DSA,
        tls=_tls() if use_ssl else None,
    )
    try:
        conn = ldap3.Connection(
            server,
            user=env["AD_USER"],
            password=env["AD_PASSWORD"],
            authentication=ldap3.SIMPLE,
            auto_bind=True,
            read_only=True,
        )
    except ldap3.core.exceptions.LDAPException as exc:
        sys.stderr.write(f"LDAP-Bind an {host}:{port} fehlgeschlagen: {exc}\n")
        sys.exit(EXIT_USAGE)
    return conn


def base_dn(conn: ldap3.Connection) -> str:
    """Such-Basis: AD_BASE_DN, sonst defaultNamingContext des DC aus der RootDSE."""
    override = os.environ.get("AD_BASE_DN")
    if override:
        return override
    info = conn.server.info
    contexts = getattr(info, "other", {}).get("defaultNamingContext") if info else None
    if not contexts:
        sys.stderr.write(
            "defaultNamingContext nicht ermittelbar - setze AD_BASE_DN explizit (z.B. DC=corp,DC=example).\n"
        )
        sys.exit(EXIT_USAGE)
    return contexts[0]


def search(conn: ldap3.Connection, base: str, search_filter: str, attributes: list[str]) -> list[dict]:
    """Gepagede Subtree-Suche. Liefert [{'dn': str, 'attrs': {name: [werte]}}]."""
    results = conn.extend.standard.paged_search(
        search_base=base,
        search_filter=search_filter,
        search_scope=ldap3.SUBTREE,
        attributes=attributes,
        paged_size=500,
        generator=False,
    )
    out: list[dict] = []
    for r in results:
        if r.get("type") != "searchResEntry":
            continue
        out.append({"dn": r["dn"], "attrs": r.get("attributes", {})})
    return out


def escape_filter(value: str) -> str:
    """Escaped einen Wert für ein LDAP-Filter-Literal (RFC 4515)."""
    return (
        value.replace("\\", "\\5c")
        .replace("*", "\\2a")
        .replace("(", "\\28")
        .replace(")", "\\29")
        .replace("\x00", "\\00")
    )


def escape_filter_wildcard(value: str) -> str:
    """Wie escape_filter, aber '*' bleibt als Wildcard erhalten (für -like-Filter)."""
    return (
        value.replace("\\", "\\5c")
        .replace("(", "\\28")
        .replace(")", "\\29")
        .replace("\x00", "\\00")
    )
