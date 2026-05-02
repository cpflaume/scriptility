# scriptility

Zentrales Repository für DevOps-Skripte. Eine Schnittstelle (`task`), viele Skripte —
einheitlich aufrufbar, getestet, reviewbar.

> **Warum?** Statt 50 Bash-Snippets in Wikis und Slack-Threads: ein Repo, eine
> Konvention, ein Befehl. Jeder im Team kann fragen wie *"Welche Cronjobs laufen
> auf Host X?"* oder *"Wo ist überall ein Weekly-Schedule konfiguriert?"* mit
> einem einzigen Kommando beantworten.

---

## TL;DR

```bash
git clone <repo> && cd scriptility
task setup           # einmalig: venv, pre-commit, .env
task --list-all      # alle Skripte anzeigen
task doctor          # prüft installierte Tools

# Beispiele:
task network:check-port -- 10.0.0.1 443
task gitlab:list-schedules -- 12345
task linux:list-users -- prod-web-01
ENV=staging task terraform:plan
```

## Wichtige Doku

| Datei | Inhalt |
|---|---|
| [docs/USAGE.md](docs/USAGE.md) | So benutzt du das Repo im Alltag |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | So fügst du ein neues Skript hinzu |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Welche Tools du installiert haben musst |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Warum es so aufgebaut ist wie es ist |

## Aufbau (kurz)

```
taskfiles/      # Eine YAML pro Domäne (network, gitlab, ...)
scripts/        # Bash + Python, organisiert nach Domäne
  lib/          # Geteilte Helfer (Logging, Env-Checks)
tests/          # bats für bash, pytest für python
infrastructure/ # Terraform-Umgebungen + Ansible-Playbooks
templates/      # Vorlagen für `task dev:new`
```

## Mitmachen

Neues Skript? `task dev:new -- bash <namespace> <name>` und dann CONTRIBUTING.md
befolgen. CI sorgt dafür, dass nichts ungetestet hereinkommt.

## AI-Assistenten (Claude Code, Continue, Roo Code, …)

Der gesamte Projekt-Kontext für AI-Tools steht in [`AGENTS.md`](AGENTS.md).
Tool-spezifische Pfade sind Symlinks darauf:

| Tool | Pfad |
|---|---|
| Claude Code | `CLAUDE.md` → `AGENTS.md` |
| Continue (VSCode) | `.continue/rules/project.md` → `AGENTS.md` |
| Roo Code (VSCode) | `.roo/rules/project.md` → `AGENTS.md` |

Editiere **nur `AGENTS.md`**; die Symlinks aktualisieren sich automatisch.
Auf Windows muss `git config --global core.symlinks true` gesetzt sein
(einmalig pro Entwickler).
