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
| `AD_USER` / `AD_PASSWORD` | AD-LDAP (read-only) | Domänen-Account mit Lese-Rechten |

Trag die Werte in `.env` ein (lokal) bzw. in der CI als geschützte Variablen.

## Skript-spezifisch: `ad-app-onboarding`

`task ad-app-onboarding` liest den Ist-Zustand aus der on-prem Active Directory
(Service-/gMSA-Konto, SPNs/Hostnamen, Zugriffs-Gruppen + Mitglieder) per
**LDAP(S) direkt vom Domain Controller** (Simple Bind mit User + Passwort). Ein
Windows-Jump-Host oder RSAT-PowerShell ist **nicht** mehr nötig. Damit der Lauf
funktioniert, müssen **alle** folgenden Voraussetzungen erfüllt sein:

**1. Credentials / ENV** (siehe auch `.env.example`)

| ENV-Variable | Pflicht | Default | Wofür |
|---|---|---|---|
| `AD_USER` | ja | — | Bind-DN oder UPN (z. B. `svc-read@corp.example`) |
| `AD_PASSWORD` | ja | — | Passwort dazu |
| `AD_PORT` | nein | `636`/`389` | LDAP-Port (636 bei LDAPS, sonst 389) |
| `AD_USE_SSL` | nein | `true` | `false` = LDAP im Klartext (nur bewusst) |
| `AD_TLS_VERIFY` | nein | `true` | `false` deaktiviert die Zertifikatsprüfung (nur bewusst) |
| `AD_CA_BUNDLE` | nein | — | Pfad zu einer CA-Bundle-Datei (private CA) |
| `AD_BASE_DN` | nein | — | Such-Basis-DN; ohne Angabe der `defaultNamingContext` des DC |

**2. Ziel-Host (`--host`)**

- Ein **Domain Controller**, der per LDAP(S) erreichbar ist (standardmäßig
  **LDAPS auf Port 636**); der LDAP-Dienst muss laufen und der Port aus dem
  Runner erreichbar sein.
- Bei LDAPS muss das Server-Zertifikat vertrauenswürdig sein (öffentliche CA im
  Trust-Store, oder private CA via `AD_CA_BUNDLE`); andernfalls scheitert die
  Zertifikatsprüfung (oder man setzt bewusst `AD_TLS_VERIFY=false`).

**3. Rechte des `AD_USER`-Accounts**

- **Lese**-Rechte in der AD reichen — das Skript verändert nichts (der Bind läuft
  `read_only`). Gelesen werden Konten (`user`/`msDS-GroupManagedServiceAccount`),
  Gruppen und rekursive Mitgliedschaften (via `LDAP_MATCHING_RULE_IN_CHAIN`). Ein
  normaler Domänen-Benutzer kann diese Objekte i. d. R. lesen.

**4. Optionaler `--spec`-Modus**

- `--spec <datei.json>` erwartet eine **lokal lesbare JSON-Datei** mit dem
  Soll-Zustand (`account`, optional `type`, `hostnames`, `groups[].members`).
  Ohne `--spec` läuft nur der Dump (kein pass/fail).

Die Python-Abhängigkeit `ldap3` ist Projekt-Dependency (`pyproject.toml`); die
Spec wird mit der stdlib gelesen.

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
