#!/usr/bin/env bash
# list_users.sh - Listet lokale Benutzer (UID >= 1000) eines Linux-Hosts.
# Usage: list_users.sh <host>
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <host>" 2
require_cmd ssh

ssh -o BatchMode=yes -o ConnectTimeout=5 "$1" \
    "awk -F: '\$3 >= 1000 && \$1 != \"nobody\" {printf \"%-20s %-6s %s\\n\", \$1, \$3, \$7}' /etc/passwd"
