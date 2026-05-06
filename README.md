# scriptility

DevOps-Skripte fürs Team — einheitlich aufrufbar via Taskfile, getestet, reviewbar.

## Quickstart

```bash
git clone <repo> && cd scriptility
task setup              # einmalig: venv, pre-commit, .env
task --list-all         # alle verfügbaren Skripte
task check-port -- 10.0.0.1 443
task new -- bash my-new-script   # neues Skript anlegen (Skript + Test + Task)
```

## Lokales Setup mit VS Code Dev Container

Der schnellste Weg, ohne Tools auf dem Host installieren zu müssen: der
mitgelieferte **Dev Container** unter [`.devcontainer/`](.devcontainer/).
Er enthält alle Pflicht- und empfohlenen Tools aus
[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) (task, uv, python 3.12, bash,
shellcheck, bats, jq, dig, terraform, gitleaks, stackit-cli, ssh) und führt
beim ersten Start automatisch `task setup` und `task doctor` aus.

### Voraussetzungen auf dem Host

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (oder Docker
  Engine + Compose unter Linux)
- [VS Code](https://code.visualstudio.com/) mit der Extension
  [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- `git`

### Erste Schritte

1. Repo klonen und in VS Code öffnen:
   ```bash
   git clone <repo> && cd scriptility
   code .
   ```
2. VS Code zeigt rechts unten **"Reopen in Container"** an — anklicken.
   Alternativ: Command Palette (`F1`) → *Dev Containers: Reopen in Container*.
3. Beim ersten Start baut Docker das Image (~3–5 min). Danach läuft automatisch
   `task setup` (venv, pre-commit, `.env` aus `.env.example`) und `task doctor`.
4. Im integrierten Terminal direkt loslegen:
   ```bash
   task --list-all
   task check-port -- 10.0.0.1 443
   task dev:test
   ```
5. Credentials in der erzeugten `.env` ergänzen — sie ist gitignored. Welche
   ENV-Variablen wofür gebraucht werden, steht in
   [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md#credentials).

### Was ist im Container drin

| Kategorie | Tools |
|---|---|
| Entry Point | `task` |
| Sprachen | `bash` 5, `python` 3.12, `uv` |
| Lint/Test | `shellcheck`, `bats`, `ruff` (via uv), `pytest` (via uv), `ansible-lint` (via uv), `pre-commit` (via uv) |
| Infra | `terraform`, `ansible-core` (via uv), `stackit` |
| Sonst | `git`, `jq`, `dig`, `ssh`, `gitleaks` |

VS Code-Extensions (Python, Ruff, Shellcheck, Bash IDE, Task, Terraform,
Ansible, YAML, TOML, EditorConfig, GitHub Actions) werden beim ersten Start
automatisch installiert.

### Manuelles Setup (ohne Dev Container)

Wenn du lieber direkt auf dem Host arbeitest, installiere die Tools laut
[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) und führe danach `task setup` aus.

## Doku

| Datei | Inhalt |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Welche Tools du brauchst |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | PR-Workflow & Checkliste |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layout & Designentscheidungen |
| [AGENTS.md](AGENTS.md) | Kanonischer Skript-/Task-Vertrag (auch von AI-Tools gelesen) |
| [renovate.json](renovate.json) | Renovate-Konfig (Dependency-Updates Mo+Do, Auto-Merge bei dev-Patches) |

> AI-Assistenten (Claude Code, Continue, Roo Code) lesen `AGENTS.md` über Symlinks
> (`CLAUDE.md`, `.continue/rules/project.md`, `.roo/rules/project.md`).
> Auf Windows: `git config --global core.symlinks true`.
