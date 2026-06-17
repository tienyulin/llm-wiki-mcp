#!/usr/bin/env bash
# Bring up shared infra then each service on llm-wiki-net.
# Run mode: independent services sharing one MinIO + Postgres.
# (Do not run alongside `docker compose up` in the repo root — they share ports 9000/9001/5432.)
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting shared infra..."
docker compose -f "$REPO_ROOT/infra/docker-compose.yml" up -d

echo "Starting wiki-processor..."
docker compose -f "$REPO_ROOT/wiki-processor/docker-compose.yml" up -d --build

echo "Starting mcp-server..."
docker compose -f "$REPO_ROOT/mcp-server/docker-compose.yml" up -d --build

echo "Starting flashback-api..."
docker compose -f "$REPO_ROOT/flashback-api/docker-compose.yml" up -d --build

echo "All services up. Endpoints:"
echo "  wiki-processor : http://localhost:8001/health"
echo "  mcp-server     : http://localhost:8002/health"
echo "  flashback-api  : http://localhost:8003/health"
echo "  MinIO console  : http://localhost:9001"
