#!/usr/bin/env bats
# Tests für {{NS}}/{{NAME}}.sh

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../../scripts/{{NS}}/{{NAME}}.sh"
}

@test "{{NAME}}: zeigt Usage bei fehlenden Argumenten" {
    run "$SCRIPT"
    [ "$status" -eq 2 ]
}
