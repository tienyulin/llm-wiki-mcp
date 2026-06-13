#!/usr/bin/env bash
# Simulate the GitLab CI push step (ci-templates/generate-and-push-wiki.yml,
# push_wiki stage) for an application — locally, against a running
# wiki-processor. Default target is flashback-api's README.
#
# This is the "第三步：推送更新" from the root README, run by hand:
#   collect the app's markdown -> POST /process with source_app -> wiki update.
#
# Usage:
#   docker compose up -d minio wiki-processor mcp-server
#   bash examples/simulate-app-push.sh
#
# Override the app being pushed:
#   SOURCE_APP=my-app MARKDOWN_PATTERN='path/to/*.md' MARKDOWN_KEY=my-app.md \
#     bash examples/simulate-app-push.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export SOURCE_APP="${SOURCE_APP:-flashback-api}"
export SOURCE_VERSION="${SOURCE_VERSION:-0.1.0}"
export MARKDOWN_PATTERN="${MARKDOWN_PATTERN:-flashback-api/README.md}"
export MARKDOWN_KEY="${MARKDOWN_KEY:-flashback-api.md}"
export WIKI_PROCESSOR_URL="${WIKI_PROCESSOR_URL:-http://localhost:8001}"
# PROCESSOR_API_KEY is forwarded automatically by send_to_processor.py if set.

echo "Simulating CI push for app='$SOURCE_APP' (version=$SOURCE_VERSION)"
echo "  markdown: $MARKDOWN_PATTERN  ->  key: $MARKDOWN_KEY"
echo "  target:   $WIKI_PROCESSOR_URL/process"

exec python3 examples/send_to_processor.py
