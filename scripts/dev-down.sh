#!/usr/bin/env bash
# Tear down all services and shared infra.
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

for svc in flashback-api mcp-server wiki-processor; do
  docker compose -f "$REPO_ROOT/$svc/docker-compose.yml" down 2>/dev/null || true
done

echo "Stopping shared infra..."
docker compose -f "$REPO_ROOT/infra/docker-compose.yml" down
