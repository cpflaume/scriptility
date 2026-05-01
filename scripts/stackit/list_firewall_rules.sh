#!/usr/bin/env bash
# list_firewall_rules.sh - Listet alle Security-Group-Rules eines STACKIT-Projekts.
# Usage: list_firewall_rules.sh <project_id>
set -euo pipefail
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <project_id>" 2
require_cmd stackit jq
require_env STACKIT_SERVICE_ACCOUNT_TOKEN

PROJECT_ID="$1"

# stackit-cli liefert JSON; mit jq normalisieren.
stackit security-group list --project-id "$PROJECT_ID" --output-format json \
    | jq -r '.[] | {sg_id: .id, sg_name: .name, rules: .rules}' \
    | jq -s '.'
