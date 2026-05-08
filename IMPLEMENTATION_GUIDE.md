# Wiki Processor Implementation Guide

## Architecture Overview

The LLM Wiki system follows a **push-based, incremental update** architecture:

```
┌─────────────────────────────────┐
│   Central Markdown Repo         │
│   (all API documentation)       │
│                                 │
│  markdowns/                     │
│  ├── api-users.md              │
│  ├── api-orders.md             │
│  └── api-products.md           │
└────────────┬────────────────────┘
             │
             │ CI: Collect all markdown files
             │      → Send via HTTP POST
             ▼
┌─────────────────────────────────┐
│   Wiki Processor (FastAPI)      │
│   http://localhost:8001         │
│                                 │
│   POST /process                 │
│   ├── Compare with old snapshot │
│   ├── Detect changes (add/mod)  │
│   ├── Call Minimax LLM          │
│   │   • First run: Generate wiki│
│   │   • Incremental: Merge delta│
│   └── Save to Minio             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   Minio Object Storage          │
│   http://localhost:9001         │
│                                 │
│   wiki-data bucket:             │
│   ├── wiki.json (main output)   │
│   └── markdowns_snapshot.json   │
│       (for change detection)    │
└─────────────────────────────────┘
```

## Key Design Decisions

### 1. **Push Model (CI → Processor)**
- ✅ CI directly sends markdown content to processor
- ✅ No git cloning needed in processor
- ✅ Single HTTP request per update
- ✅ Clear separation of concerns

### 2. **Incremental Updates (Karpathy Style)**
Instead of regenerating the entire wiki on every change:

**First Run:**
```
All markdowns → LLM → "Analyze and generate complete wiki" → wiki.json
```

**Subsequent Updates:**
```
Current wiki (context)
      +
Changed markdowns (new input)
      ↓
LLM → "Merge changes into existing wiki" → Updated wiki.json
```

**Benefits:**
- 🚀 Token cost grows linearly with changes, not total content
- 🧠 LLM understands semantic relationships between old and new APIs
- 💾 Maintains wiki structure consistency

### 3. **Change Detection via Snapshot**
- Before processing: Compare current markdowns with `markdowns_snapshot.json`
- Categories: Added, Modified, Deleted files
- Only changed files sent to LLM in incremental updates

## Setup & Deployment

### Prerequisites
- Docker & Docker Compose
- Minimax API Key (for LLM calls)
- Central markdown repository with CI/CD enabled

### Step 1: Start Infrastructure

```bash
# Set your Minimax API key
export MINIMAX_API_KEY="your-key-here"

# Start Minio + Wiki Processor
docker-compose up -d
```

Services:
- **Minio**: http://localhost:9001 (admin:minioadmin)
- **Wiki Processor**: http://localhost:8001

### Step 2: Initialize Minio

```bash
# Create wiki-data bucket (processor auto-creates, but manual is safer)
docker exec wiki-minio mc mb minio/wiki-data
```

### Step 3: Configure Central Markdown Repo

In your central markdown repository (contains all API docs):

**1. Create directory structure:**
```
central-markdown-repo/
├── markdowns/
│   ├── api-users.md
│   ├── api-orders.md
│   └── api-products.md
├── .gitlab-ci.yml (or equivalent)
└── README.md
```

**2. Add `.gitlab-ci.yml` (see examples/ci-gitlab-central-repo.yml):**
```yaml
process-wiki:
  stage: deploy
  image: python:3.11-slim
  script:
    # Collect markdowns and send to processor
    - python3 collect_and_send.py
  only:
    - main
  rules:
    - changes:
        - markdowns/**/*.md
```

**3. Python helper script (collect_and_send.py):**
```python
import json
import glob
from datetime import datetime, timezone
import httpx

# Collect markdowns
markdowns = {}
for f in sorted(glob.glob("markdowns/**/*.md", recursive=True)):
    with open(f) as file:
        markdowns[f] = file.read()

# Send to processor
payload = {
    "markdowns": markdowns,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "trigger_info": {
        "repo": "central-markdown-repo",
        "branch": "main"
    }
}

response = httpx.post(
    "http://wiki-processor:8001/process",
    json=payload,
    timeout=60.0
)
response.raise_for_status()
print("Wiki updated successfully!")
print(response.json())
```

### Step 4: Test the Flow

