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

## Skript-spezifisch: `ad-app-onboarding`

`task ad-app-onboarding` liest den Ist-Zustand aus der on-prem Active Directory
(Service-/gMSA-Konto, SPNs/Hostnamen, Zugriffs-Gruppen + Mitglieder) per
PowerShell `Get-AD*` über WinRM. Damit der Lauf funktioniert, müssen **alle**
folgenden Voraussetzungen erfüllt sein:

**1. Credentials / ENV** (siehe auch `.env.example`)

| ENV-Variable | Pflicht | Default | Wofür |
|---|---|---|---|
| `WIN_USER` | ja | — | WinRM-/Domänen-Account |
| `WIN_PASSWORD` | ja | — | Passwort dazu |
| `WIN_TRANSPORT` | nein | `ntlm` | `ntlm` \| `kerberos` \| `credssp` \| `basic` |
| `WIN_PORT` | nein | `5986` | WinRM-Port (HTTPS) |
| `WIN_TLS_VERIFY` | nein | `true` | `false` deaktiviert die Zertifikatsprüfung (nur bewusst) |

**2. Ziel-Host (`--host`)**

- Erreichbar über WinRM (standardmäßig **HTTPS auf Port 5986**); der WinRM-Dienst
  muss laufen und der Port aus dem Runner erreichbar sein.
- Es muss das **RSAT-PowerShell-Modul `ActiveDirectory`** installiert sein
  (`Import-Module ActiveDirectory` muss klappen). Das ist auf einem
  Domänen-Mitglied als Admin-/Jump-Host (RSAT-Feature) oder direkt auf einem
  **Domain Controller** gegeben. Ein reiner Nicht-Domänen-Host reicht **nicht**.
- Host ist der Domäne beigetreten bzw. kann die Domäne auflösen/erreichen, damit
  die `Get-AD*`-Cmdlets einen DC finden.

**3. Rechte des `WIN_USER`-Accounts**

- **Lese**-Rechte in der AD reichen — das Skript verändert nichts. Konkret
  genutzt: `Get-ADServiceAccount`, `Get-ADUser`, `Get-ADGroup`,
  `Get-ADGroupMember -Recursive` und (nur bei `--group-filter`) `Get-ADGroup
  -Filter`. Ein normaler Domänen-Benutzer kann diese Objekte i. d. R. lesen.
- Der Account braucht **WinRM-Remoting-Rechte** auf dem Ziel-Host (Mitglied der
  lokalen Gruppe *Remote Management Users* oder Administrator).

**4. Optionaler `--spec`-Modus**

- `--spec <datei.json>` erwartet eine **lokal lesbare JSON-Datei** mit dem
  Soll-Zustand (`account`, optional `type`, `hostnames`, `groups[].members`).
  Ohne `--spec` läuft nur der Dump (kein pass/fail).

Es werden **keine** neuen ENV-Variablen und **keine** zusätzliche Python-/System-
Abhängigkeit benötigt (`pywinrm` ist bereits Projekt-Dependency, die Spec wird
mit der stdlib gelesen).

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
