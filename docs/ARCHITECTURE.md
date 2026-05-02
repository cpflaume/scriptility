# Architecture

## Schichten

```
Taskfile (Entry Point)        ← User sieht NUR Task-Befehle
  ↓
scripts/<ns>/...              ← bash + python, eine Aufgabe pro Datei
  ↓
scripts/lib                   ← Logging, ENV-Checks, Exit-Codes
  ↓
CLI-Tools (jq, terraform, …)  ← externe Werkzeuge
```

## Bash vs. Python

- **bash** für CLI-Verkettungen (`stackit | jq`, `ssh ... 'awk ...'`).
- **python** sobald JSON, Pagination, Mocking oder mehr als triviale Logik
  nötig wird. Auch alles über WinRM.

Faustregel: zweites `jq` im bash-Skript → Python.

## Sicherheit

- Secrets nur aus `.env`/CI-Variablen, nie hardgecoded. `gitleaks` als
  pre-commit-Hook.
- Skripte sind **read-only by default**. Mutierende Aktionen brauchen
  `--apply` (Skript) oder `prompt:` (Taskfile, z. B. `terraform:apply`).
- Linux-Skripte nutzen `sudo -n` — SSH-Targets müssen passwortloses sudo
  für die jeweiligen Befehle erlauben.

## Wachstum

- Namespace > 15 Tasks → splitten via weitere `includes` (z. B.
  `gitlab/projects.yml` + `gitlab/pipelines.yml`).
- Mehrfach genutzte Helper wandern nach `scripts/lib/`.
- Tests sind nicht verhandelbar.
