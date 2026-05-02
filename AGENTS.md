# AI Context — scriptility

Single source of truth für AI-Assistenten (Claude Code, Continue, Roo Code, Cursor)
**und** menschliche Contributors. `CLAUDE.md`, `.continue/rules/project.md` und
`.roo/rules/project.md` sind Symlinks darauf.

---

## 1. Repo-Zweck

Zentrale DevOps-Skripte, einheitlich über **Taskfile** (`task <ns>:<task>`)
ausgeführt. Domänen: GitLab, STACKIT, Linux, Windows, plus Terraform/Ansible-Wrapper.
Der User sieht nur Task-Befehle — jedes Skript ist hinter einem Task gekapselt.

## 2. Layout (verbindlich)

```
taskfiles/<ns>.yml               # eine Datei pro Domäne, included im Root-Taskfile
scripts/<ns>/<name>.{sh,py}
scripts/lib/                     # geteilte Helfer (common.sh, common.py)
tests/<ns>/<name>.{bats,py}
templates/                       # Vorlagen für `task dev:new`
infrastructure/{terraform,ansible}/
```

- **Niemals** Skripte ausserhalb `scripts/<ns>/`.
- **Niemals** Tasks im Root-`Taskfile.yml` ausser `default` und `doctor` —
  Domain-Tasks gehören in `taskfiles/<ns>.yml`.

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

## 4. Task-Vertrag (`taskfiles/<ns>.yml`)

```yaml
my-task:
  desc: 'Eine Zeile. Usage: task ns:my-task -- <args>'
  cmds:
    - bash scripts/<ns>/<name>.sh {{.CLI_ARGS}}
```

Bei Bedarf:
- `summary:` für mehrzeilige Hilfe in `task --list-all`.
- `preconditions:` für ENV-/Tool-Checks (`[ -n "$TOKEN" ]`, `command -v xy`).
- `requires: { vars: [ENV] }` für Pflicht-Variablen — **nicht** `default:`-Filter
  bei gefährlichen ENVs.
- `prompt:` für destruktive Aktionen.
- `sources:`/`generates:` für Caching (z. B. Linter).
- `aliases:` für Kurzformen.

User-Argumente **immer** über `{{.CLI_ARGS}}` mit `--`. Niemals ENV für User-Args.

## 5. Tests sind Pflicht

- **bash** → `tests/<ns>/<name>.bats` mit Usage-Fall (Exit 2) und Happy-Path.
- **python** → `tests/<ns>/test_<name>.py`, ruft `main()`. Externe Systeme
  (GitLab, STACKIT, WinRM) **mocken** — keine Echt-Aufrufe.

```bash
task dev:test    # bats + pytest
task dev:lint    # shellcheck, ruff, terraform fmt, ansible-lint
```

## 6. Neues Skript hinzufügen

1. `task dev:new -- <bash|py> <ns> <name>` — generiert Skript + Test aus Templates.
2. Skript implementieren (Vertrag §3) und Test schreiben.
3. Task-Eintrag in `taskfiles/<ns>.yml` ergänzen — Vorlage gibt der Generator aus.
4. Neue ENVs in `.env.example` + `docs/REQUIREMENTS.md`. `task dev:lint && task dev:test` grün.

## 7. Anti-Patterns (für AI besonders relevant)

- ❌ Skripte ohne Task-Eintrag — sie sind unsichtbar.
- ❌ Skripte ohne Test — CI blockiert.
- ❌ Secrets/Tokens hardcoden — immer aus `.env` via `dotenv:`.
- ❌ Logik in Root-`Taskfile.yml` — gehört in `taskfiles/<ns>.yml`.
- ❌ Eigene Logging-Funktionen — `scripts/lib/common.{sh,py}` nutzen.
- ❌ `git rev-parse` o. ä. in Root-`vars:` — `{{.TASKFILE_DIR}}` ist die Built-in.
- ❌ Defaults für gefährliche ENVs (`ENV: example` bei `terraform:destroy`) —
  `requires:` erzwingen.
- ❌ `deps:` wenn Output-Reihenfolge wichtig ist — sequentiell via `cmds: [- task: ...]`.
- ❌ Pattern `A && B || C` — kein if-else, nutze `if`-Block oder zwei `||`-Statements.

## 8. Einstiegspunkt-Dateien

| Datei | Zweck |
|---|---|
| `Taskfile.yml` | Root, nur Includes + `default`/`doctor` |
| `taskfiles/dev.yml` | Lint-, Test-, Generator-Tasks |
| `scripts/lib/common.{sh,py}` | Logging, Exit-Codes, Env-Checks |
| `scripts/network/check_port.{sh,py}` | **Referenz-Implementierung** |
| `tests/network/test_check_port.py` | Mocking-Beispiel mit lokalem Listener |

## 9. Stack

Taskfile + uv + ruff + shellcheck + bats/pytest + pre-commit/gitleaks.
HTTP via httpx, Windows via pywinrm, STACKIT via stackit-cli.
Stack-Änderungen vorher diskutieren.
