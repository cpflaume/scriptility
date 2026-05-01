#!/usr/bin/env bash
# Prüft, ob alle benötigten CLI-Tools installiert sind.
# Gibt eine Tabelle aus und endet mit Exit 1, wenn etwas fehlt.

set -uo pipefail

REQUIRED=(task bash python3 uv git)
OPTIONAL=(shellcheck bats jq terraform ansible stackit ssh)

missing_required=0

printf "%-15s %-10s %s\n" "TOOL" "STATUS" "PATH"
printf "%-15s %-10s %s\n" "----" "------" "----"

check() {
    local tool="$1"
    local kind="$2"
    if path=$(command -v "$tool" 2>/dev/null); then
        printf "%-15s %-10s %s\n" "$tool" "OK" "$path"
    else
        printf "%-15s %-10s %s\n" "$tool" "MISSING" "($kind)"
        [ "$kind" = "required" ] && missing_required=1
    fi
}

for t in "${REQUIRED[@]}"; do check "$t" required; done
for t in "${OPTIONAL[@]}"; do check "$t" optional; done

if [ "$missing_required" -eq 1 ]; then
    echo
    echo "FEHLER: Pflicht-Tools fehlen. Siehe docs/REQUIREMENTS.md" >&2
    exit 1
fi
