# Phase 8: LLM Provider Abstraction Refactoring

**Branch:** `feat/llm-provider-abstraction`

**Status:** Planning & Documentation Complete ✅ → Ready for Implementation

---

## Overview

This branch contains the complete plan and detailed implementation guide for refactoring the hardcoded Minimax API configuration to support **multiple LLM providers** in a flexible, pluggable architecture.

### What Problem Does This Solve?

Currently, the wiki-processor has:
- ❌ Hardcoded Minimax API configuration in `services/llm.py`
- ❌ No way to switch to other AI APIs without code changes
- ❌ Environment variables tied to Minimax (`MINIMAX_API_KEY`)

This refactoring will:
- ✅ Support **7 different LLM providers** with a unified interface
- ✅ Allow provider selection via simple environment variables
- ✅ Maintain 100% backward compatibility
- ✅ Enable self-hosted LLM services (Ollama, vLLM, LM Studio, etc.)

---

## Supported Providers

After implementation, you'll be able to use:

1. **OpenAI** - GPT-4, GPT-3.5, etc.
2. **Anthropic Claude** - Claude 3 family
3. **Google Gemini** - Latest Gemini models
4. **Groq** - Ultra-fast inference
5. **Azure OpenAI** - Enterprise deployment
6. **OpenAI-Compatible** - Any service with OpenAI API format
   - Ollama (run local models)
   - vLLM (self-hosted inference server)
   - LM Studio (local development)
   - Text Generation WebUI
   - Custom internal LLM services
7. **Minimax** - Current provider (default for backward compatibility)

---

## Key Design Decisions

### Provider Pattern

Uses the classic **Provider Pattern** with:
- **Abstract Base Class** (`LLMProvider`) - common interface for all providers
- **Provider Implementations** - specific adapters for each API
- **Factory** - creates appropriate provider based on configuration
- **Config Manager** - loads and validates settings from environment

### Standardized Error Handling

All providers raise consistent exception types:
- `AuthenticationException` - invalid API key
- `RateLimitException` - rate limit exceeded
- `APIException` - API errors
- `ValidationException` - response format errors
- `ConfigurationException` - configuration issues

### Configuration Via Environment Variables

Instead of hardcoded values, use environment variables:

```env
LLM_PROVIDER=openai          # Which provider to use
LLM_API_KEY=sk-...           # API key/token
LLM_MODEL=gpt-4-turbo        # Model name
LLM_TEMPERATURE=0.7          # Generation temperature
LLM_MAX_TOKENS=4000          # Max response length
LLM_BASE_URL=http://...      # (Optional) For self-hosted services
```

### Backward Compatibility

Default values ensure existing setups continue working:
- Default provider: **minimax**
- Default model: **MiniMax-M2.7**
- No changes to `processor.py` logic
- No changes to wiki generation behavior

---

## File Structure (After Implementation)

```
wiki-processor/
├── services/
│   ├── llm/                          (NEW DIRECTORY)
│   │   ├── __init__.py               (Exports public API)
│   │   ├── base.py                   (Abstract LLMProvider class)
│   │   ├── config.py                 (Configuration & LLMConfig dataclass)
│   │   ├── exceptions.py             (Custom exception types)
│   │   ├── factory.py                (LLMProviderFactory)
│   │   └── providers/                (NEW DIRECTORY)
│   │       ├── __init__.py           (Imports to register providers)
│   │       ├── minimax.py            (Migrated from old services/llm.py)
│   │       └── openai_compatible.py  (Self-hosted LLM support)
│   ├── processor.py                  (MODIFY: Type hints only)
│   └── (old llm.py deleted)
├── api/
│   └── routes.py                     (MODIFY: Use factory instead of MinimaxClient)
├── docker-compose.yml                (MODIFY: New environment variables)
├── .env-example                      (MODIFY: Add all provider configs)
└── LLM_PROVIDER_ABSTRACTION_IMPLEMENTATION_GUIDE.md (THIS GUIDE)
```

---

## Configuration Examples

