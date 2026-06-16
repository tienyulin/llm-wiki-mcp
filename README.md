# LLM Wiki MCP — Platform

集中式 Wiki 平台：每個應用獨立生成 API 文檔 → 推送到處理器 → LLM 萃取 → 存入
MinIO + Postgres/pgvector → 透過 MCP 查詢（關鍵字 + 語意）。供團隊共享與 LLM 理解。

This repository is the **platform / umbrella**. The services live in their own
repositories and are wired in here as **git submodules**, so each one builds,
runs, and deploys independently — the platform just composes them for full-stack
local dev and integration.

## Components (separate repos)

| Service | Repo | Role |
|---------|------|------|
| **wiki-processor** | [tienyulin/llm-wiki-processor](https://github.com/tienyulin/llm-wiki-processor) | `POST /process` — LLM extraction → MinIO (CAS) → pgvector index |
| **mcp-server** | [tienyulin/llm-mcp-server](https://github.com/tienyulin/llm-mcp-server) | read-only query API (keyword + semantic), MinIO/PG with fallback |
| **flashback-api** | [tienyulin/flashback-api](https://github.com/tienyulin/flashback-api) | example upstream app (Oracle Flashback Recovery API) |

Each repo has its own README, `.env.example`, `docker-compose.yml`, `docs/`, and tests.

## Architecture

```
100+ apps ──(CI: ci-templates/)──> wiki-processor:8001/process
                                        │  LLM extract (app-level incremental, ETag CAS)
                                        v
                                   MinIO (wiki.json — source of truth)
                                        │  best-effort sync
                                        v
                                   Postgres + pgvector (derived index)
                                        ^
                                   mcp-server:8002  ──>  Claude / LLM
```
The index layer is optional (`PG_DSN=` disables it → MinIO scan fallback).

## Two ways to run

```bash
git clone --recurse-submodules https://github.com/tienyulin/llm-wiki-mcp
cd llm-wiki-mcp
```
(Already cloned without submodules? `git submodule update --init`.)

### Mode A — one-shot full stack (self-contained)
Everything in one compose project, with its own bundled minio + pg:
```bash
cp .env-example .env            # keep MOCK_LLM=true for a no-key run
docker compose up -d --build    # minio + pg + wiki-processor + mcp-server
curl localhost:8001/health && curl localhost:8002/health
```

### Mode B — independent services on shared infra (dev)
One **shared** minio + pg ([`infra/`](infra) = the `llm-wiki-infra` submodule),
then each service from its **own** compose attached to it. Run/restart/develop
each service independently; they share data and don't clash on infra ports:
```bash
scripts/dev-up.sh        # infra + wiki-processor + mcp-server + flashback-api
scripts/dev-down.sh      # stop (add -v to wipe shared data)
```
Or by hand: `(cd infra && docker compose up -d)` then `cd <service> && docker compose up -d`.

> Run **one mode at a time** — both bind host ports 9000/9001/5432.

Update services to their latest: `git submodule update --remote`.

## Platform contents

- `docker-compose.yml` — Mode A full stack (self-contained, bundled infra)
- `infra/` — submodule [llm-wiki-infra](https://github.com/tienyulin/llm-wiki-infra): shared minio + pg (Mode B)
- `scripts/dev-up.sh` · `scripts/dev-down.sh` — Mode B orchestration
- `ci-templates/` — the GitLab CI template apps include to generate + push docs
- `sop/`, `specs/` — example SOP → spec → API source material
- `examples/` — `simulate-app-push.sh`, `send_to_processor.py`
- `tests/` — cross-service integration + stress (`tests/stress/STRESS_TEST_PLAN.md`)
- `db/init/` — pgvector + pg_trgm extension bootstrap
- `docs/` — cross-cutting docs (below)

## Documentation

- **[docs/README.md](docs/README.md)** — full index
- Architecture (cross-cutting): [service-layering](docs/architecture/service-layering.md),
  [vector-search](docs/architecture/vector-search.md)
- Guides: [local-setup](docs/guides/local-setup.md),
  [end-to-end-example](docs/guides/end-to-end-example.md),
  [sop-to-wiki-pipeline](docs/guides/sop-to-wiki-pipeline.md),
  [gitlab-setup](docs/guides/gitlab-setup.md)
- Worked example with real data: [docs/examples/real-semantic-walkthrough.md](docs/examples/real-semantic-walkthrough.md)
- Per-service docs live in each service repo's `docs/`.

## Tests

- Each service repo: `cd <repo> && python -m pytest` (hermetic).
- Platform integration/stress: `tests/` — see [tests/README.md](tests/README.md).
