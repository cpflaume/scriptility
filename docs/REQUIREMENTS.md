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

Der GitLab-Runner, auf dem der `renovate`-Job aus `.gitlab-ci.yml` läuft, steht
typischerweise in einem abgeschotteten Netz. Folgende ausgehenden Verbindungen
(HTTPS/443, sofern nicht anders vermerkt) müssen freigeschaltet bzw. über einen
Proxy/Mirror erreichbar sein:

### Pflicht (Runner-Infrastruktur)

| Ziel | Zweck |
|---|---|
| `<dein-gitlab-host>` (`$CI_SERVER_URL`) | Repo klonen, MRs anlegen, Issues/Dashboard schreiben (via `RENOVATE_TOKEN`) |
| Registry des Renovate-Images (Default `docker.io` → `registry-1.docker.io`, `auth.docker.io`, `production.cloudflare.docker.com`) | Pull von `renovate/renovate:latest` beim Job-Start |
| `app.renovatebot.com` | Optional, aber Default: Merge-Confidence- und Release-Daten. Per `RENOVATE_MERGE_CONFIDENCE_ENDPOINT=""` deaktivierbar |

Steht im abgeschotteten Netz eine eigene Registry zur Verfügung, das
Renovate-Image dorthin spiegeln und im Job auf
`<interne-registry>/renovate/renovate:<tag>` umstellen.

### Pflicht (Dependency-Lookups, abhängig von Managern)

Renovate fragt für jeden im Repo aktiven Manager den passenden Upstream ab.
Aktuell relevant für dieses Repo:

| Manager / Datei | Ziel | Zweck |
|---|---|---|
| `pep621` / `uv` (`pyproject.toml`, `uv.lock`) | `pypi.org`, `files.pythonhosted.org` | Python-Paket-Versionen + Metadaten |
| `github-actions` (`.github/workflows/*.yml`) | `api.github.com`, `github.com`, `objects.githubusercontent.com`, `raw.githubusercontent.com` | Action-Tags, Commit-SHAs, Release-Notes |
| `dockerfile` / `docker-compose` / `gitlabci` (z. B. `ghcr.io/astral-sh/uv`, `renovate/renovate`) | `ghcr.io` (+ `pkg-containers.githubusercontent.com`), `registry-1.docker.io`, `auth.docker.io` | Image-Tag-Listen, Manifeste |
| `terraform` (`infrastructure/terraform/`) | `registry.terraform.io`, `releases.hashicorp.com`, ggf. `github.com` (Module per Git-Source) | Provider- und Modul-Versionen |
| `ansible-galaxy` (`infrastructure/ansible/`, `requirements.yml`) | `galaxy.ansible.com` | Collection-/Role-Versionen |
| Changelog-Fetching (alle Manager) | `api.github.com`, `gitlab.com/api/v4` | Release-Notes in MR-Bodies (per `RENOVATE_FETCH_CHANGE_LOGS=off` abschaltbar) |

### GitHub-API-Token empfohlen

Renovate fragt für Changelogs und Container-Tag-Lookups häufig `api.github.com`
ab — ohne Auth greift dort das anonyme Rate-Limit von 60 req/h. CI/CD-Variable
`GITHUB_COM_TOKEN` (Read-only PAT, Scope `public_repo` reicht) im Projekt
setzen, dann nutzt Renovate ihn automatisch.

### Proxy / Air-Gap

- Standard-Proxy via `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` (Job- oder
  Runner-ENV) — Renovate respektiert diese Variablen.
- Für komplett air-gapped Umgebungen interne Mirrors für PyPI, Container-
  Registry, Terraform-Registry und Ansible-Galaxy aufsetzen und Renovate per
  `hostRules` (in `renovate.json`) auf diese Mirrors umbiegen.
