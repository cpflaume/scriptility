#!/usr/bin/env bash
# resolve.sh - DNS-Auflösung (A, AAAA, CNAME) eines Hostnamen.
# Usage: resolve.sh <hostname>
set -euo pipefail
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <hostname>" 2
require_cmd dig

HOST="$1"
for type in A AAAA CNAME; do
    log::info "Records vom Typ $type:"
    dig +short "$HOST" "$type" || true
done
