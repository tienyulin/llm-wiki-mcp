# Scale stress test + write-bottleneck fix — resume plan

Paused near a Claude session limit. This captures state + next steps so we resume fast.

## Goal
1. Real-LLM scale stress test (no mocks) to see true generate/query behavior.
2. Chart the write bottleneck, then fix it for "huge company" scale.

## Current stack state (already configured)
- **Real Minimax M3** LLM + **local embedding model** (fastembed bge-small, 384-dim).
- `.env` written (gitignored) in both repos:
  - `llm-wiki-processor/.env`: `LLM_PROVIDER=minimax`, `LLM_API_KEY=<set>`, `LLM_MODEL=MiniMax-M3`, `MOCK_LLM=false`, `EMBEDDING_BASE_URL=http://embed-srv:8088`, `EMBEDDING_DIM=384`, `MOCK_EMBEDDINGS=false`, `PG_DSN=...@pg:5432/wiki`.
  - `llm-mcp-server/.env`: embeddings + PG (no LLM key).
- `embed-srv` container (bge-small) runs on docker network `llm-wiki-net` (port 8088). Restart if gone:
  `docker run -d --name embed-srv --network llm-wiki-net -v /tmp/embed-srv:/srv -w /srv -p 8088:8088 python:3.14-slim sh -c "pip install -q fastembed fastapi 'uvicorn[standard]'; python app.py"` (script at `/tmp/embed-srv/app.py`).
- DB currently holds 1 app (payments-api) from a smoke test. **Wipe before the real run.**
- Resume: `cd llm-wiki-infra && docker compose up -d` → ensure embed-srv on net → `up -d` processor + mcp.

## ⚠️ Security
The Minimax key was pasted into chat — **rotate it** after this work. It lives only in the gitignored `.env`.

## Smoke result (verified)
One real M3 push = **18.7s** (two-step extract). Descriptions are now endpoint-specific ("Refund a previous charge to the customer"), not the generic title the mock produced. → 18s/push means concurrency + patience needed.

## Findings so far (from the 100-app MOCK run)
- Reads scale great: query p50 **4–10ms**, p95 ≤14ms; concurrent **260 q/s** @32 parallel (p95 177ms).
- reindex 1000 endpoints **1.07s**; rebuild-concepts **94ms**.
- **Write bottleneck**: per-push latency rose first-10 **596ms** → last-10 **795ms** (+33%) at 100 apps. Cause: every `/process` re-reads + rewrites the *whole* growing `wiki.json` blob under CAS → O(N) per write, O(N²) total.

## Next steps (do in order)
1. **Real-LLM full run** — wipe DB; ingest 100 apps × 10 endpoints + 200 knowledge docs via real M3 + local embeddings.
   - Concurrency ~6–8 (watch Minimax rate limits; ~18s/call → expect 30–60+ min).
   - Measure: ingest latency/throughput, **rate-limit/failure count**, real generate time/push, embedding latency, extraction quality.
   - Scripts ready: `/tmp/scale.py` (full battery), `/tmp/curve.py` (write curve).
2. **Write-curve (mock)** to 500–1000 apps — bucket per-push latency by N to chart the O(N) blob cost precisely.
3. **Query latency + concurrent load** at 1000+ endpoints (semantic/hybrid/keyword/knowledge) p50/p95.
4. **Fix the write bottleneck** (the headline robustness item; PR, no-merge):
   - Design: stop storing all apps in one `wiki.json`. Store **per-app objects** (e.g. `apps/<app>.json`) as source of truth; a push rewrites only its own object (flat O(1) write, no cross-app CAS contention).
   - Keep an aggregate/index for whole-wiki reads (or have mcp read PG, which is already per-row). Concepts/overviews stay aggregate, rebuilt on demand.
   - Re-run the write-curve to prove flat latency.

## Acceptance
- Write latency stays ~flat as apps grow (no +33%/N climb).
- Reads + cross-domain reasoning unchanged (71/56 suites green, live Claude check).

---

# RESULTS — real-LLM run (Minimax M3 + local bge-small), 2026-06-20

Ingested with REAL M3 + REAL embeddings. Landed: **35 apps / 280 endpoints + 60 knowledge docs**.

## What's GOOD
- **Query quality (real embeddings) is excellent**: "refund a payment"→billing, "log a user in"→users, "ship an order"→orders, "billing consistent across replicas"→billing KB docs. All correct.
- **Single-query latency fine at scale**: search_apis/semantic/knowledge p50 **27–31ms**, p95 ≤40ms; list_apis 3ms. reindex 280 entries **5.9s**.
- **Extraction quality**: M3 gives per-endpoint descriptions ("Refund a previous charge to the customer").

