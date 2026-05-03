#!/usr/bin/env bats
# Tests für scripts/check_port.sh

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../scripts/check_port.sh"
}

@test "check_port: usage bei zu wenig args" {
    run "$SCRIPT"
    [ "$status" -eq 2 ]
}

@test "check_port: usage bei nicht-numerischem Port" {
    run "$SCRIPT" 127.0.0.1 abc
    [ "$status" -eq 2 ]
}

@test "check_port: usage bei Port out-of-range" {
    run "$SCRIPT" 127.0.0.1 99999
    [ "$status" -eq 2 ]
}

@test "check_port: --help liefert Exit 2" {
    run "$SCRIPT" --help
    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage"* ]]
}

@test "check_port: nicht erreichbarer Port liefert 1" {
    # Port 1 ist auf den meisten Systemen geschlossen, mit kurzem Timeout.
    run "$SCRIPT" 127.0.0.1 1 1
    [ "$status" -eq 1 ]
}
