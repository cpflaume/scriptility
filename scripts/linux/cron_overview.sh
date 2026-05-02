#!/usr/bin/env bash
# cron_overview.sh - Sammelt alle zeitgesteuerten Jobs eines Linux-Hosts.
#
# Deckt ab:
#   - /etc/crontab und /etc/cron.d/*
#   - /etc/cron.{hourly,daily,weekly,monthly}
#   - per-user crontabs
#   - systemd timers (auf modernen Distros oft der primaere Mechanismus)
#
# Usage: cron_overview.sh <host>
set -euo pipefail
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <host>" 2
require_cmd ssh

ssh -o BatchMode=yes -o ConnectTimeout=5 "$1" '
    echo "=== /etc/crontab ==="
    sudo -n cat /etc/crontab 2>/dev/null || true

    echo
    echo "=== /etc/cron.d/ ==="
    for f in /etc/cron.d/*; do
        [ -f "$f" ] || continue
        echo "--- $f ---"
        sudo -n cat "$f" 2>/dev/null || true
    done

    echo
    echo "=== /etc/cron.{hourly,daily,weekly,monthly} ==="
    for d in /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly; do
        [ -d "$d" ] || continue
        echo "--- $d ---"
        ls -la "$d" 2>/dev/null | tail -n +2 || true
    done

    echo
    echo "=== Per-user crontabs ==="
    for u in $(cut -d: -f1 /etc/passwd); do
        ct=$(sudo -n crontab -u "$u" -l 2>/dev/null) || continue
        if [ -n "$ct" ]; then
            echo "--- $u ---"
            echo "$ct"
        fi
    done

    echo
    echo "=== systemd timers ==="
    if command -v systemctl >/dev/null 2>&1; then
        systemctl list-timers --all --no-pager 2>/dev/null || true
    else
        echo "(systemctl nicht verfuegbar)"
    fi
'
