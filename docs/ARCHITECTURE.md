# Architecture

## Schichten

```
Taskfile (Entry Point)        ← User sieht NUR Task-Befehle
  ↓
scripts/<name>.{sh,py}        ← bash + python, eine Aufgabe pro Datei (flach)
  ↓
scripts/lib                   ← Logging, ENV-Checks, Exit-Codes, WinRM, Generator
  ↓
CLI-Tools (jq, terraform, …)  ← externe Werkzeuge
```

Hinzufügen eines Skripts: `task new -- <bash|py> <name>` legt Skript + Test
an und registriert den Task im AUTO-GENERATED-Block in `Taskfile.yml`. Kein
Namespace-Layout, kein manueller Taskfile-Edit.

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

- Bei Namens-Konflikten plattformspezifisch präfixen (`list_linux_users.sh`
  vs. `list_windows_users.py`).
- Mehrfach genutzte Helper wandern nach `scripts/lib/`.
- Tests sind nicht verhandelbar.
