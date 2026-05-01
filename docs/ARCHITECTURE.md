# Architecture

## Designziele

1. **Niederschwelligkeit**: Jeder im Team — auch ohne Skript-Vorerfahrung — soll
   bestehende Skripte mit einem einzigen Befehl ausführen können.
2. **Konsistenz**: Egal ob bash oder python: gleicher Aufrufpattern, gleiche
   Exit-Codes, gleiches Logging-Format.
3. **Reviewbarkeit**: Tests sind Pflicht. CI verhindert ungeprüften Code.
4. **Auffindbarkeit**: `task --list-all` ist die kanonische Skript-Übersicht.
   Keine Skripte ohne Task-Eintrag.

## Schichten

```
┌─────────────────────────────────────┐
│   Taskfile (UI / Entry Point)       │  ← der User sieht NUR Task-Befehle
├─────────────────────────────────────┤
│   scripts/<namespace>/...           │  ← bash + python, eine Aufgabe pro Datei
├─────────────────────────────────────┤
│   scripts/lib (Common Helpers)      │  ← Logging, ENV-Checks, Exit-Codes
├─────────────────────────────────────┤
│   CLI-Tools (jq, terraform, ...)    │  ← externe Werkzeuge
└─────────────────────────────────────┘
```

## Warum Taskfile?

- **Selbstdokumentierend**: `desc:` + `summary:` ergeben automatisch eine Doku.
- **Plattform-neutral** (Linux/macOS/WSL).
- **Includes & Namespacing** halten ein wachsendes Repo übersichtlich.
- **`preconditions:`** verlagern Tool-/Env-Checks in den Wrapper, statt sie in
  jedem Skript zu duplizieren.
- **`dotenv:`** lädt `.env` automatisch — keine Boilerplate in Skripten.
- **`{{.CLI_ARGS}}`** reicht User-Argumente sauber durch.

## Warum bash *und* python?

- **bash**: ideal für Operationen, die hauptsächlich CLI-Tools verketten
  (`stackit | jq`, `ssh ... 'awk ...'`, kleine Wrapper).
- **python**: sobald JSON-Verarbeitung, Pagination, Mocking in Tests oder mehr
  als triviale Logik nötig wird. Auch für alles über WinRM (pywinrm).

Faustregel: **wenn in deinem bash-Skript ein zweites `jq` auftaucht, nimm Python.**

## Warum `uv` statt pip/poetry?

- Schnell, lockfile-basiert (`uv.lock`), reproduzierbar.
- `uv run pytest` braucht kein `source venv/bin/activate`.

## Sicherheit

- **Secrets** ausschließlich aus `.env` / CI-Variablen, nie hardgecoded.
- `gitleaks` als pre-commit-Hook verhindert versehentliches Committen.
- Skripte sind **read-only by default**. Mutierende Aktionen brauchen entweder
  `--apply` oder einen `prompt:` im Taskfile (Beispiel: `terraform:apply`).
- Linux-Skripte nutzen `sudo -n` (non-interactive) — die SSH-Targets müssen
  passwortloses sudo für die jeweiligen Befehle erlauben.

## Wachstumsstrategie

- Wird ein Namespace zu groß (>15 Tasks), splitten:
  `gitlab.yml` → `gitlab/projects.yml` + `gitlab/pipelines.yml` via `includes`.
- Wenn mehrere Skripte denselben Helper bauen, wandert er nach `scripts/lib/`.
- Tests sind nicht verhandelbar — kein Skript ohne mindestens einen Test.
