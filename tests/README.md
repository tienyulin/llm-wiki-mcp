# Test Suite

This directory contains all tests for the LLM Wiki MCP project, organized by category.

## 📁 Structure

```
tests/
├── unit/                    # Unit tests (mostly in package directories)
├── integration/             # Integration tests
└── stress/                  # Performance & stress tests
```

## 🧪 Test Categories

### Unit Tests
**Location:** Primarily within service packages (`wiki-processor/tests/`, `mcp-server/tests/`)

Unit tests verify individual components in isolation:
- `wiki-processor/tests/test_llm.py` — LLM provider abstraction
- `wiki-processor/tests/test_routes.py` — API endpoint handlers
- `wiki-processor/tests/test_processor.py` — Wiki processing logic
- `mcp-server/tests/test_wiki_service.py` — Wiki service methods

**Run unit tests:**
```bash
pytest wiki-processor/tests/ mcp-server/tests/
```

### Integration Tests
**Location:** `tests/integration/`

Integration tests verify components working together:
- `test_docker_integration.py` — Docker Compose services interaction
- `test_processor.py` — Full wiki-processor pipeline

**Run integration tests:**
```bash
pytest tests/integration/
```

### Stress Tests
**Location:** `tests/stress/`

Stress and performance tests verify behavior under load:
- `test_100_apps_performance.py` — Performance with 100 concurrent applications
- `test_poc_standalone.py` — Standalone POC functionality
- `test_poc_100_apps.py` — 100-app integration POC

**Run stress tests:**
```bash
pytest tests/stress/
```

Note: Stress tests may be slow and resource-intensive. Set `MOCK_LLM=true` for faster execution.

## 🚀 Running Tests

### All Tests
```bash
pytest
```

### With Coverage
```bash
pytest --cov=wiki_processor --cov=mcp_server --cov-report=html
```

### Specific Category
```bash
pytest tests/integration/       # Integration only
pytest wiki-processor/tests/    # Unit tests for wiki-processor
pytest tests/stress/            # All stress tests
```

### With Mock LLM (Faster)
```bash
export MOCK_LLM=true
pytest tests/stress/
```

### Verbose Output
```bash
pytest -v
```

## 📊 Test Configuration

Tests use the following environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MOCK_LLM` | false | Use mock LLM responses (skip API calls) |
| `LLM_PROVIDER` | minimax | LLM provider for tests |
| `MINIMAX_API_KEY` | (unset) | For testing with real Minimax API |

## ✅ Expected Results

| Test Suite | Expected Status | Duration |
|-----------|-----------------|----------|
| Unit tests | All passing | ~5-10s |
| Integration tests | All passing | ~30-60s |
| Stress tests | All passing | ~1-5min (with MOCK_LLM=true) |

## 🔍 Test Coverage

Target coverage: **>80%** for core modules

Current coverage areas:
- ✅ LLM provider abstraction
- ✅ Wiki processing logic
- ✅ MCP API endpoints
- ✅ Configuration loading
- ✅ Application isolation (100-app scenario)

## 🐛 Debugging Tests

### Enable Detailed Logging
```bash
pytest -v --log-cli-level=DEBUG
```

### Run Single Test
```bash
pytest tests/integration/test_docker_integration.py::test_process_endpoint
```

### Debug with pdb
```bash
pytest --pdb tests/integration/test_processor.py
```

## 📝 Writing New Tests

### Directory Structure
- **Unit tests:** Place in the package's `tests/` directory
- **Integration tests:** Place in `tests/integration/`
- **Stress tests:** Place in `tests/stress/`

### Example Test Structure
```python
import pytest
from wiki_processor.services.processor import WikiProcessor

class TestWikiProcessing:
    @pytest.fixture
    def processor(self):
        return WikiProcessor()
    
    def test_basic_processing(self, processor):
        result = processor.process({"test.md": "# Test"})
        assert result["status"] == "success"
```

## 🚦 CI/CD Integration

Tests run automatically on:
- **Pull requests** — All tests must pass before merge
- **Main branch pushes** — Full test suite runs
- **Scheduled** — Nightly stress tests

See `.gitlab-ci.yml` for CI/CD configuration.

---

**Last Updated:** 2026-05-11  
**Maintainer:** LLM Wiki MCP Team
