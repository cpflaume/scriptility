# AI Context — scriptility

Diese Datei ist die **single source of truth** für AI-Assistenten (Claude Code,
Continue, Roo Code, Cursor, …). Sie beschreibt, was das Repo ist, welche
Konventionen gelten und wie ein neues Skript korrekt hinzugefügt wird.

> **Wartung**: nur diese Datei (`AGENTS.md`) editieren. `CLAUDE.md`,
> `.continue/rules/project.md` und `.roo/rules/project.md` sind Symlinks darauf.

---

## 1. Was ist das Repo?

`scriptility` ist eine zentrale Sammlung von DevOps-Skripten, die ein Team
einheitlich über **Taskfile** (`task <namespace>:<task>`) ausführt. Zielgruppen
sind GitLab-, STACKIT-, Linux-, Windows-Operationen plus
Terraform/Ansible-Wrapper.

Der User sieht nur Task-Befehle — niemals direkte Skriptaufrufe. Jedes Skript
ist hinter einem Task gekapselt.

## 2. Layout (verbindlich)

```
taskfiles/<namespace>.yml        # eine Datei pro Domäne, included im Root-Taskfile
scripts/<namespace>/<name>.{sh,py}
scripts/lib/                     # geteilte Helfer (common.sh, common.py, doctor.sh)
tests/<namespace>/<name>.{bats,py}
templates/                       # Vorlagen für `task dev:new`
infrastructure/terraform/envs/<env>/
infrastructure/ansible/{playbooks,inventories}/
docs/                            # USAGE, CONTRIBUTING, REQUIREMENTS, ARCHITECTURE
```

**Niemals** Skripte ausserhalb von `scripts/<namespace>/` ablegen. **Niemals**
Tasks im Root-`Taskfile.yml` definieren ausser `default` und `doctor` — alles
andere gehört in `taskfiles/<namespace>.yml`.

## 3. Skript-Vertrag

Jedes neue Skript **muss** dem folgen — egal ob bash oder python:

| Anforderung | Bash | Python |
|---|---|---|
| Strikte Modi | `set -euo pipefail` | `from __future__ import annotations` |
| Hilfe | `-h`/`--help` zeigt Usage und exitet mit 2 | `argparse` |
| Exit-Codes | `0` ok, `1` fachlicher Fehler, `2` Aufruf-Fehler | dito, via `EXIT_OK/EXIT_FAIL/EXIT_USAGE` aus `scripts.lib.common` |
| Logging | `log::info/warn/error` aus `scripts/lib/common.sh` (geht nach **stderr**) | `get_logger()` aus `scripts.lib.common` (stderr) |
| ENV-Checks | `require_env VAR` aus `common.sh` | `require_env("VAR")` aus `common.py` |
| Tool-Checks | `require_cmd jq dig` aus `common.sh` | — (lieber Bibliothek nutzen) |
| Output | Resultat nach **stdout**, Logs nach **stderr** | dito; `--json` für maschinenlesbar |

**Faustregel bash vs python**: sobald in einem bash-Skript ein zweites `jq`
oder echte JSON-Logik auftaucht → Python nehmen.

## 4. Task-Vertrag (`taskfiles/<namespace>.yml`)

Pflichtfelder pro Task:

```yaml
my-task:
  desc: 'Eine Zeile. Usage: task ns:my-task -- <args>'
  cmds:
    - bash scripts/<ns>/<name>.sh {{.CLI_ARGS}}
```

Empfohlen, wenn anwendbar:

- **`summary:`** für mehrzeilige Hilfe (sichtbar in `task --list-all`).
- **`preconditions:`** für ENV-/Tool-Checks vor dem Lauf — z. B.
  ```yaml
  preconditions:
    - sh: '[ -n "$GITLAB_TOKEN" ]'
      msg: "GITLAB_TOKEN nicht gesetzt"
    - sh: command -v stackit
      msg: "stackit-cli fehlt"
  ```
- **`requires:`** für Pflicht-Variablen (statt `default`-Filter):
  ```yaml
  requires:
    vars: [ENV]
  ```
- **`prompt:`** für destruktive Aktionen:
  ```yaml
  prompt: "ENV={{.ENV}} - destroy wirklich ausführen?"
  ```