**Manual test without CI:**
```bash
# Test with sample markdowns
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{
    "markdowns": {
      "api-users.md": "## GET /users/{id}\nGet user by ID",
      "api-orders.md": "## POST /orders\nCreate new order"
    },
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "trigger_info": {"repo": "test", "branch": "main"}
  }'
```

**Expected response:**
```json
{
  "status": "success",
  "message": "Wiki generated successfully",
  "wiki_url": "minio://wiki-data/wiki.json",
  "changes_summary": {
    "added": ["api-users.md", "api-orders.md"],
    "modified": [],
    "deleted": []
  },
  "timestamp": "2026-05-08T10:00:00Z"
}
```

**Verify outputs in Minio:**
```bash
# Access Minio console
http://localhost:9001
# Login: minioadmin / minioadmin
# Navigate to: wiki-data bucket
# View: wiki.json and markdowns_snapshot.json
```

## API Reference

### POST /process

**Request:**
```json
{
  "markdowns": {
    "path/to/file1.md": "markdown content...",
    "path/to/file2.md": "markdown content..."
  },
  "timestamp": "2026-05-08T10:00:00Z",
  "trigger_info": {
    "repo": "repo-name",
    "branch": "main",
    "commit_sha": "...",
    "pipeline_url": "..."
  }
}
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Wiki generated/updated successfully",
  "wiki_url": "minio://wiki-data/wiki.json",
  "changes_summary": {
    "added": [...],
    "modified": [...],
    "deleted": [...]
  },
  "timestamp": "2026-05-08T10:00:01Z"
}
```

### GET /status

Returns current wiki statistics:
```json
{
  "status": "running",
  "wiki_size": 42,
  "tracked_files": 5,
  "last_updated": "2026-05-08T10:00:01Z"
}
```

### GET /health

Health check:
```json
{
  "status": "ok",
  "minio_connected": true,
  "minimax_accessible": true
}
```

## Monitoring & Debugging

### View Processor Logs
```bash
docker logs -f wiki-processor
```

### Check Minio Contents
```bash
# Access console
firefox http://localhost:9001

# Or via CLI
docker exec wiki-minio mc ls minio/wiki-data
docker exec wiki-minio mc cat minio/wiki-data/wiki.json
```

### Common Issues

**1. "Minio connection failed"**
```bash
# Check Minio health
curl http://localhost:9000/minio/health/live
```

**2. "No markdown files found"**
- Ensure CI is looking for files in correct path
- Check glob pattern matches your directory structure

**3. "LLM API error"**
- Verify `MINIMAX_API_KEY` is set
- Check Minimax API status
- Review prompt size (may exceed limits)

## Performance Characteristics

### Token Usage (Incremental Model)
- **First run**: ~500-2000 tokens (full wiki)
- **Per update**: ~100-500 tokens (changes only)
- **Scaling**: Linear with content changes, not total docs

### Latency
- **Markdown collection**: <1s
- **HTTP POST**: <2s
- **LLM processing**: 10-30s (depends on changes)
- **Minio write**: <1s
- **Total**: ~15-35s per update

### Storage
- **wiki.json**: 10-100KB (typical)
- **markdowns_snapshot.json**: 10-100KB
- Scales with number of APIs (one entry per endpoint)

## Prompt Caching (Future Optimization)

The incremental update model is designed to leverage LLM prompt caching:

```python
# Current wiki as system message (cached)
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Current wiki:", "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": json.dumps(current_wiki)},
        ]
    },
    # Only changed markdowns in actual request (not cached)
    {
        "role": "user",
        "content": "Merge these changes: ..."
    }
]
```

This reduces token costs for repeated wiki updates from ~1000 to ~50-100.

## Next Steps

1. **Deploy in your environment**
   - Update docker-compose.yml with your settings
   - Configure CI in central markdown repo
   - Test end-to-end flow

2. **Integrate into your workflow**
   - Add wiki.json as documentation source
   - Create frontend to visualize wiki
   - Set up automated alerts on update failures

3. **Optimize**
   - Enable prompt caching once API supports it
   - Monitor token usage and adjust LLM prompts
   - Consider batch processing for multiple repos

## References

- [Minimax API Docs](https://platform.minimaxi.com)
- [Minio Documentation](https://docs.min.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- Karpathy LLM Paper (incremental learning approach)
