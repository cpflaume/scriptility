# AI Context — scriptility

Single source of truth für AI-Assistenten (Claude Code, Continue, Roo Code, Cursor)
**und** menschliche Contributors. `CLAUDE.md`, `.continue/rules/project.md` und
`.roo/rules/project.md` sind Symlinks darauf.

---

## 1. Repo-Zweck

Zentrale DevOps-Skripte, einheitlich über **Taskfile** ausgeführt. Domänen:
GitLab, STACKIT, Linux, Windows, plus Terraform/Ansible-Wrapper. Der User sieht
nur Task-Befehle (`task <name> -- <args>`) — jedes Skript ist hinter einem Task
gekapselt. Flacher Aufbau, keine Namespaces — ein Team, ein Pool von Skripten.

## 2. Layout (verbindlich)

```
scripts/<name>.{sh,py}            # alle Skripte direkt hier — keine Unterordner
scripts/lib/                      # einziger erlaubter Unterordner: geteilte Helfer
  common.sh / common.py           # Logging, Exit-Codes, Env-Checks
  winrm.py                        # WinRM-Helper für Windows-Skripte
  doctor.sh                       # Tool-Verifikation
  new_script.sh                   # Generator (von `task new` aufgerufen)
  sync_tasks.py                   # rebaut den AUTO-GENERATED-Block in Taskfile.yml
tests/<name>.{bats,py}            # ein Test pro Skript, flach
tests/lib/                        # Tests für scripts/lib/
templates/                        # Vorlagen für `task new`
taskfiles/{setup,dev,terraform,ansible}.yml  # Meta-Tasks
Taskfile.yml                      # Root: enthält pro Skript einen Task im AUTO-GENERATED-Block
infrastructure/{terraform,ansible}/
```

- **Niemals** Skripte in Unterordnern unter `scripts/` (Ausnahme: `scripts/lib/`).
- **Niemals** den Block zwischen `>>> AUTO-GENERATED ... >>>` und
  `<<< END AUTO-GENERATED <<<` von Hand bearbeiten — `task new` schreibt rein,
  `task dev:sync-tasks` rebaut komplett.
- Bei Namens-Konflikten plattformspezifisch präfixen
  (`list_linux_users.sh` vs. `list_windows_users.py`).

## 3. Skript-Vertrag

Pflicht für jedes Skript:

| Anforderung | Bash | Python |
|---|---|---|
| Strikte Modi | `set -euo pipefail` | `from __future__ import annotations` |
| Hilfe | `-h`/`--help` → Exit 2 | `argparse` |
| Exit-Codes | `0` ok, `1` fachlicher Fehler, `2` Aufruf-Fehler | dito via `EXIT_OK/EXIT_FAIL/EXIT_USAGE` aus `scripts.lib.common` |
| Logging | `log::info/warn/error` aus `scripts/lib/common.sh` | `get_logger()` aus `scripts.lib.common` |
| ENV-Checks | `require_env VAR` aus `common.sh` | `require_env("VAR")` aus `common.py` |
| Tool-Checks | `require_cmd jq dig` aus `common.sh` | — (Bibliothek nutzen) |

I/O-Konventionen:
- Resultat nach **stdout**, Logs nach **stderr** — Output ist pipebar.
- Python-Skripte bieten `--json` für maschinenlesbare Ausgabe.
- Mutierende Aktionen brauchen `--apply` (Skript) oder `prompt:` (Taskfile).

**Faustregel bash vs python**: zweites `jq` oder echte JSON-Logik im bash-Skript →
Python.

## 4. Task-Vertrag

Pro Skript wird vom Generator ein Eintrag erzeugt:

```yaml
my-task:
  desc: 'TODO: Beschreibung. Usage: task my-task -- <args>'
  cmds: [bash scripts/my_task.sh {{.CLI_ARGS}}]
```

- Skript-Dateinamen verwenden Underscore (`my_task.sh`), Task-Namen Bindestrich
  (`my-task`). Generator macht das automatisch.
- ENV-/Tool-Checks gehören **ins Skript** (`require_env`, `require_cmd`), nicht in
  `preconditions:` — Skripte sollen auch direkt ausführbar bleiben.
- Mehrzeilige `summary:`, `prompt:`, `sources:`/`generates:` etc. dürfen nach
  Generierung im Block ergänzt werden — `dev:sync-tasks` behält bestehende
  `desc:`-Werte, ersetzt aber `cmds:`. Andere Felder (summary etc.) gehen
  bei einem Sync verloren; bei Bedarf manuell wiederherstellen.

User-Argumente **immer** über `{{.CLI_ARGS}}` mit `--`. Niemals ENV für User-Args.

## 5. Tests sind Pflicht

- **bash** → `tests/<name>.bats` mit Usage-Fall (Exit 2) und Happy-Path.
- **python** → `tests/test_<name>.py`, ruft `main()`. Externe Systeme
  (GitLab, STACKIT, WinRM) **mocken** — keine Echt-Aufrufe.

```bash
task dev:test    # bats + pytest
task dev:lint    # shellcheck, ruff, terraform fmt, ansible-lint
```

## 6. Neues Skript hinzufügen

1. `task new -- <bash|py> <name>` — generiert Skript + Test, registriert Task.
2. Skript implementieren (Vertrag §3), Test schreiben.
3. Neue ENVs in `.env.example` + `docs/REQUIREMENTS.md`. `task dev:lint && task dev:test` grün.

Das war's — kein manueller Taskfile-Edit mehr nötig.

## 7. Anti-Patterns (für AI besonders relevant)

- ❌ Skripte direkt in `scripts/` ablegen ohne `task new` — Task-Eintrag fehlt
  dann.
- ❌ Den AUTO-GENERATED-Block in `Taskfile.yml` von Hand editieren — Generator
  bzw. `dev:sync-tasks` benutzen.
- ❌ Skripte ohne Test — CI blockiert.
- ❌ Secrets/Tokens hardcoden — immer aus `.env` via `dotenv:`.
- ❌ Eigene Logging-Funktionen — `scripts/lib/common.{sh,py}` nutzen.
- ❌ Defaults für gefährliche ENVs (`ENV: example` bei `terraform:destroy`) —
  `requires:` erzwingen.
- ❌ `deps:` wenn Output-Reihenfolge wichtig ist — sequentiell via `cmds: [- task: ...]`.
- ❌ Pattern `A && B || C` — kein if-else, nutze `if`-Block oder zwei `||`-Statements.

## 8. Einstiegspunkt-Dateien

| Datei | Zweck |
|---|---|
| `Taskfile.yml` | Root: enthält pro Skript einen Task; `setup`/`dev`/`terraform`/`ansible` als Includes |
| `taskfiles/dev.yml` | Lint, Test, `dev:new`, `dev:sync-tasks`, Format |
| `scripts/lib/common.{sh,py}` | Logging, Exit-Codes, Env-Checks |
| `scripts/lib/new_script.sh` | Generator (registriert Tasks im Root-Taskfile) |
| `scripts/check_port.{sh,py}` | **Referenz-Implementierung** |
| `tests/test_check_port.py` | Mocking-Beispiel mit lokalem Listener |

## 9. Stack

Taskfile + uv + ruff + shellcheck + bats/pytest + pre-commit/gitleaks.
HTTP via httpx, Windows via pywinrm, STACKIT via stackit-cli.
Stack-Änderungen vorher diskutieren.
