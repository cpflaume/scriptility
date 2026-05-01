"""Listet alle Projekte einer GitLab-Group rekursiv.

Usage:
    python list_projects.py <group_id> [--json]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import EXIT_OK, emit, get_logger, require_env  # noqa: E402

log = get_logger("gitlab.projects")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("group_id", type=int)
    p.add_argument("--json", dest="json_output", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    env = require_env("GITLAB_TOKEN")
    base = os.environ.get("GITLAB_URL", "https://gitlab.com").rstrip("/")
    with httpx.Client(base_url=base, headers={"PRIVATE-TOKEN": env["GITLAB_TOKEN"]}, timeout=30.0) as c:
        projects: list[dict] = []
        page = 1
        while True:
            r = c.get(
                f"/api/v4/groups/{args.group_id}/projects",
                params={"include_subgroups": True, "per_page": 100, "page": page, "archived": False},
            )
            r.raise_for_status()
            chunk = r.json()
            if not chunk:
                break
            projects.extend(chunk)
            page += 1
    rows = [{"id": p["id"], "path": p["path_with_namespace"], "default_branch": p.get("default_branch")} for p in projects]
    emit(rows, json_output=args.json_output, table_fn=lambda rs: [print(f"{r['id']:>8}  {r['path']}") for r in rs])
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
