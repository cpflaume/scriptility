# Contributing — neues Skript hinzufügen

Dieses Repo lebt davon, dass Skripte einer einheitlichen Konvention folgen. Bitte
halte dich an diesen Workflow.

## 1. Skript generieren

```bash
# Bash:
task dev:new -- bash <namespace> <skript-name>
# Python:
task dev:new -- py   <namespace> <skript-name>
```

Der Generator legt an:
- `scripts/<namespace>/<skript-name>.{sh,py}` — aus Template
- `tests/<namespace>/<skript-name>.{bats,py}` — aus Template

Anschließend musst du **manuell** einen Task-Eintrag in
`taskfiles/<namespace>.yml` ergänzen (Vorschlag wird vom Generator ausgegeben).

## 2. Skript-Vertrag

Jedes Skript **muss**:

| Anforderung | Bash | Python |
|---|---|---|
| Shebang | `#!/usr/bin/env bash` | — |
| Strikte Modi | `set -euo pipefail` | `from __future__ import annotations` |
| Doku-Header | Kommentarblock mit Usage + Exit-Codes | Modul-Docstring |
| `--help` / `-h` | Eigene `usage()`-Funktion | `argparse` |
| Exit-Codes | `0/1/2` (siehe USAGE.md) | `EXIT_OK/EXIT_FAIL/EXIT_USAGE` aus `lib.common` |
| Logging | `log::info/warn/error` aus `lib/common.sh` | `get_logger()` aus `lib/common.py` |
| ENV-Checks | `require_env VAR` aus `lib/common.sh` | `require_env("VAR")` aus `lib/common.py` |
| Tool-Checks | `require_cmd jq dig` aus `lib/common.sh` | — |

Jedes Skript **soll** (wo sinnvoll):
- `--json` als Flag anbieten (für Pipeline-Verarbeitung).
- **Idempotent** sein, wenn es etwas verändert.
- **Read-only by default** sein und mutierende Aktionen hinter `--apply` verstecken.

## 3. Tests

Jedes Skript **braucht mindestens einen Test**:

- **Bash** → bats unter `tests/<namespace>/<name>.bats`. Mindestens:
  - Usage-Fall (Exit 2 bei fehlenden Args).
  - Ein Happy-Path.
- **Python** → pytest unter `tests/<namespace>/test_<name>.py`. Mindestens:
  - `main()` mit gültigen Args → Exit 0.
  - `main()` mit ungültigen Args → Exit 2 / `SystemExit`.

Externe Systeme (GitLab, STACKIT, WinRM) **werden gemockt** — keine Tests gegen
echte Endpoints. Für Netzwerk-Tests gibt es ein Beispiel mit lokalem Listener
in `tests/network/test_check_port.py`.

Tests laufen lokal mit:
```bash
task dev:test
```

## 4. Task-Eintrag

In `taskfiles/<namespace>.yml`:

```yaml
my-script:
  desc: 'Kurze Beschreibung. Usage: task ns:my-script -- <args>'
  summary: |
    Längere Beschreibung, was das Skript löst und welche Outputs es liefert.
  cmds:
    - bash scripts/<ns>/my_script.sh {{.CLI_ARGS}}
  preconditions:
    - sh: '[ -n "$REQUIRED_TOKEN" ]'
      msg: "REQUIRED_TOKEN nicht gesetzt"
```

**Pflicht:**
- `desc:` — eine Zeile, erscheint in `task --list`.
- **Sprechender Task-Name** in kebab-case.

**Empfohlen:**
- `summary:` für mehrzeilige Hilfe (sichtbar in `task --list-all`).
- `preconditions:` für ENV-/Tool-Checks vor dem Lauf.
- `prompt:` bei destruktiven Aktionen (siehe `terraform:apply`).

## 5. Quality-Gates

Vor dem Commit läuft pre-commit (shellcheck, ruff, terraform fmt, gitleaks).
In CI (`.gitlab-ci.yml` / `.github/workflows/ci.yml`) laufen zusätzlich:

```bash
task dev:lint
task dev:test
```

Ein PR ist mergebar, wenn:
- [ ] CI grün
- [ ] CODEOWNER hat reviewed
- [ ] `desc:` und `summary:` aussagekräftig
- [ ] Mindestens ein Test pro Skript
- [ ] Keine Secrets committed
- [ ] Bei mutierenden Aktionen: `--apply`-Flag oder `prompt:` im Taskfile

## 6. Domain-Ownership

Pro Namespace gibt es eine verantwortliche Person (siehe `CODEOWNERS`).
Reviews außerhalb des eigenen Namespaces sind willkommen, aber nicht Pflicht.