- **`sources:` / `generates:`** für inkrementelle Ausführung (Caching), z. B. bei Lintern.
- **`aliases:`** für Kurzformen.

Argument-Übergabe: **immer** `{{.CLI_ARGS}}` mit `--` durch den User. Niemals
ENV-Variablen für User-Args bauen.

## 5. Tests sind Pflicht

Kein Skript ohne mindestens einen Test:

- **bash** → `tests/<namespace>/<name>.bats` mit Usage-Fall (Exit 2) und Happy-Path.
- **python** → `tests/<namespace>/test_<name>.py` mit Aufrufen über `main()`.
  Externe Systeme (GitLab, STACKIT, WinRM) **mocken**, nicht echt aufrufen.

Ausführen:
```bash
task dev:test          # bats + pytest
task dev:lint          # shellcheck, ruff, terraform fmt, ansible-lint
```

## 6. So fügt man ein neues Skript hinzu (Schritt-für-Schritt)

1. Generator: `task dev:new -- <bash|py> <namespace> <skript-name>`
   → legt Skript + Test aus `templates/` an.
2. Skript implementieren — Vertrag aus Abschnitt 3 einhalten.
3. Test schreiben (mindestens Usage + ein Happy-Path).
4. **Manuell** Task-Eintrag in `taskfiles/<namespace>.yml` ergänzen
   (Vorlage gibt der Generator aus).
5. Falls neue ENV-Variable nötig: in `.env.example` ergänzen + in `docs/REQUIREMENTS.md` dokumentieren.
6. `task dev:lint && task dev:test` lokal grün bekommen.
7. PR — CI muss grün sein, CODEOWNER muss reviewen.

## 7. Was AI-Assistenten **nicht** tun sollen

- ❌ Skripte ohne Task-Eintrag erzeugen — sie sind sonst unsichtbar.
- ❌ Skripte ohne Test mergen (CI wird das ohnehin blockieren).
- ❌ Secrets/Tokens hardcoden — immer aus `.env` über Taskfile-`dotenv:` laden.
- ❌ Logik in den Root-`Taskfile.yml` schreiben — gehört in `taskfiles/<ns>.yml`.
- ❌ Eigene Logging-Funktionen einführen — `scripts/lib/common.{sh,py}` nutzen.
- ❌ Mutierende Aktionen ohne `prompt:` (Taskfile) oder `--apply`-Flag (Skript).
- ❌ `git rev-parse` o. ä. in Root-`vars:` — `{{.TASKFILE_DIR}}` ist die
  Built-in für den Repo-Root.
- ❌ Sich auf Defaults für gefährliche ENV verlassen
  (z. B. `ENV: example` als Default für `terraform:destroy`) — `requires:` nutzen.
- ❌ Tasks parallel via `deps:` chainen, wenn die Output-Reihenfolge wichtig ist
  (dann `cmds: [- task: ...]` sequentiell).

## 8. Wichtige Dateien als Einstiegspunkt

| Datei | Zweck |
|---|---|
| `Taskfile.yml` | Root, nur Includes + `default`/`doctor` |
| `taskfiles/dev.yml` | Lint-, Test-, Generator-Tasks |
| `scripts/lib/common.sh` / `common.py` | Logging, Exit-Codes, Env-Checks |
| `scripts/network/check_port.{sh,py}` | **Referenz-Implementierung** — bei neuen Skripten als Vorbild nutzen |
| `tests/network/test_check_port.py` | Beispiel für Mocking via lokalem Listener |
| `templates/` | Vorlagen, die `task dev:new` befüllt |
| `docs/CONTRIBUTING.md` | menschliche Langfassung dieses Files |
| `docs/ARCHITECTURE.md` | Designentscheidungen + Begründung |

## 9. Tools-Stack (nicht ändern ohne Diskussion)

- **Taskfile** als Entry Point.
- **uv** für Python-Deps (`pyproject.toml`, `uv.lock`).
- **ruff** für Format + Lint, **shellcheck** für bash, **bats** + **pytest** für Tests.
- **pre-commit** mit gitleaks für Secret-Scan.
- **httpx** für HTTP, **pywinrm** für Windows, **stackit-cli** für STACKIT.
