# Usage Guide

## Installation (einmalig pro Entwickler)

1. **Voraussetzungen** prüfen — siehe [REQUIREMENTS.md](REQUIREMENTS.md).
2. Repo klonen.
3. ```bash
   task setup
   ```
   Das legt eine Python-venv mit `uv` an, installiert pre-commit-Hooks und kopiert
   `.env.example` nach `.env`.
4. `.env` ausfüllen (Tokens, Credentials).
5. ```bash
   task doctor
   ```
   prüft, ob alle CLI-Tools installiert sind.

## Skripte ausführen

Alle Skripte werden über Tasks aufgerufen. Argumente werden mit `--` weitergereicht:

```bash
task <namespace>:<task> -- <arg1> <arg2> ...
```

**Beispiele:**

```bash
# TCP-Port-Check
task network:check-port -- 10.0.0.1 443 5

# Python-Variante mit JSON-Output
task network:check-port-py -- --host 10.0.0.1 --port 443 --json

# Alle Pipeline-Schedules in GitLab-Group 12345
task gitlab:list-schedules -- 12345

# STACKIT-Firewall-Regeln
task stackit:list-firewall-rules -- $STACKIT_DEFAULT_PROJECT_ID

# Lokale Linux-Benutzer abfragen (via SSH)
task linux:list-users -- prod-web-01

# Terraform-Umgebung neu anlegen
task terraform:bootstrap-env -- staging
ENV=staging task terraform:init
ENV=staging task terraform:plan
ENV=staging task terraform:apply

# Übersicht aller Tasks
task --list-all
```

## Konventionen für jeden Aufruf

- **Hilfe**: jedes Skript versteht `--help` (Python) bzw. `-h`/`--help` (Bash).
- **Exit-Codes**:
  - `0` = Erfolg
  - `1` = fachlicher Fehler (z. B. Port nicht offen)
  - `2` = Aufruf-Fehler (fehlende Argumente, falsche ENV)
- **JSON-Output**: Python-Skripte unterstützen `--json` für maschinenlesbare Ausgabe.
- **Logging**: Logs gehen nach **stderr**, Resultate nach **stdout** — du kannst Output
  bedenkenlos pipen: `task network:check-port-py -- --host x --port y --json | jq`.

## Secrets

Tokens und Passwörter gehören in `.env` und werden niemals committed. Im CI
werden sie über CI-Variablen bzw. Vault bereitgestellt. Für die lokale
Entwicklung kann `.env` auch aus einem Passwort-Manager generiert werden.