## PROBLEMS FOUND (prioritized)

### P1 — LLM rate-limit, no backoff/retry  (ingest robustness)
Concurrency 8 against real M3 → **apps 35/100 ok (65 fail), knowledge 60/200 ok (140 fail)**. Pattern: bursts succeed, then walls of ~1.2s 429 fast-fails. Processor returns status=failed gracefully but never retries.
**Fix:** catch `RateLimitException` in the LLM `generate()` path → exponential backoff + retry (a few attempts, jitter). Optionally a small client-side concurrency cap / token-bucket. Highest value; small change.

### P2 — rebuild-concepts times out at scale  (real bug)
`POST /admin/rebuild-concepts` → **HTTP 500 (httpx.ReadTimeout)**. Cause: real-LLM `generate_concepts` puts the WHOLE wiki catalogue (280 endpoints) into ONE prompt → times out; worse at 1000.
**Fix:** don't send the whole wiki to the LLM. The deterministic token+semantic clustering (mock path, already O(n) and good) should be the default for concept building; drop/limit the single giant LLM call (or chunk per-app). Lazy + more scalable.

### P3 — write bottleneck (single wiki.json blob)  [from mock 100-app run]
Per-push latency +33% (596→795ms) at 100 apps; O(N) rewrite per push, O(N²) total.
**Fix:** per-app objects (`apps/<app>.json`) so a push rewrites only its own object.

### P4 — query embedding in the hot path caps concurrent throughput
Concurrent 200@32: mock **260 q/s** vs real **57 q/s** (p95 753ms). Each hybrid/semantic query makes a synchronous embed call; the single local embedder serializes under load.
**Fix:** cache query embeddings (LRU on query text); and/or batch; in prod use a scaled embedding service. Cheap win: `functools.lru_cache`-style cache on `aembed_query`.

## Suggested fix order
P1 (rate-limit backoff) → P2 (concept build off the giant LLM call) → P4 (query-embed cache) → P3 (blob sharding, biggest).
All as separate PRs, no-merge, with before/after evidence.

---

# FIX RESULTS (2026-06-20)

| # | fix | PR | before → after (live, real LLM+embeddings) |
|---|---|---|---|
| **P1** | LLM rate-limit backoff + concurrency cap | llm-wiki-processor #10 | ingest failures **65% → 0%** (30 apps @ concurrency 8) |
| **P2** | deterministic concept build (drop whole-wiki LLM call) | llm-wiki-processor #11 (stacked on #10) | rebuild-concepts **HTTP 500 timeout → 200 in 0.20s** |
| **P4** | LRU-cache query embeddings | llm-mcp-server #10 | concurrent throughput **57 → 221 q/s** (repeated queries) |
| **P3** | per-app objects (kill blob O(N²)) | — design below, dedicated pass | not yet built |

## P3 design (do as its own focused change — touches ~11 files + tests)

**Problem:** every `/process` rewrites the whole `wiki.json`; O(N) per push, O(N²) total. +33% latency at 100 apps (mock).

**Plan:** stop putting all apps in one object.
- **Source of truth → per-app objects** `apps/<app>.json` = that app's `{apis, knowledge, overview}`. A push reads+writes only its own object (small, O(1)) under CAS on that key → no global write-lock, no cross-app contention.
- **Aggregate is derived, not on the hot path.** `concepts.json` (+ optional merged view) rebuilt on demand by `rebuild_concepts` reading `apps/*.json` (or straight from PG). Already an admin op.
- **mcp reads unchanged** — PG-first (already per-row, scales). Fallback path reads per-app objects / `concepts.json` instead of one `wiki.json`.
- **Migration:** lazy — on first per-app write, split an existing `wiki.json` into `apps/*.json`; keep reading old `wiki.json` until split. Or a one-shot `/admin/migrate-split`.

**Files:** processor `processor.py`(merge/CAS/process), `vector_sync.py`(reindex reads), `admin.py`, `system_service.py`; mcp `minio_client.py`(reader), `wiki_service.py`, `query_service.py`, `pg_reader.py` fallback, `core/cache.py`.

**Acceptance:** write-curve flat as apps grow (re-run `/tmp/curve.py`); 78/59 suites green; live Claude cross-domain check unchanged.

## ⚠️ Still TODO
- Rotate the Minimax API key (pasted in chat).
- Merge P1/P2/P4 (stacked: merge #10 then #11 in processor; #10 in mcp), then bump platform submodules.
