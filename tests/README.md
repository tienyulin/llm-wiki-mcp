# Test Suite

This directory contains all tests for the LLM Wiki MCP project, organized by category.

## 📁 Structure

```
tests/
├── integration/             # Integration tests
└── stress/                  # Performance & stress tests

wiki-processor/tests/        # Unit tests (wiki-processor)
mcp-server/tests/            # Unit tests (mcp-server)
mcp-server/http_api/test_http_api.py  # HTTP API spec tests
```

> ⚠️ `wiki-processor` and `mcp-server` are **separate import roots**. Unit
> tests must be run from each package's directory (`python -m pytest` puts
> the cwd on `sys.path`). Running `pytest wiki-processor/tests/ mcp-server/tests/`
> from the repo root does **not** work (import errors + duplicate `tests`
> package names).

## 🧪 Test Categories

### Unit Tests
**Location:** within service packages

- `wiki-processor/tests/test_llm.py` — LLM provider abstraction
- `wiki-processor/tests/test_routes.py` — API endpoint handlers (empty-markdowns 422,
  X-API-Key auth 401/200/dev mode)
- `wiki-processor/tests/test_processor.py` — change detection logic
- `wiki-processor/tests/test_concurrency.py` — **concurrency regression**: 20 parallel
  `process()` calls must not lose updates; CAS conflict injection; resubmission
  replaces only that app's entries; v2 schema migration
- `wiki-processor/tests/test_storage_cas.py` — MinIO conditional-write behavior
  (runs against a real MinIO, auto-skips when unreachable)
- `mcp-server/tests/test_rate_limit.py` — token-bucket middleware (burst, 429, refill)
- `mcp-server/tests/test_wiki_service.py` — wiki service methods
- `mcp-server/tests/test_cache.py` — cache TTL + exact-match invalidation
- `mcp-server/http_api/test_http_api.py` — HTTP read API behavior spec

Unit tests are **hermetic** — no MinIO or LLM API required
(`wiki-processor/tests/conftest.py` stubs the Minio SDK and sets `MOCK_LLM=true`).

**Run unit tests:**
```bash
cd wiki-processor && python -m pytest          # 33 tests (CAS tests skip without MinIO)
cd mcp-server && python -m pytest              # 28 tests (tests/ + http_api/)
```

### Integration Tests
**Location:** `tests/integration/`

- `test_processor.py` — payload/logic validation (pytest, no services needed)
- `test_docker_integration.py` — end-to-end: 6 scenarios against running services
  (single app, multi app, wiki structure, API detail, 10 parallel apps, incremental update)

**Requires running services** — either `docker-compose up`, or without docker
(see `docs/troubleshooting.md` § 在沒有 Docker 的環境執行測試): local MinIO
binary + two uvicorn processes with `MOCK_LLM=true` and `MCP_SERVER_URL` set.

**Run integration tests:**
```bash
python -m pytest tests/integration/test_processor.py     # pytest-style
python tests/integration/test_docker_integration.py      # script, needs services
```

### Stress Tests
**Location:** `tests/stress/` — these are **scripts, run with `python`, not pytest**

- `test_mock_stress.py` — 100-way concurrent updates on in-memory CAS storage:
  no lost updates, resubmission replacement, app isolation, audit completeness
- `test_real_service_stress.py` — **100 concurrent apps against the real HTTP
  services + real MinIO (real ETag conditional writes)**; asserts per-app
  integrity: every app's derived entries must appear in the final wiki

**Run stress tests:**
```bash
python tests/stress/test_mock_stress.py            # hermetic, no services
python tests/stress/test_real_service_stress.py    # needs running services
```

> The three legacy v1-model scripts (test_poc_standalone / test_poc_100_apps /
> test_100_apps_performance) were removed with the schema-v2 migration — the
> data model they exercised no longer exists.

## 📊 Test Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `MOCK_LLM` | false | Use mock LLM responses (skip API calls) |
| `LLM_PROVIDER` | minimax | LLM provider for tests |
| `LLM_API_KEY` | (unset) | For testing with a real LLM API |
| `MINIO_ENDPOINT` | minio:9000 | MinIO address (use `localhost:9000` locally) |
| `MCP_SERVER_URL` | (unset) | Enables cache invalidation from wiki-processor |
| `PROCESSOR_API_KEY` | (unset) | /process auth key; integration/stress clients send it automatically |
| `RATE_LIMIT_RPS` | 0 | mcp-server per-IP rate limit (0 = disabled) |
| `STRESS_N_APPS` | 100 | App count for `test_real_service_stress.py` |

## ✅ Expected Results

| Test Suite | Expected Status | Duration |
|-----------|-----------------|----------|
| Unit tests (61 total) | All passing | ~2s |
| Integration tests (6 scenarios) | All passing | ~10s |
| Stress tests | All passing | ~10s (with MOCK_LLM=true) |

Latest verified run: see `docs/test-results.md`.

## 🐛 Debugging Tests

```bash
python -m pytest -v --log-cli-level=DEBUG          # detailed logging
python -m pytest tests/test_concurrency.py -v      # single file (from package dir)
python -m pytest --pdb                             # drop into pdb on failure
```

## 📝 Writing New Tests

- **Unit tests:** place in the package's `tests/` directory; keep them hermetic
  (use the in-memory storage / fake LLM patterns from `test_concurrency.py`)
- **Integration tests:** place in `tests/integration/`
- **Stress tests:** place in `tests/stress/` as runnable scripts with a non-zero
  exit code on failure

---

**Last Updated:** 2026-06-11
**Maintainer:** LLM Wiki MCP Team
