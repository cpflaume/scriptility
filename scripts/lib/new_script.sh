#!/usr/bin/env bash
# new_script.sh - Generiert neues Skript inkl. Test und registriert es als Task.
# Usage: new_script.sh <bash|py> <skript-name>
#   z.B. new_script.sh bash ping-host
#        new_script.sh py   list-foo
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

[ $# -eq 2 ] || die "Usage: $0 <bash|py> <skript-name>" 2

KIND="$1"
NAME="$2"

# Validierung: nur klein, Buchstaben/Ziffern/Bindestrich, kein /.
[[ "$NAME" =~ ^[a-z][a-z0-9-]*$ ]] || die "Ungültiger Name: '$NAME' (nur a-z, 0-9, -; muss mit Buchstabe starten)" 2

SAFE_NAME="${NAME//-/_}"
TASK_NAME="$NAME"

ROOT="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="$ROOT/scripts"
TEST_DIR="$ROOT/tests"
TASKFILE="$ROOT/Taskfile.yml"

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
        # Wenn ein bash-Skript mit gleichem Stem existiert, Task '<name>-py' nennen.
        [ -e "$SCRIPT_DIR/${SAFE_NAME}.sh" ] && TASK_NAME="${NAME}-py"
        ;;
    *)
        die "Unbekannter Kind: $KIND (bash|py)" 2
        ;;
esac

[ -e "$SCRIPT_PATH" ] && die "Skript existiert bereits: $SCRIPT_PATH"
[ -e "$TEST_PATH" ] && die "Test existiert bereits: $TEST_PATH"

# Markierung im Taskfile.yml prüfen, bevor wir Dateien schreiben.
grep -q '<<< END AUTO-GENERATED <<<' "$TASKFILE" \
    || die "Marker '<<< END AUTO-GENERATED <<<' fehlt in $TASKFILE" 1
grep -qE "^  ${TASK_NAME}:" "$TASKFILE" \
    && die "Task '${TASK_NAME}' existiert bereits in $TASKFILE" 1

cp "$TPL" "$SCRIPT_PATH"
cp "$TEST_TPL" "$TEST_PATH"
[ "$KIND" = "bash" ] && chmod +x "$SCRIPT_PATH"

# `sed -i` ist nicht portabel: GNU akzeptiert `-i`, BSD/macOS verlangt `-i ''`.
# Das Backup-Pattern (`-i.bak` plus Loeschen) funktioniert auf beiden.
sed -i.bak "s|{{NAME}}|$SAFE_NAME|g" "$SCRIPT_PATH" "$TEST_PATH"
rm -f "${SCRIPT_PATH}.bak" "${TEST_PATH}.bak"

# Task-Block vor der END-Markierung einfügen.
TMP_BLOCK="$(mktemp)"
trap 'rm -f "$TMP_BLOCK"' EXIT
{
    printf '  %s:\n' "$TASK_NAME"
    printf "    desc: 'TODO: Beschreibung. Usage: task %s -- <args>'\n" "$TASK_NAME"
    printf "    cmds: ['%s scripts/%s.%s {{.CLI_ARGS}}']\n" "$RUNNER" "$SAFE_NAME" "$EXT"
} > "$TMP_BLOCK"

TMP_OUT="$(mktemp)"
awk -v block="$TMP_BLOCK" '
    /<<< END AUTO-GENERATED <<</ {
        while ((getline line < block) > 0) print line
        close(block)
    }
    { print }
' "$TASKFILE" > "$TMP_OUT"
mv "$TMP_OUT" "$TASKFILE"

log::info "Erstellt: $SCRIPT_PATH"
log::info "Erstellt: $TEST_PATH"
log::info "Registriert: task $TASK_NAME (in $TASKFILE)"
log::info "Run: task $TASK_NAME -- <args>"
