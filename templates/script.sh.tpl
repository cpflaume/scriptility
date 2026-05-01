#!/usr/bin/env bash
# {{NAME}}.sh - TODO: kurze Beschreibung.
#
# Usage:   {{NAME}}.sh <arg1> [arg2]
# Exit:    0 = ok, 1 = fachlicher Fehler, 2 = Aufruf-Fehler

set -euo pipefail
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"

[ $# -ge 1 ] || die "Usage: $0 <arg1> [arg2]" 2

# TODO: Implementierung
log::info "Hello from {{NAME}}: $*"
