"""Listet alle Pipeline-Schedules in einer GitLab-Group rekursiv.

Beantwortet "Wo läuft überall ein Weekly Schedule?".

Usage:
    python list_schedules.py <group_id> [--json]

ENV:
    GITLAB_URL   (default: https://gitlab.com)
    GITLAB_TOKEN (Personal Access Token, scope read_api)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import EXIT_FAIL, EXIT_OK, emit, get_logger, require_env  # noqa: E402

log = get_logger("gitlab.schedules")


def gl_get(client: httpx.Client, path: str, **params) -> list[dict]:
    """Paginiertes GET über die GitLab-API."""
    out: list[dict] = []
    params.setdefault("per_page", 100)
    page = 1
    while True:
        params["page"] = page
        r = client.get(path, params=params)
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            return out
        out.extend(chunk)
        page += 1


def collect_projects(client: httpx.Client, group_id: int) -> list[dict]:
    return gl_get(client, f"/api/v4/groups/{group_id}/projects", include_subgroups=True, archived=False)


def project_schedules(client: httpx.Client, project_id: int) -> list[dict]:
    return gl_get(client, f"/api/v4/projects/{project_id}/pipeline_schedules")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("group_id", type=int)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def render_table(rows: list[dict]) -> None:
    print(f"{'Project':50} {'Schedule':30} {'Cron':20} {'Active'}")
    print("-" * 110)
    for row in rows:
        print(f"{row['project']:50.50} {row['description']:30.30} {row['cron']:20.20} {row['active']}")


def main(argv=None) -> int:
    args = parse_args(argv)
    env = require_env("GITLAB_TOKEN")
    base = os.environ.get("GITLAB_URL", "https://gitlab.com").rstrip("/")

    with httpx.Client(base_url=base, headers={"PRIVATE-TOKEN": env["GITLAB_TOKEN"]}, timeout=30.0) as client:
        projects = collect_projects(client, args.group_id)
        log.info("Gefundene Projekte: %d", len(projects))
        rows: list[dict] = []
        for proj in projects:
            for s in project_schedules(client, proj["id"]):
                rows.append(
                    {
                        "project": proj["path_with_namespace"],
                        "description": s["description"],
                        "cron": s["cron"],
                        "active": s["active"],
                    }
                )

    if not rows:
        log.warning("Keine Schedules gefunden in Group %s", args.group_id)
        return EXIT_OK

    emit(rows, json_output=args.json_output, table_fn=render_table)
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPStatusError as exc:
        log.error("GitLab-API-Fehler: %s", exc)
        sys.exit(EXIT_FAIL)
