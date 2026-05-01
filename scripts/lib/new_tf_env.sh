#!/usr/bin/env bash
# new_tf_env.sh - Klont infrastructure/terraform/envs/example zu einer neuen Umgebung.
# Usage: new_tf_env.sh <env_name>
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

[ $# -eq 1 ] || die "Usage: $0 <env_name>" 2
NAME="$1"
ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/infrastructure/terraform/envs/example"
DST="$ROOT/infrastructure/terraform/envs/$NAME"

[ -d "$DST" ] && die "Umgebung existiert bereits: $DST"
cp -r "$SRC" "$DST"
log::info "Neue Umgebung angelegt: $DST"
log::info "Nächste Schritte:  ENV=$NAME task terraform:init && ENV=$NAME task terraform:plan"
