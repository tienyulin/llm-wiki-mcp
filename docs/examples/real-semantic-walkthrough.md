# Real walkthrough: one request, every layer, with real data

This is a **real, captured run** — not a mock and not a summary. It follows one
piece of data from a pushed README all the way to a semantic query answer, and
shows the **actual values at every layer** plus the **exact command that produced
each value**, so you can re-run and verify each number yourself.

- **LLM (extraction):** real MiniMax-M3 (`api.minimax.io`)
- **Embeddings:** real Google Gemini `gemini-embedding-001` (OpenAI-compatible endpoint), 1536-dim
- **Storage:** real MinIO + real Postgres/pgvector (the default `docker compose` stack)

Captured 2026-06-14. Keys are redacted; the run used a gitignored `.env`.

---

## 0. Setup

`.env` (real keys redacted):
```env
MOCK_LLM=false
LLM_PROVIDER=minimax
LLM_API_KEY=sk-cp-…redacted…
LLM_MODEL=MiniMax-M3
MOCK_EMBEDDINGS=false
EMBEDDING_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
EMBEDDING_API_KEY=AIza…redacted…
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIM=1536
EMBEDDING_SEND_DIMENSIONS=true      # gemini-embedding-001 defaults to 3072 (> pgvector's 2000 index cap); request 1536
PG_DSN=postgresql://wiki:wikipass@pg:5432/wiki
```

```bash
docker compose up -d --build
curl -s localhost:8001/health
```
Real output:
```json
{"status":"ok","minio_connected":true,"llm_configured":true,"llm_provider":"minimax",
 "vector_index_connected":true,"embeddings_configured":true,"minimax_accessible":true}
```

---

## 1. Input — what we push

We push three apps. We trace **`billing-api`** all the way through; the other two
(`identity-api`, `warehouse-api`) exist so the semantic query has real competitors.

The billing-api request (`POST localhost:8001/process`):
```json
{
  "markdowns": {
    "billing-api.md": "# Billing API\n\nPOST /billing/charge - Charge a saved credit card to collect payment for a completed purchase."
  },
  "timestamp": "2026-06-14T03:00:00",
  "trigger_info": {"source": "walkthrough"},
  "source_app": "billing-api",
  "source_version": "v1"
}
```

---

## 2. Stage 1 — LLM extraction (real MiniMax-M3)

`/process` sends the markdown to MiniMax, which extracts structured API entries.
Real 200 response:
```json
{
  "status": "success",
  "message": "Wiki generated successfully",
  "source_app": "billing-api",
  "files_updated": ["POST /billing/charge"],
  "processing_time_ms": 4562
}
```
> Real LLM output is **non-deterministic** — this is what *this* run produced. The
> three apps took 4562 / 4135 / 4180 ms (real network round-trips to MiniMax).

---

## 3. Stage 2 — MinIO is the source of truth

The extracted entries are merged into a single `wiki.json` object in the
`wiki-data` bucket (concurrent writers use ETag CAS). MinIO is authoritative; PG
is a derived index rebuildable from it.

```bash
docker compose exec -T wiki-processor python -c "
from repository.minio_client import MinioStorage
import json; s=MinioStorage()
print(json.dumps(s.get_json('wiki.json')['apis']['billing'], indent=2, ensure_ascii=False))"
```
Real `wiki.json → apis.billing`:
```json
{
  "POST /billing/charge": {
    "method": "POST",
    "path": "/billing/charge",
    "description": "Charge a saved credit card to collect payment for a completed purchase.",
    "source_app": "billing-api",
    "source_version": "v1"
  }
}
```
Note: the real LLM named the **module `billing`** (dropped `-api`); the app
identity is preserved separately as `source_app: billing-api`.

`wiki.json` shape: `schema_version: 2`, plus `metadata`:
```json
{"version":"1.0","created_at":"2026-06-14T03:54:12.792019","updated_at":"2026-06-14T03:54:25.631571"}
```

Objects in the bucket (`s.list_files('')`):
```
wiki.json                                              # the merged wiki
snapshots/billing-api.json                             # per-app input snapshot (for change detection)
snapshots/identity-api.json
snapshots/warehouse-api.json
audit/2026-06-14T03:54:17.260847-f2139279.json         # one append-only record per push
audit/2026-06-14T03:54:21.469956-4bcc2201.json
audit/2026-06-14T03:54:25.640198-531124d7.json
```
`snapshots/billing-api.json` (the raw input we sent, kept verbatim):
```json
{"billing-api.md": "# Billing API\n\nPOST /billing/charge - Charge a saved credit card to collect payment for a completed purchase."}
```
One audit record:
```json
{"timestamp":"2026-06-14T03:54:17.260847","source_app":"billing-api","files_count":1,
 "status":"success","files_updated":["POST /billing/charge"]}
```

