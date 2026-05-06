#!/usr/bin/env bash
# Wird einmalig nach dem Erstellen des Dev Containers ausgeführt.
# Bootet die lokale Entwicklungsumgebung (venv, pre-commit, .env)
# und prüft, dass alle Pflicht-Tools verfügbar sind.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ task setup (venv, pre-commit, .env)"
task setup

echo
echo "→ task doctor"
task doctor || true

echo
echo "Dev Container bereit. 'task --list-all' zeigt alle Skripte."