### Using OpenAI

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-...
LLM_MODEL=gpt-4-turbo
LLM_TEMPERATURE=0.7
```

### Using Anthropic Claude

```env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-opus-4-7
```

### Using Google Gemini

```env
LLM_PROVIDER=gemini
LLM_API_KEY=AIzaSy...
LLM_MODEL=gemini-2.0-flash
```

### Using Ollama (Local)

```env
LLM_PROVIDER=openai-compatible
LLM_API_KEY=not-needed
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama2
```

### Using vLLM (Self-hosted)

```env
LLM_PROVIDER=openai-compatible
LLM_API_KEY=your-token
LLM_BASE_URL=http://llm-server:8000/v1
LLM_MODEL=mistral-7b
```

### Using Minimax (Default/Current)

```env
LLM_PROVIDER=minimax
LLM_API_KEY=sk-cp-...
LLM_MODEL=MiniMax-M2.7
```

---

## Implementation Phases

The detailed guide (`LLM_PROVIDER_ABSTRACTION_IMPLEMENTATION_GUIDE.md`) breaks down the work into 8 phases:

### Phase 1: Base Classes & Setup
- Create directory structure
- Implement exception classes
- Implement `LLMConfig` configuration dataclass
- Implement abstract `LLMProvider` base class

### Phase 2: Factory & Configuration
- Implement `LLMProviderFactory` for provider instantiation
- Implement configuration loading from environment

### Phase 3: Provider Implementations
- **Minimax** provider (migrate existing code)
- **OpenAI-compatible** provider (supports self-hosted)
- (Optional: OpenAI, Anthropic, Google, Groq, Azure in future)

### Phase 4: Integration
- Update `api/routes.py` to use factory
- Update type hints in `processor.py`
- Delete old `services/llm.py`

### Phase 5: Configuration
- Update `docker-compose.yml`
- Update `.env-example`
- Document all provider options

### Phase 6: Testing
- Unit tests for config, factory, each provider
- Integration tests for provider switching
- Backward compatibility verification

### Phase 7: Additional Providers (Future)
- OpenAI provider
- Anthropic provider
- Google Gemini provider
- Groq provider
- Azure OpenAI provider

### Phase 8: Verification
- Run full test suite
- Update documentation
- Create migration guide

---

## Key Files to Understand

1. **`LLM_PROVIDER_ABSTRACTION_IMPLEMENTATION_GUIDE.md`**
   - Complete step-by-step implementation guide
   - Code templates and examples
   - Testing strategy
   - Troubleshooting guide

2. **`/root/.claude/plans/document-sorted-castle.md`**
   - High-level architectural plan
   - Comparison table of API providers
   - Design trade-offs and rationale
   - Performance considerations

---

## How to Implement This

### Option A: Manual Implementation
Follow the detailed guide in `LLM_PROVIDER_ABSTRACTION_IMPLEMENTATION_GUIDE.md` step by step.

### Option B: AI-Assisted Implementation
Provide this document and guide to another Claude instance to implement automatically:

```
"Please implement the LLM provider abstraction based on:
1. /root/.claude/plans/document-sorted-castle.md (Phase 8 section)
2. LLM_PROVIDER_ABSTRACTION_IMPLEMENTATION_GUIDE.md

The guide contains all necessary code templates and step-by-step instructions."
```

---

## Testing After Implementation

### Quick Verification

```bash
# 1. Verify structure
ls -la wiki-processor/services/llm/
# Should see: __init__.py, base.py, config.py, exceptions.py, factory.py, providers/

# 2. Run unit tests
pytest tests/unit/test_llm_config.py -v
pytest tests/unit/test_llm_factory.py -v

# 3. Start services with new provider
docker compose up -d
docker compose logs wiki-processor | grep "Initialized LLM"

# 4. Verify old tests still pass
pytest tests/ -v
```

### Provider Switching

```bash
# Change provider in .env or docker-compose.yml

# Test with OpenAI
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-...

# Test with Ollama
export LLM_PROVIDER=openai-compatible
export LLM_BASE_URL=http://localhost:11434/v1

# Services should work with any provider without code changes
```

---

## Backward Compatibility Guarantee

This refactoring maintains 100% backward compatibility:

✅ Default provider is Minimax (same as before)
✅ Default model is MiniMax-M2.7 (same as before)
✅ No changes to `processor.py` logic
✅ No changes to wiki generation behavior
✅ Environment variable `LLM_API_KEY` replaces `MINIMAX_API_KEY`
✅ All existing tests should pass without modification
✅ MOCK_LLM behavior unchanged

---

## What Happens Next?

### Immediate (This Branch)
- ✅ Complete evaluation of AI API formats
- ✅ Design Provider Pattern architecture
- ✅ Create detailed implementation guide
- ✅ Document all supported providers
- ✅ Prepare for implementation

### Implementation Phase
1. Another AI implements based on guide
2. Unit tests verify each provider
3. Integration tests verify switching works
4. Backward compatibility tests
5. Full test suite passes

### Post-Implementation
1. Merge to main
2. Update documentation
3. Deploy new version
4. Users can now switch providers easily

---

## Questions?

### "How long will implementation take?"
Estimated: **8-12 hours** for a developer following the detailed guide, or instant if delegated to Claude with this documentation.

### "Will this affect current users?"
No. Default behavior is identical. Users can optionally switch providers by setting one environment variable.

### "Can I still use Minimax?"
Yes, that's the default. Just keep using `LLM_API_KEY` instead of `MINIMAX_API_KEY`.

### "What if I need a provider not listed?"
The architecture is extensible. Any new provider just needs to:
1. Extend `LLMProvider` base class
2. Implement 3 methods: `generate()`, `validate_config()`, `get_model_info()`
3. Register via `LLMProviderFactory.register()`

### "Will this work with Docker?"
Yes, all configuration is via environment variables which docker-compose supports.

---

## Success Criteria ✓

- [ ] Code compiles and imports correctly
- [ ] All existing tests pass (backward compatibility)
- [ ] New unit tests for factory and config
- [ ] Provider-specific unit tests
- [ ] Integration tests for provider switching
- [ ] docker-compose works with new variables
- [ ] Documentation updated
- [ ] No breaking changes to processor API

---

## Related Documents

- **Evaluation Details:** `/root/.claude/plans/document-sorted-castle.md` (Phase 8)
- **Implementation Guide:** `LLM_PROVIDER_ABSTRACTION_IMPLEMENTATION_GUIDE.md`
- **Current API Integration:** `wiki-processor/services/llm.py` (to be refactored)

---

**Branch Status:** Ready for Implementation ✅

Created: May 10, 2026
Phase: 8 of Wiki MCP System Development