---

## 4. Stage 3 — what actually gets embedded (`embed_text`)

Before embedding, each entry is flattened to one string by
`wiki-processor/services/embeddings/text.py::entry_to_text`:
```
"{module} | {api_key} | {endpoint} | {description} | {params}"   (empty parts dropped)
```
For billing, the real `embed_text` (read from PG below) is:
```
billing | POST /billing/charge | POST /billing/charge | Charge a saved credit card to collect payment for a completed purchase.
```
This exact string — not the raw markdown — is what gets vectorized.

---

## 5. Stage 4 — the embedding API (real Gemini request + response)

The processor sends `embed_text` to Gemini. The real request:
```
POST https://generativelanguage.googleapis.com/v1beta/openai/v1/embeddings
Authorization: Bearer AIza…redacted…
{"model":"gemini-embedding-001","input":["billing | POST /billing/charge | …"],"dimensions":1536}
```
Real response (shape + the actual vector head):
```json
{
  "object": "list",
  "model": "gemini-embedding-001",
  "data": [
    { "object": "embedding",
      "embedding": [-0.008967627, 0.001633695, -0.001927566, -0.077539764,
                     0.006107465,  0.032517925,  0.021139143,  0.001127183, … 1536 floats total] }
  ]
}
```
Reproduce it yourself (paste the embed_text):
```bash
curl -s https://generativelanguage.googleapis.com/v1beta/openai/v1/embeddings \
  -H "Authorization: Bearer $GEMINI_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gemini-embedding-001","input":["billing | POST /billing/charge | POST /billing/charge | Charge a saved credit card to collect payment for a completed purchase."],"dimensions":1536}' \
  | python3 -c 'import sys,json;e=json.load(sys.stdin)["data"][0]["embedding"];print("dim",len(e),"first8",[round(x,9) for x in e[:8]])'
```
→ `dim 1536 first8 [-0.008967627, 0.001633695, -0.001927566, -0.077539764, 0.006107465, 0.032517925, 0.021139143, 0.001127183]`

---

## 6. Stage 5 — the PG row (the index)

That vector + metadata is written to `api_entries`. Real row:
```bash
docker compose exec -T pg psql -U wiki -d wiki -x -c \
  "SELECT module, api_key, source_app, source_version, description, embed_text,
          vector_dims(embedding) AS dim, embedding_model
   FROM api_entries WHERE source_app='billing-api';"
```
```
module          | billing
api_key         | POST /billing/charge
source_app      | billing-api
source_version  | v1
description     | Charge a saved credit card to collect payment for a completed purchase.
embed_text      | billing | POST /billing/charge | POST /billing/charge | Charge a saved credit card to collect payment for a completed purchase.
dim             | 1536
embedding_model | gemini-embedding-001
```
First 8 components of the stored vector:
```bash
docker compose exec -T pg psql -U wiki -d wiki -tA -c \
  "SELECT (string_to_array(trim(both '[]' from embedding::text), ','))[1:8]
   FROM api_entries WHERE source_app='billing-api';"
```
→ `{-0.008967627,0.0016336951,-0.0019275661,-0.077539764,0.0061074654,0.032517925,0.021139143,0.0011271825}`

**✅ Cross-check:** these first 8 numbers match the Gemini API response in Stage 4
exactly. The PG vector *is* the Gemini embedding of `embed_text` — nothing else.

`app_sync` (one row per app, drives provenance / incremental replace):
```
 source_app    | source_version | synced_at
 billing-api   | v1             | 2026-06-14 03:54:12.778821+00
 identity-api  | v1             | 2026-06-14 03:54:17.348813+00
 warehouse-api | v1             | 2026-06-14 03:54:21.49143+00
```

---

## 7. Stage 6 — query through mcp (and *why* it answers what it does)

### The question
A paraphrase that shares **no keywords** with the stored endpoint
(`billing` / `charge` / `credit card` appear nowhere in it):
```
"deduct money from a shopper card"
```

### The mcp answer
```bash
curl -s 'localhost:8002/semantic_search?query=deduct%20money%20from%20a%20shopper%20card&top_k=3'
```
```json
{
  "results": [
    {"module":"billing","api_key":"POST /billing/charge","source_app":"billing-api","score":0.5382, "description":"Charge a saved credit card…"},
    {"module":"warehouse","api_key":"GET /warehouse/stock","source_app":"warehouse-api","score":0.4999, "description":"Look up how many units…"},
    {"module":"identity","api_key":"POST /identity/login","source_app":"identity-api","score":0.4244, "description":"Verify a user password…"}
  ],
  "count": 3,
  "mode": "semantic"
}
```
`POST /billing/charge` ranks #1 — by **meaning**, not keywords.

