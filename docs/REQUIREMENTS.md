# Voraussetzungen

## Pflicht

| Tool | Zweck | Install (Debian/Ubuntu) | Install (macOS) |
|---|---|---|---|
| `task` | Entry Point | `sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -b ~/.local/bin` | `brew install go-task` |
| `bash` ≥ 5 | Skripte | meist vorhanden | `brew install bash` |
| `python` ≥ 3.11 | Python-Skripte | `apt install python3` | `brew install python@3.12` |
| `uv` | Python-Deps | `pip install --user uv` | `brew install uv` |
| `git` | — | `apt install git` | vorhanden |

## Empfohlen / abhängig vom Namespace

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
