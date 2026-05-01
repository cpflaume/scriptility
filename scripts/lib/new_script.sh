#!/usr/bin/env bash
# new_script.sh - Generiert neues Skript inkl. Test+Task aus templates/.
# Usage: new_script.sh <bash|py> <namespace> <skript-name>
#   z.B. new_script.sh bash network ping-host
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

[ $# -eq 3 ] || die "Usage: $0 <bash|py> <namespace> <skript-name>" 2

KIND="$1"
NS="$2"
NAME="$3"
SAFE_NAME="${NAME//-/_}"

ROOT="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="$ROOT/scripts/$NS"
TEST_DIR="$ROOT/tests/$NS"
TASKFILE="$ROOT/taskfiles/${NS}.yml"

mkdir -p "$SCRIPT_DIR" "$TEST_DIR"

case "$KIND" in
    bash)
        SCRIPT_PATH="$SCRIPT_DIR/${SAFE_NAME}.sh"
        TEST_PATH="$TEST_DIR/${SAFE_NAME}.bats"
        cp "$ROOT/templates/script.sh.tpl" "$SCRIPT_PATH"
        cp "$ROOT/templates/script.bats.tpl" "$TEST_PATH"
        chmod +x "$SCRIPT_PATH"
        sed -i "s|{{NAME}}|$SAFE_NAME|g" "$SCRIPT_PATH" "$TEST_PATH"
        sed -i "s|{{NS}}|$NS|g" "$TEST_PATH"
        ;;
    py)
        SCRIPT_PATH="$SCRIPT_DIR/${SAFE_NAME}.py"
        TEST_PATH="$TEST_DIR/test_${SAFE_NAME}.py"
        cp "$ROOT/templates/script.py.tpl" "$SCRIPT_PATH"
        cp "$ROOT/templates/test_py.py.tpl" "$TEST_PATH"
        sed -i "s|{{NAME}}|$SAFE_NAME|g" "$SCRIPT_PATH" "$TEST_PATH"
        ;;
    *)
        die "Unbekannter Kind: $KIND (bash|py)" 2
        ;;
esac

log::info "Erstellt: $SCRIPT_PATH"
log::info "Erstellt: $TEST_PATH"
log::warn "Bitte Task-Eintrag manuell ergänzen in: $TASKFILE"
log::info "Vorschlag:"
cat <<EOF
  ${NAME}:
    desc: 'TODO. Usage: task ${NS}:${NAME} -- <args>'
    cmds:
      - ${KIND/py/uv run python} scripts/${NS}/${SAFE_NAME}.${KIND/py/py}${KIND/bash/.sh} {{.CLI_ARGS}}
EOF
