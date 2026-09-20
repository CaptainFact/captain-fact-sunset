#!/usr/bin/env bash
# Serve the static sunset page locally.
#
# Usage:
#   ./scripts/dev-server.sh
#   ./scripts/dev-server.sh 8080

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8000}"

cd "$ROOT"
echo "Serving ${ROOT} at http://localhost:${PORT}/"
exec python3 -m http.server "$PORT"
