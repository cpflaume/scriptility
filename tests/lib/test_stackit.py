"""Tests für scripts/lib/stackit.py — den Read-Only-Guard."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.lib.stackit import MutatingCommandError, ServerEnricher, assert_read_only, run_stackit_query


@pytest.mark.parametrize(
    "args",
    [
        ["project", "list"],
        ["server", "list", "--project-id", "p"],
        ["server", "describe", "--server-id", "s"],
        ["security-group", "rule", "list", "--project-id", "p", "--security-group-id", "g"],
        ["image", "list", "--all", "--project-id", "p"],
        ["server", "machine-type", "list", "--project-id", "p"],
        # describe mit positionaler ID: das Verb steht nicht am Ende des Pfads.
        ["image", "describe", "11111111-2222-3333-4444-555555555555", "--project-id", "p"],
    ],
)
def test_read_commands_allowed(args):
    assert_read_only(args)  # darf nicht werfen


@pytest.mark.parametrize(
    "args",
    [
        ["server", "create", "--name", "x"],
        ["server", "delete", "--server-id", "s"],
        ["server", "update", "--server-id", "s"],
        ["security-group", "rule", "create", "--project-id", "p"],
        ["server", "start", "--server-id", "s"],
        ["server", "delete", "s-123", "--project-id", "p"],  # mutierendes Verb vor positionaler ID
        # Das erste Verb entscheidet: ein positionales Argument, das wie ein
        # Lese-Verb aussieht (Server namens "list"), darf create nicht durchlassen.
        ["server", "create", "list"],
        ["dns", "record-set", "delete", "describe"],
        [],  # leerer Command => default-deny
        ["--help"],  # nur Flags, kein Verb
        ["server", "console", "--server-id", "s"],  # kein list/describe => blockiert (sichere Richtung)
    ],
)
def test_mutating_commands_blocked(args):
    with pytest.raises(MutatingCommandError):
        assert_read_only(args)


def test_run_stackit_query_blocks_before_subprocess():
    """Ein mutierender Command darf stackit gar nicht erst starten."""
    with patch("subprocess.run") as run:
        with pytest.raises(MutatingCommandError):
            run_stackit_query(["server", "delete", "--server-id", "s"])
        run.assert_not_called()


def test_run_stackit_query_parses_read_output():
    class _Res:
        returncode = 0
        stderr = ""
        stdout = json.dumps([{"id": "s-1"}])

    with patch("subprocess.run", return_value=_Res()):
        out = run_stackit_query(["server", "list", "--project-id", "p"])
    assert out == [{"id": "s-1"}]


def test_server_enricher_caches_images_across_projects():
    """Image wird nur bei Cache-Miss geladen; IDs gelten projektübergreifend."""
    calls = {"image": 0, "machine_type": 0}

    def fake(cmd, **_kwargs):
        args = cmd[1:-2]

        class _Res:
            returncode = 0
            stderr = ""

        if args[0] == "image":  # image describe <id>
            calls["image"] += 1
            _Res.stdout = json.dumps({"id": args[2], "name": "Ubuntu", "config": {"operatingSystem": "linux"}})
        elif "machine-type" in args:
            calls["machine_type"] += 1
            _Res.stdout = json.dumps([{"name": "g1.2", "vcpus": 2, "ram": 4096, "disk": 20}])
        else:
            _Res.stdout = "[]"
        return _Res()

    server = {"id": "s", "name": "n", "machineType": "g1.2", "imageId": "img-1"}
    enricher = ServerEnricher()
    with patch("subprocess.run", side_effect=fake):
        r1 = enricher.enrich(server, "p-1")
        enricher.enrich({**server, "id": "s2"}, "p-1")  # gleiches Projekt, gleiches Image
        r3 = enricher.enrich({**server, "id": "s3"}, "p-2")  # anderes Projekt, gleiche Image-ID

    assert r1["os"] == "linux"
    assert r1["vcpus"] == 2
    assert r3["disk_gb"] == 20
    assert calls["image"] == 1  # Image nur einmal geladen (Cache greift projektübergreifend)
    assert calls["machine_type"] == 2  # machine-type list genau einmal pro Projekt
