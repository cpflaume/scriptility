# scriptility

DevOps-Skripte fürs Team — einheitlich aufrufbar via Taskfile, getestet, reviewbar.

## Quickstart

```bash
git clone <repo> && cd scriptility
task setup              # einmalig: venv, pre-commit, .env
task --list-all         # alle verfügbaren Skripte
task network:check-port -- 10.0.0.1 443
```

## Doku

| Datei | Inhalt |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Welche Tools du brauchst |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | PR-Workflow & Checkliste |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layout & Designentscheidungen |
| [AGENTS.md](AGENTS.md) | Kanonischer Skript-/Task-Vertrag (auch von AI-Tools gelesen) |

> AI-Assistenten (Claude Code, Continue, Roo Code) lesen `AGENTS.md` über Symlinks
> (`CLAUDE.md`, `.continue/rules/project.md`, `.roo/rules/project.md`).
> Auf Windows: `git config --global core.symlinks true`.
