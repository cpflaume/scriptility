#!/usr/bin/env bash
# cron_overview.sh - Sammelt System- und User-Cronjobs.
# Usage: cron_overview.sh <host>
set -euo pipefail
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <host>" 2

ssh -o BatchMode=yes -o ConnectTimeout=5 "$1" '
    echo "=== /etc/crontab ==="; sudo -n cat /etc/crontab 2>/dev/null || true
    echo; echo "=== /etc/cron.d/ ==="; sudo -n ls -la /etc/cron.d/ 2>/dev/null || true
    echo; echo "=== Per-user crontabs ==="
    for u in $(cut -d: -f1 /etc/passwd); do
        ct=$(sudo -n crontab -u "$u" -l 2>/dev/null) || continue
        [ -n "$ct" ] && echo "--- $u ---" && echo "$ct"
    done
'
