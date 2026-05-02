#!/usr/bin/env bash
# Gemeinsame Helfer für bash-Skripte.
# Einbinden via:  source "$(dirname "$0")/../lib/common.sh"

set -euo pipefail

# ANSI-Farben (nur wenn TTY)
if [ -t 2 ]; then
    readonly C_RED='\033[0;31m'
    readonly C_YELLOW='\033[0;33m'
    readonly C_GREEN='\033[0;32m'
    readonly C_RESET='\033[0m'
else
    readonly C_RED='' C_YELLOW='' C_GREEN='' C_RESET=''
fi

log::info()  { printf "%b[INFO]%b  %s\n" "$C_GREEN"  "$C_RESET" "$*" >&2; }
log::warn()  { printf "%b[WARN]%b  %s\n" "$C_YELLOW" "$C_RESET" "$*" >&2; }
log::error() { printf "%b[ERROR]%b %s\n" "$C_RED"    "$C_RESET" "$*" >&2; }

# die "msg" [exit_code]   - Logged Fehler und beendet
die() {
    log::error "$1"
    exit "${2:-1}"
}

# require_cmd <cmd> [<cmd> ...] - prüft ob CLI-Tools vorhanden sind
require_cmd() {
    local missing=()
    for cmd in "$@"; do
        command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        die "Fehlende Befehle: ${missing[*]}"
    fi
}

# require_env <VAR> [<VAR> ...] - prüft ob ENV-Variablen gesetzt sind
require_env() {
    local missing=()
    for var in "$@"; do
        [ -n "${!var:-}" ] || missing+=("$var")
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        die "Fehlende Umgebungsvariablen: ${missing[*]}"
    fi
}
