"""Gemeinsame WinRM-Helfer für Windows-Skripte."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import winrm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import EXIT_USAGE, require_env  # noqa: E402


def session(host: str) -> winrm.Session:
    """WinRM-Session mit TLS-Verifikation by default.

    ENV-Toggles:
      WIN_TLS_VERIFY     "true" (default) | "false"  - TLS-Cert prüfen
      WIN_TRANSPORT      "ntlm" (default) | "kerberos" | "credssp" | "basic"
      WIN_PORT           "5986" (default) - Port; HTTP nur mit basic/ntlm bewusst
    """
    env = require_env("WIN_USER", "WIN_PASSWORD")
    verify = os.environ.get("WIN_TLS_VERIFY", "true").lower() != "false"
    transport = os.environ.get("WIN_TRANSPORT", "ntlm")
    port = os.environ.get("WIN_PORT", "5986")
    if not verify:
        sys.stderr.write(
            "[WARN] WIN_TLS_VERIFY=false - WinRM-Verbindung läuft ohne Zertifikatsprüfung (MITM möglich).\n"
        )
    return winrm.Session(
        f"https://{host}:{port}/wsman",
        auth=(env["WIN_USER"], env["WIN_PASSWORD"]),
        transport=transport,
        server_cert_validation="validate" if verify else "ignore",
    )


def run_ps(host: str, script: str) -> str:
    res = session(host).run_ps(script)
    if res.status_code != 0:
        sys.stderr.write(res.std_err.decode("utf-8", errors="replace"))
        sys.exit(EXIT_USAGE)
    return res.std_out.decode("utf-8", errors="replace")
