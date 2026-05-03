#!/usr/bin/env bash
# check_port.sh - Prüft TCP-Erreichbarkeit von HOST:PORT.
#
# Usage:   check_port.sh <host> <port> [timeout_seconds]
# Exit:    0 = offen, 1 = geschlossen/timeout, 2 = Aufruf-Fehler
# Beispiel: check_port.sh 10.0.0.1 443 5

set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

usage() {
    sed -n '/^# Usage:/,/^# Beispiel/p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

case "${1:-}" in -h|--help) usage ;; esac
{ [ $# -lt 2 ] || [ $# -gt 3 ]; } && usage

HOST="$1"
PORT="$2"
TIMEOUT="${3:-3}"

# Validierung
[[ "$PORT" =~ ^[0-9]+$ ]] || die "Port muss numerisch sein: $PORT" 2
[ "$PORT" -ge 1 ] || die "Port ausserhalb 1-65535: $PORT" 2
[ "$PORT" -le 65535 ] || die "Port ausserhalb 1-65535: $PORT" 2
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || die "Timeout muss numerisch (Sekunden) sein: $TIMEOUT" 2

require_cmd timeout

# /dev/tcp ist eine bash-Built-in; HOST/PORT als Positional-Args durchreichen,
# damit keine Shell-Interpolation in den `bash -c`-String stattfindet (Injection).
# shellcheck disable=SC2016  # Expansion findet erst in der inneren Shell statt - genau so gewollt.
if timeout "$TIMEOUT" bash -c 'exec 3<>/dev/tcp/"$1"/"$2"' _ "$HOST" "$PORT" 2>/dev/null; then
    log::info "${HOST}:${PORT} ist erreichbar (timeout=${TIMEOUT}s)"
    exit 0
else
    log::warn "${HOST}:${PORT} ist NICHT erreichbar (timeout=${TIMEOUT}s)"
    exit 1
fi
