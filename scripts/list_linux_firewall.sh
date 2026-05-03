#!/usr/bin/env bash
# list_firewall.sh - Zeigt Firewall-Regeln (nftables bevorzugt, sonst iptables).
# Usage: list_firewall.sh <host>
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <host>" 2
require_cmd ssh

ssh -o BatchMode=yes -o ConnectTimeout=5 "$1" '
    if command -v nft >/dev/null 2>&1; then
        sudo -n nft list ruleset
    elif command -v iptables >/dev/null 2>&1; then
        sudo -n iptables -L -v -n
    else
        echo "Weder nft noch iptables verfügbar" >&2; exit 1
    fi
'
