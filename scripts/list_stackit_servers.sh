#!/usr/bin/env bash
# list_servers.sh - Listet alle STACKIT Compute-Server eines Projekts mit Status.
# Usage: list_servers.sh <project_id>
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <project_id>" 2
require_cmd stackit jq column
require_env STACKIT_SERVICE_ACCOUNT_TOKEN

stackit server list --project-id "$1" --output-format json \
    | jq -r '.[] | [.id, .name, .status, .machineType] | @tsv' \
    | column -t -s $'\t'
