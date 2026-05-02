#!/usr/bin/env bash
# resolve.sh - DNS-Auflösung mit den gängigsten Record-Typen.
# Usage: resolve.sh <hostname> [type ...]
#   default: A AAAA CNAME MX TXT NS
set -euo pipefail
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"

[ $# -ge 1 ] || die "Usage: $0 <hostname> [type ...]" 2
require_cmd dig

HOST="$1"
shift
TYPES=("$@")
[ "${#TYPES[@]}" -eq 0 ] && TYPES=(A AAAA CNAME MX TXT NS)

for type in "${TYPES[@]}"; do
    log::info "Records vom Typ $type:"
    dig +short "$HOST" "$type" || true
done
