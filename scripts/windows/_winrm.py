"""Gemeinsame WinRM-Helfer für Windows-Skripte."""

from __future__ import annotations

import sys
from pathlib import Path

import winrm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import EXIT_USAGE, require_env  # noqa: E402


def session(host: str) -> winrm.Session:
    env = require_env("WIN_USER", "WIN_PASSWORD")
    return winrm.Session(
        f"https://{host}:5986/wsman",
        auth=(env["WIN_USER"], env["WIN_PASSWORD"]),
        transport="ntlm",
        server_cert_validation="ignore",
    )


def run_ps(host: str, script: str) -> str:
    res = session(host).run_ps(script)
    if res.status_code != 0:
        sys.stderr.write(res.std_err.decode("utf-8", errors="replace"))
        sys.exit(EXIT_USAGE)
    return res.std_out.decode("utf-8", errors="replace")
