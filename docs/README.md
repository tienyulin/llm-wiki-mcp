# Documentation Index

Welcome to the LLM Wiki MCP documentation. This directory contains all project documentation organized by category.

## 📋 Quick Navigation

### 🚀 Getting Started
- **[End-to-End Example](guides/end-to-end-example.md)** — Follow two real markdown files through the entire pipeline: what each step produces, what MinIO/Postgres store, and what each query endpoint returns. **Start here if you're new.**
- **[SOP → Wiki Pipeline](guides/sop-to-wiki-pipeline.md)** — The full chain: SOP → spec → API + README → simulated CI push → wiki → query, with real output.
- **[Local Setup Guide](guides/local-setup.md)** — How to set up the project locally, start services, run tests
- **[Quick Start](../README.md#快速開始)** — Quick start in main README

### 🏗️ Architecture & Design
- **[Service Layering](architecture/service-layering.md)** — Three-layer architecture (api/service/repository), dependency injection, test patterns
- **[LLM Provider Abstraction](architecture/llm-provider-abstraction.md)** — Design and implementation of 7-provider abstraction layer
- **[Concurrency Model](architecture/concurrency.md)** — Multi-replica safe two-phase CAS write pipeline
- **[Vector Search](architecture/vector-search.md)** — PG+pgvector index design, measured evaluation, failure semantics (with diagrams)
- **[API Schema](api/schema.md)** — Complete API endpoint documentation

### 👨‍💻 Development
- **[Development Guide](guides/development.md)** — Code structure, how to extend, development workflow
- **[SOP → Spec → Service](../specs/oracle-flashback-recovery-api.spec.md)** — Document-driven flow: SOP (`../sop/`) → spec via `.claude/skills/sop-to-spec` → `flashback-api/` implementation
- **[GitLab Integration](guides/gitlab-setup.md)** — CI/CD configuration and GitLab integration steps

### 🔧 Troubleshooting & Monitoring
- **[Troubleshooting Guide](troubleshooting.md)** — Common issues and solutions
- **[Test Results](test-results.md)** — Latest test run results and performance metrics

---

## 📁 Directory Structure

```
docs/
├── README.md                              # This file
├── guides/
│   ├── end-to-end-example.md             # Worked example through the whole pipeline
│   ├── local-setup.md                    # Local environment setup
│   ├── development.md                    # Development guidelines
│   └── gitlab-setup.md                   # GitLab CI/CD configuration
├── architecture/
│   ├── llm-provider-abstraction.md       # Provider abstraction design
│   ├── concurrency.md                    # Multi-replica CAS write design
│   └── vector-search.md                  # PG+pgvector design + evaluation
├── api/
│   └── schema.md                         # API endpoint reference
├── troubleshooting.md                    # Troubleshooting & FAQ
└── test-results.md                       # Test execution results
```

---

## 🧪 Tests

Test files are organized in the `tests/` directory:

```
tests/
├── unit/                                 # Unit tests (in package directories)
├── integration/                          # Integration tests
│   ├── test_docker_integration.py
│   └── test_processor.py
└── stress/                               # Performance & stress tests
    ├── test_100_apps_performance.py
    ├── test_poc_standalone.py
    └── test_poc_100_apps.py
```

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/integration/
pytest tests/stress/

# With coverage
pytest --cov=wiki_processor --cov=mcp_server
```

---

## 📖 Document Purpose

| File | Purpose | Audience |
|------|---------|----------|
| local-setup.md | Step-by-step environment setup | Developers |
| development.md | Code structure and extension guide | Contributors |
| gitlab-setup.md | CI/CD pipeline configuration | DevOps / Developers |
| llm-provider-abstraction.md | Design decisions for provider pattern | Architects |
| schema.md | API endpoint reference | Backend developers |
| troubleshooting.md | Common issues and fixes | Everyone |
| test-results.md | Performance benchmarks | QA / Ops |

---

## 🔄 Work in Progress

This documentation is continuously updated. If you find outdated information or have suggestions for improvement, please:
1. Open an issue describing the problem
2. Create a PR with improvements following the [development guide](guides/development.md)

---

## 📝 Latest Updates

- **2026-05-11** — Reorganized documentation structure for clarity
- **2026-05-10** — Phase 8 complete: 7-provider LLM abstraction
- **2026-05-09** — Multi-provider configuration documentation added
