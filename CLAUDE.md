# LLM Wiki MCP — Claude Code Guidelines

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
| **New LLM provider** | Architecture design, setup instructions | `docs/architecture/llm-provider-abstraction.md`, `docs/guides/local-setup.md` |
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