### How mcp produced that (step by step)
1. mcp embeds the **query string** via the same Gemini endpoint + `dimensions:1536`
   (`mcp-server/services/embeddings.py::QueryEmbedder.aembed_query`). Real query
   vector head:
   ```
   first8 [-0.00538147, 0.017700898, 0.011566551, -0.064901225, -0.024086909, 0.007932861, 0.002413509, 0.016159862]
   ```
2. mcp runs one SQL query — pgvector cosine distance `<=>`, score = `1 - distance`
   (`mcp-server/repository/pg_reader.py::semantic_search`):
   ```sql
   SELECT module, api_key, description, source_app,
          1 - (embedding <=> $query_vec::vector) AS score
   FROM api_entries
   WHERE embedding IS NOT NULL
   ORDER BY embedding <=> $query_vec::vector
   LIMIT 3;
   ```

### Prove it — reproduce mcp's exact scores directly in psql
Embed the query, drop the 1536-float vector literal into the **same** SQL, run it
against PG yourself:
```bash
# 1) get the query vector as a pgvector literal
Q="deduct money from a shopper card"
VEC=$(curl -s "$EMBEDDING_BASE_URL/v1/embeddings" \
  -H "Authorization: Bearer $GEMINI_KEY" -H 'Content-Type: application/json' \
  -d "{\"model\":\"gemini-embedding-001\",\"input\":[\"$Q\"],\"dimensions\":1536}" \
  | python3 -c 'import sys,json;v=json.load(sys.stdin)["data"][0]["embedding"];print("["+",".join(repr(x) for x in v)+"]")')

# 2) run the same cosine ranking mcp runs
docker compose exec -T pg psql -U wiki -d wiki -c \
 "SELECT module, api_key, source_app,
         round((1 - (embedding <=> '$VEC'::vector))::numeric,4) AS score
  FROM api_entries WHERE embedding IS NOT NULL
  ORDER BY embedding <=> '$VEC'::vector LIMIT 3;"
```
Real psql output:
```
  module   |       api_key        |  source_app   | score
-----------+----------------------+---------------+--------
 billing   | POST /billing/charge | billing-api   | 0.5382
 warehouse | GET /warehouse/stock | warehouse-api | 0.4999
 identity  | POST /identity/login | identity-api  | 0.4244
```
**✅ Identical to the mcp `/semantic_search` scores.** mcp is doing exactly this
cosine ranking and nothing more — no hidden re-ranking, no magic.

### Why billing wins
Cosine similarity measures angle between the **query meaning** and each entry's
**`embed_text` meaning**. "deduct money from a shopper card" is closest in
Gemini's vector space to "charge a saved credit card to collect payment"
(0.5382), further from warehouse stock (0.4999) and login (0.4244). The model
understands *charge ≈ deduct money*, *credit card ≈ shopper card* — without a
single shared word. (With mock embeddings, similarity is just token overlap, so
this keyword-free query would not rank billing first — that is the difference
real embeddings buy.)

---

## 8. Reproduce the whole thing

```bash
# bring up real stack (needs MiniMax + Gemini keys in .env, see §0)
docker compose up -d --build
curl -s localhost:8001/health

# push one app
curl -s -X POST localhost:8001/process -H 'Content-Type: application/json' -d '{
 "markdowns":{"billing-api.md":"# Billing API\n\nPOST /billing/charge - Charge a saved credit card to collect payment for a completed purchase."},
 "timestamp":"2026-06-14T03:00:00","trigger_info":{"source":"walkthrough"},
 "source_app":"billing-api","source_version":"v1"}'

# MinIO source of truth
docker compose exec -T wiki-processor python -c "from repository.minio_client import MinioStorage;import json;print(json.dumps(MinioStorage().get_json('wiki.json')['apis'],indent=2))"

# PG row + vector
docker compose exec -T pg psql -U wiki -d wiki -x -c "SELECT module,api_key,source_app,embed_text,vector_dims(embedding) dim,embedding_model FROM api_entries WHERE source_app='billing-api';"

# query + psql reproduction: see §7
```

Every number above is paired with the command that produced it. The two ✅
cross-checks (Gemini vector == PG vector; mcp score == psql cosine) are what make
this verifiable rather than "trust me."
