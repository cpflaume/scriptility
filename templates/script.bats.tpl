#!/usr/bin/env bats
# Tests für {{NAME}}.sh

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../scripts/{{NAME}}.sh"
}

@test "{{NAME}}: zeigt Usage bei fehlenden Argumenten" {
    run "$SCRIPT"
    [ "$status" -eq 2 ]
}
