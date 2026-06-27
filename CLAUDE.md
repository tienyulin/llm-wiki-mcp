# LLM Wiki MCP — Claude Code Guidelines

## Repository structure (submodules)

This is the **platform** repo. The three services are **git submodules** with
their own repos — edit code in the submodule, commit/PR there, then bump the
pointer here:

| Path (submodule) | Repo |
|------------------|------|
| `wiki-processor/` | [tienyulin/llm-wiki-processor](https://github.com/tienyulin/llm-wiki-processor) |
| `mcp-server/`     | [tienyulin/llm-mcp-server](https://github.com/tienyulin/llm-mcp-server) |
| `flashback-api/`  | [tienyulin/flashback-api](https://github.com/tienyulin/flashback-api) |
| `.claude/skills/` | [tienyulin/llm-wiki-skills](https://github.com/tienyulin/llm-wiki-skills) — shared Claude Code skills (`wiki-doc-author`, `sop-to-spec`) |

- Clone with `git clone --recurse-submodules` (or `git submodule update --init`).
- A service's own README, `.env.example`, `docker-compose.yml`, `docs/`, and tests
  live in its repo. The platform keeps the full-stack `docker-compose.yml`,
  `ci-templates/`, `sop/`, `specs/`, `examples/`, `tests/`, `db/init/`, and
  cross-cutting `docs/`.
- After landing changes in a service repo, update its pointer here:
  `git submodule update --remote <path> && git commit`.

## Git Workflow (Critical)

**ALWAYS follow this workflow:**

1. **Create feature branch** — never commit directly to `main`
   ```bash
   git checkout -b feature/your-feature-name
   # or via GitHub MCP: mcp__github__create_branch
   ```

2. **Make changes and commit** — on the feature branch

3. **Update documentation** — if code changes affect functionality
   - Update relevant guide in `docs/guides/`
   - Update API docs in `docs/api/schema.md` if endpoints changed
   - Update architecture docs in `docs/architecture/` if design changed
   - Add entry to `docs/test-results.md` if test results changed
   - **IMPORTANT:** Every code change should have a corresponding doc update

4. **Open PR** — feature branch → `main`
   - Use `mcp__github__create_pull_request` with `head=your-branch` and `base=main`
   - Include clear description of changes
   - Include what documentation was updated

5. **Merge** — only after PR is opened
   - Use `mcp__github__merge_pull_request` on the PR
   - Prefer "squash" method for clean history

**NEVER:**
- ❌ Push directly to `main` via `git push origin main`
- ❌ Use `mcp__github__push_files` targeting `main` directly
- ❌ Merge without opening a PR first
- ❌ Code changes without updating documentation

### Example Workflow

```bash
# Start feature work
git checkout -b docs/update-readme

# Make changes
# ... edit files ...

# Commit locally
git add .
git commit -m "docs: update README"

# Create PR (via MCP or git push)
mcp__github__create_pull_request \
  --head docs/update-readme \
  --base main \
  --title "docs: update README" \
  --body "..."

# Merge after review
mcp__github__merge_pull_request --pullNumber 27
```

## Documentation Sync Checklist

**Before opening a PR, verify documentation is updated:**

| Change Type | What to Update | File Location |
|------------|-----------------|-------------------|
| **New LLM provider** | Architecture design, setup instructions | `wiki-processor/docs/llm-provider-abstraction.md` (submodule), `docs/guides/local-setup.md` |
| **API endpoint change** | Endpoint reference, schema | `docs/api/schema.md` |
| **Setup/installation** | Local setup guide | `docs/guides/local-setup.md` |
| **Development process** | Development guide | `docs/guides/development.md` |
| **GitLab CI change** | GitLab setup guide | `docs/guides/gitlab-setup.md` |
| **Bug fix/troubleshooting** | Troubleshooting guide | `docs/troubleshooting.md` |
| **New test feature** | Test documentation | `tests/README.md` |
| **Performance test** | Test results | `docs/test-results.md` |
| **Architecture decision** | Architecture docs | `docs/architecture/` |

**Example PR description:**
```
## Changes
- Added new OpenAI provider support
- Updated config.py to support LLM_PROVIDER env var

## Documentation Updated
- ✅ Updated docs/architecture/llm-provider-abstraction.md with provider design
- ✅ Updated docs/guides/local-setup.md with OpenAI setup instructions
- ✅ Updated .env-example with OpenAI configuration
```

---

## Environment

- **Repository:** `tienyulin/llm-wiki-mcp`
- **Development branch:** `claude/resolve-pr-conflicts-Sy3o7` (when working on assigned features)
- **Main branch:** `main` (stable, merge via PR only)

## Key Implementation Details

### LLM Multi-Provider Refactoring (Phase 8 - Complete) ✅

7 providers implemented via abstract `LLMProvider` + `LLMProviderFactory`:
- Minimax, OpenAI, Anthropic, Gemini, Groq, Azure, OpenAI-compatible (Ollama/vLLM/LM Studio)

**Environment variables:**
```env
LLM_PROVIDER=minimax              # Provider name (required)
LLM_API_KEY=sk-...                # API key (backward-compat: falls back to MINIMAX_API_KEY)
LLM_MODEL=MiniMax-M2.7            # Model name (required)
LLM_BASE_URL=http://...           # Only for openai-compatible
LLM_TEMPERATURE=0.3               # Optional, defaults per provider
LLM_MAX_TOKENS=4000               # Optional, defaults to 4000
MOCK_LLM=true                      # For testing without API calls
```

**Key files:**
- `wiki-processor/services/llm/` — provider abstraction
- `wiki-processor/services/llm/config.py` — environment loading
- `wiki-processor/services/llm/factory.py` — provider factory
- All providers in `wiki-processor/services/llm/providers/`

### Vector Index (Postgres + pgvector) ✅

Optional, derived, rebuildable index over wiki.json (MinIO stays the source
of truth). `PG_DSN` empty = disabled, system behaves exactly as before.
Design + measured numbers: `docs/architecture/vector-search.md`.

**Key files:**
- `wiki-processor/services/embeddings/` — OpenAI-compatible embedding client,
  `MOCK_EMBEDDINGS` mode, canonical `entry_to_text`
- `wiki-processor/repository/pg_store.py` — read-write store; **owns the DDL**
  (`ensure_schema`), best-effort post-CAS sync, `/admin/reindex` rebuild
- `mcp-server/repository/pg_reader.py` — read-only queries + circuit breaker
- `mcp-server/services/query_service.py` — owns the PG-first/cached-wiki
  fallback contract; every read endpoint goes through it
- `mcp-server/services/embeddings.py` — query-side `mock_embed` copy,
  **golden-pinned** against the processor copy (change both together)
- `db/` — extension bootstrap + topology notes; compose profile `pg` runs a
  single pgvector/pgvector:pg16 instance (client already supports multi-host
  failover DSNs, so an HA cluster later is a compose-only change)

### Three-Layer Architecture (api / service / repository) ✅

Both FastAPI services follow api → service → repository layering; see
`docs/architecture/service-layering.md` for the layer map, dependency
injection pattern (wiki-processor: `core/deps.py` lru_cache providers +
`Depends`; mcp-server: `app.state` + per-request `QueryService`), and the
test override patterns. Routers live in `api/routers/` (wiki-processor)
and `http_api/routers/` (mcp-server); data access lives in `repository/`.

### SOP → Spec → Service Pipeline ✅

Upstream example app `flashback-api/` (port 8003, compose profile
`flashback`) demonstrates the document-driven flow:

1. `sop/oracle-flashback-recovery.md` — human DBA runbook (DBA-SOP-014)
2. `.claude/skills/sop-to-spec` — generic skill converting any SOP into a
   self-contained implementation spec (risk tiers read/reversible/
   irreversible, precondition→HTTP mapping, mock state, test plan)
3. `specs/oracle-flashback-recovery-api.spec.md` — generated spec; the
   implementation agent reads ONLY this, never the SOP
4. `flashback-api/` — three-layer service built from the spec
   (`MOCK_ORACLE=true` for tests/demo; irreversible ops gated by
   `confirm` token + `approval_id`, everything audited)

The skill (now v5) was tuned over four iterations (full log:
`specs/REVIEWS.md`). Three blind-audit rounds — an independent
fresh-context agent reads only the spec and lists everything an
implementer would have to guess; findings triaged (rejections recorded
with reasons) and attributed to SOP/skill/spec/code — yielded EARS
acceptance criteria, canonical gate order (401→422→404→428→409),
interrogation checklist, blind-audit gate before coding, implementation
feedback step. Iteration 4 (user feedback) added the dual-audience
structure: every spec is Part A (plain-language approval summary with
risk lights, scenarios, sign-off point) + Part B (EARS implementation
spec), the skill follows Anthropic progressive disclosure (lean SKILL.md
+ references/), and every implementation must ship a README. Generality
validated on a second domain: `sop/minio-bucket-disaster-recovery.md` →
`specs/minio-bucket-disaster-recovery-api.spec.md` (spec only).

The full chain closes back into the wiki: an app's README *is* the
markdown fed to wiki-processor (it has an H1 + `METHOD /path` lines that
MOCK_LLM extraction parses), so no per-app generator is needed.
`examples/simulate-app-push.sh` reproduces the GitLab-CI push step
(`examples/send_to_processor.py` now sends `source_app`/`source_version`
for app-level updates); end-to-end walkthrough + real output in
`docs/guides/sop-to-wiki-pipeline.md`, guarded by
`tests/integration/test_readme_to_wiki.py`.

### Git Push 403 Issue (Resolved)

If `git push` fails with HTTP 403, use GitHub MCP API instead:
```python
mcp__github__push_files(
    owner="tienyulin",
    repo="llm-wiki-mcp",
    branch="your-branch",
    files=[...],
    message="commit message"
)
```

After MCP push, local branch will diverge from remote. Sync with:
```bash
git reset --hard origin/your-branch
```

## Next Phases

- **Phase 7:** Large-scale stress testing (100+ apps, 1000+ concurrent agents)
- **Phase 8:** CI/CD integration for auto doc generation
- **Phase 9:** Kubernetes deployment and monitoring
