# Voraussetzungen

## Pflicht

| Tool | Zweck | Install (Debian/Ubuntu) | Install (macOS) |
|---|---|---|---|
| `task` | Entry Point | `sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -b ~/.local/bin` | `brew install go-task` |
| `bash` ≥ 5 | Skripte | meist vorhanden | `brew install bash` |
| `python` ≥ 3.11 | Python-Skripte | `apt install python3` | `brew install python@3.12` |
| `uv` | Python-Deps | `pip install --user uv` | `brew install uv` |
| `git` | — | `apt install git` | vorhanden |

## Empfohlen / abhängig vom Skript

| Tool | Wofür | Install |
|---|---|---|
| `shellcheck` | bash-Linter | `apt install shellcheck` / `brew install shellcheck` |
| `bats` | bash-Tests | `apt install bats` / `brew install bats-core` |
| `jq` | JSON in bash | `apt install jq` / `brew install jq` |
| `dig` | DNS-Skripte | `apt install dnsutils` / vorhanden |
| `terraform` ≥ 1.6 | terraform-Tasks | [hashicorp.com/downloads](https://developer.hashicorp.com/terraform/install) |
| `ansible` | ansible-Tasks | wird via `uv sync` installiert |
| `stackit` | STACKIT-Tasks | [github.com/stackitcloud/stackit-cli](https://github.com/stackitcloud/stackit-cli) |
| `ssh` | linux-Tasks | vorhanden |
| `gitleaks` | Secret-Scan im pre-commit | `brew install gitleaks` / [Releases](https://github.com/gitleaks/gitleaks/releases) |

## Verifikation

```bash
task doctor
```

Gibt eine Übersicht aus, was vorhanden / was fehlt.

## Credentials

| ENV-Variable | Wofür | Quelle |
|---|---|---|
| `GITLAB_TOKEN` | GitLab-API | PAT, Scope `read_api` |
| `STACKIT_SERVICE_ACCOUNT_TOKEN` | STACKIT-CLI | Service Account im Portal |
| `WIN_USER` / `WIN_PASSWORD` | WinRM | Domänen-Account mit Remoting |

Trag die Werte in `.env` ein (lokal) bzw. in der CI als geschützte Variablen.

## Renovate-Pipeline: Netzwerk-Ziele

Egress (HTTPS/443), den der Runner für den `renovate`-Job erreichen muss:

| Domain | Wofür |
|---|---|
| `<dein-gitlab-host>` (`$CI_SERVER_URL`) | Repo klonen, MRs/Issues schreiben |
| `registry-1.docker.io`, `auth.docker.io` | Pull `renovate/renovate`-Image |
| `app.renovatebot.com` | Merge-Confidence- / Release-Daten |
| `pypi.org`, `files.pythonhosted.org` | Python-Deps (`pyproject.toml`, `uv.lock`) |
| `api.github.com`, `github.com`, `objects.githubusercontent.com`, `raw.githubusercontent.com` | GitHub-Actions-Tags + Changelogs |
| `ghcr.io`, `pkg-containers.githubusercontent.com` | Container-Images aus GHCR (z. B. `astral-sh/uv`) |
| `registry.terraform.io`, `releases.hashicorp.com` | Terraform-Provider/-Module |
| `galaxy.ansible.com` | Ansible-Collections/-Roles |
