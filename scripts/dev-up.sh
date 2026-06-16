#!/usr/bin/env bash
# Start the whole platform as INDEPENDENT services sharing one infra.
# Brings up the shared infra (minio + pg on llm-wiki-net), then each service's
# own compose attached to it. All services run at once, share data, no port
# clash. (Alternative: `docker compose up` runs the self-contained full stack.)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> shared infra (minio + pg, network llm-wiki-net)"
( cd infra && docker compose up -d )

for svc in wiki-processor mcp-server flashback-api; do
  echo "==> $svc"
  (
    cd "$svc"
    [ -f .env ] || cp .env.example .env
    docker compose up -d --build
  )
done

cat <<'EOF'

Up:
  wiki-processor  http://localhost:8001/health
  mcp-server      http://localhost:8002/health
  flashback-api   http://localhost:8003/health
  MinIO console   http://localhost:9001  (minioadmin/minioadmin)
  Postgres        localhost:5432         (wiki/wikipass)

Stop:  scripts/dev-down.sh
EOF
