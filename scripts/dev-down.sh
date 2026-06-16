#!/usr/bin/env bash
# Stop the independent-services dev stack (started by dev-up.sh).
# Pass -v to also wipe the shared infra data volumes.
set -euo pipefail
cd "$(dirname "$0")/.."

WIPE=""
[ "${1:-}" = "-v" ] && WIPE="-v"

for svc in flashback-api mcp-server wiki-processor; do
  ( cd "$svc" && docker compose down ) || true
done

echo "==> shared infra"
( cd infra && docker compose down $WIPE )
