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
        EXT="sh"
        RUNNER="bash"
        SCRIPT_PATH="$SCRIPT_DIR/${SAFE_NAME}.${EXT}"
        TEST_PATH="$TEST_DIR/${SAFE_NAME}.bats"
        TPL="$ROOT/templates/script.sh.tpl"
        TEST_TPL="$ROOT/templates/script.bats.tpl"
        ;;
    py)
        EXT="py"
        RUNNER="uv run python"
        SCRIPT_PATH="$SCRIPT_DIR/${SAFE_NAME}.${EXT}"
        TEST_PATH="$TEST_DIR/test_${SAFE_NAME}.py"
        TPL="$ROOT/templates/script.py.tpl"
        TEST_TPL="$ROOT/templates/test_py.py.tpl"
        ;;
    *)
        die "Unbekannter Kind: $KIND (bash|py)" 2
        ;;
esac

cp "$TPL" "$SCRIPT_PATH"
cp "$TEST_TPL" "$TEST_PATH"
[ "$KIND" = "bash" ] && chmod +x "$SCRIPT_PATH"
sed -i "s|{{NAME}}|$SAFE_NAME|g" "$SCRIPT_PATH" "$TEST_PATH"
sed -i "s|{{NS}}|$NS|g" "$TEST_PATH"

log::info "Erstellt: $SCRIPT_PATH"
log::info "Erstellt: $TEST_PATH"
log::warn "Bitte Task-Eintrag manuell ergänzen in: $TASKFILE"
log::info "Vorschlag:"
cat <<EOF
  ${NAME}:
    desc: 'TODO. Usage: task ${NS}:${NAME} -- <args>'
    cmds:
      - ${RUNNER} scripts/${NS}/${SAFE_NAME}.${EXT} {{.CLI_ARGS}}
EOF
