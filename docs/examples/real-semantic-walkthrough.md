# 真實實跑：一個請求、每一層、真實資料

這是一次**真實擷取的執行** —— 非 mock、非摘要。它跟著一份資料，從推進來的 README 一路
走到語意查詢的答案，並展示**每一層的實際值** + **產生該值的確切指令**，讓你能自己重跑驗證。

> 名詞：**embedding** = 文字轉向量；**cosine** = 向量夾角相似度（1 最像）；**CAS** = ETag 樂觀鎖；
> **source of truth** = 真相來源（其他都是它的衍生）。

- **LLM（抽取）：** 真 MiniMax-M3（`api.minimax.io`）
- **Embeddings：** 真 Google Gemini `gemini-embedding-001`（OpenAI-相容端點），1536 維
- **儲存：** 真 MinIO + 真 Postgres/pgvector（預設 `docker compose` stack）

擷取於 2026-06-14。金鑰已遮罩；該次用 gitignored 的 `.env`。

> 註：此例擷取時 wiki 仍是單一 `wiki.json`（per-app 物件 P3 之前）。流程與每層的值不變；
> P3 後 `apis` 改由每-app 物件 `apps/<app>.json` 匯總而來。

---

## 0. 設定

`.env`（真金鑰遮罩）：
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
EMBEDDING_SEND_DIMENSIONS=true      # gemini-embedding-001 預設 3072（> pgvector 索引上限 2000）；要求 1536
PG_DSN=postgresql://wiki:wikipass@pg:5432/wiki
```

```bash
docker compose up -d --build
curl -s localhost:8001/health
```
真實輸出：
```json
{"status":"ok","minio_connected":true,"llm_configured":true,"llm_provider":"minimax",
 "vector_index_connected":true,"embeddings_configured":true,"minimax_accessible":true}
```

---

## 1. 輸入 —— 我們推什麼

推三個 app。全程追蹤 **`billing-api`**；另兩個（`identity-api`、`warehouse-api`）存在是為了讓
語意查詢有真實的競爭對手。

billing-api 請求（`POST localhost:8001/process`）：
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

## 2. 階段 1 —— LLM 抽取（真 MiniMax-M3）

`/process` 把 markdown 送給 MiniMax，抽出結構化 API 條目。真 200 回應：
```json
{
  "status": "success",
  "message": "Wiki generated successfully",
  "source_app": "billing-api",
  "files_updated": ["POST /billing/charge"],
  "processing_time_ms": 4562
}
```
> 真 LLM 輸出**非確定性** —— 這是*這次*跑出來的。三個 app 各花 4562 / 4135 / 4180 ms
> （對 MiniMax 的真實網路往返）。

---

## 3. 階段 2 —— MinIO 是真相來源

抽出的條目合併進 `wiki-data` bucket 裡的 `wiki.json`（並發寫入用 ETag CAS）。MinIO 權威；
PG 是可由它重建的衍生索引。

```bash
docker compose exec -T wiki-processor python -c "
from repository.minio_client import MinioStorage
import json; s=MinioStorage()
print(json.dumps(s.get_json('wiki.json')['apis']['billing'], indent=2, ensure_ascii=False))"
```
真 `wiki.json → apis.billing`：
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
注意：真 LLM 把 **module 命名為 `billing`**（去掉 `-api`）；app 身分另存為 `source_app: billing-api`。

`wiki.json` 結構：`schema_version: 2`，加上 `metadata`：
```json
{"version":"1.0","created_at":"2026-06-14T03:54:12.792019","updated_at":"2026-06-14T03:54:25.631571"}
```

bucket 內物件（`s.list_files('')`）：
```
wiki.json                                              # 合併後的 wiki
snapshots/billing-api.json                             # 每-app 輸入快照（變更偵測用）
snapshots/identity-api.json
snapshots/warehouse-api.json
audit/2026-06-14T03:54:17.260847-f2139279.json         # 每次推送一筆 append-only 記錄
audit/2026-06-14T03:54:21.469956-4bcc2201.json
audit/2026-06-14T03:54:25.640198-531124d7.json
```
`snapshots/billing-api.json`（我們送的原始輸入，原樣保留）：
```json
{"billing-api.md": "# Billing API\n\nPOST /billing/charge - Charge a saved credit card to collect payment for a completed purchase."}
```
一筆 audit 記錄：
```json
{"timestamp":"2026-06-14T03:54:17.260847","source_app":"billing-api","files_count":1,
 "status":"success","files_updated":["POST /billing/charge"]}
```

---

## 4. 階段 3 —— 實際被 embed 的是什麼（`embed_text`）

embed 前，每個條目由 `wiki-processor/services/embeddings/text.py::entry_to_text` 攤平成一個字串：
```
"{module} | {api_key} | {endpoint} | {description} | {params}"   (空的部分丟掉)
```
billing 的真 `embed_text`（從下方 PG 讀出）：
```
billing | POST /billing/charge | POST /billing/charge | Charge a saved credit card to collect payment for a completed purchase.
```
被向量化的是這個確切字串 —— 不是原始 markdown。

---

## 5. 階段 4 —— embedding API（真 Gemini 請求 + 回應）

processor 把 `embed_text` 送給 Gemini。真請求：
```
POST https://generativelanguage.googleapis.com/v1beta/openai/v1/embeddings
Authorization: Bearer AIza…redacted…
{"model":"gemini-embedding-001","input":["billing | POST /billing/charge | …"],"dimensions":1536}
```
真回應（結構 + 實際向量開頭）：
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
自己重現（貼上 embed_text）：
```bash
curl -s https://generativelanguage.googleapis.com/v1beta/openai/v1/embeddings \
  -H "Authorization: Bearer $GEMINI_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gemini-embedding-001","input":["billing | POST /billing/charge | POST /billing/charge | Charge a saved credit card to collect payment for a completed purchase."],"dimensions":1536}' \
  | python3 -c 'import sys,json;e=json.load(sys.stdin)["data"][0]["embedding"];print("dim",len(e),"first8",[round(x,9) for x in e[:8]])'
```
→ `dim 1536 first8 [-0.008967627, 0.001633695, -0.001927566, -0.077539764, 0.006107465, 0.032517925, 0.021139143, 0.001127183]`

---

## 6. 階段 5 —— PG 列（索引）

該向量 + metadata 寫入 `api_entries`。真列：
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
儲存向量的前 8 個分量：
```bash
docker compose exec -T pg psql -U wiki -d wiki -tA -c \
  "SELECT (string_to_array(trim(both '[]' from embedding::text), ','))[1:8]
   FROM api_entries WHERE source_app='billing-api';"
```
→ `{-0.008967627,0.0016336951,-0.0019275661,-0.077539764,0.0061074654,0.032517925,0.021139143,0.0011271825}`

**✅ 交叉驗證：** 這前 8 個數字與階段 4 的 Gemini API 回應完全相符。PG 向量*就是* `embed_text`
的 Gemini embedding —— 沒有別的。

`app_sync`（每 app 一列，驅動出處 / 增量取代）：
```
 source_app    | source_version | synced_at
 billing-api   | v1             | 2026-06-14 03:54:12.778821+00
 identity-api  | v1             | 2026-06-14 03:54:17.348813+00
 warehouse-api | v1             | 2026-06-14 03:54:21.49143+00
```

---

## 7. 階段 6 —— 透過 mcp 查詢（以及*為何*它這樣答）

### 問句
一個與儲存 endpoint **零關鍵字重疊**的改寫（`billing` / `charge` / `credit card` 都沒出現）：
```
"deduct money from a shopper card"
```

### mcp 的答案
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
`POST /billing/charge` 排第 1 —— 靠**語意**，不是關鍵字。

### mcp 怎麼算出來的（逐步）
1. mcp 用同一個 Gemini 端點 + `dimensions:1536` 把**查詢字串** embed
   （`mcp-server/services/embeddings.py::QueryEmbedder.aembed_query`）。真查詢向量開頭：
   ```
   first8 [-0.00538147, 0.017700898, 0.011566551, -0.064901225, -0.024086909, 0.007932861, 0.002413509, 0.016159862]
   ```
2. mcp 跑一條 SQL —— pgvector cosine 距離 `<=>`，score = `1 - distance`
   （`mcp-server/repository/pg_reader.py::semantic_search`）：
   ```sql
   SELECT module, api_key, description, source_app,
          1 - (embedding <=> $query_vec::vector) AS score
   FROM api_entries
   WHERE embedding IS NOT NULL
   ORDER BY embedding <=> $query_vec::vector
   LIMIT 3;
   ```

### 證明 —— 在 psql 直接重現 mcp 的確切分數
把查詢 embed，把 1536-float 向量字面丟進**同一條** SQL，自己對 PG 跑：
```bash
# 1) 取得查詢向量的 pgvector 字面
Q="deduct money from a shopper card"
VEC=$(curl -s "$EMBEDDING_BASE_URL/v1/embeddings" \
  -H "Authorization: Bearer $GEMINI_KEY" -H 'Content-Type: application/json' \
  -d "{\"model\":\"gemini-embedding-001\",\"input\":[\"$Q\"],\"dimensions\":1536}" \
  | python3 -c 'import sys,json;v=json.load(sys.stdin)["data"][0]["embedding"];print("["+",".join(repr(x) for x in v)+"]")')

# 2) 跑 mcp 跑的同一個 cosine 排序
docker compose exec -T pg psql -U wiki -d wiki -c \
 "SELECT module, api_key, source_app,
         round((1 - (embedding <=> '$VEC'::vector))::numeric,4) AS score
  FROM api_entries WHERE embedding IS NOT NULL
  ORDER BY embedding <=> '$VEC'::vector LIMIT 3;"
```
真 psql 輸出：
```
  module   |       api_key        |  source_app   | score
-----------+----------------------+---------------+--------
 billing   | POST /billing/charge | billing-api   | 0.5382
 warehouse | GET /warehouse/stock | warehouse-api | 0.4999
 identity  | POST /identity/login | identity-api  | 0.4244
```
**✅ 與 mcp `/semantic_search` 分數完全相同。** mcp 做的就是這個 cosine 排序、別無其他 ——
沒有隱藏 re-ranking、沒有魔法。

### 為何 billing 贏
cosine 相似度量的是**查詢語意**與每個條目的 **`embed_text` 語意**之間的夾角。
"deduct money from a shopper card" 在 Gemini 向量空間裡最接近 "charge a saved credit card
to collect payment"（0.5382），離 warehouse stock（0.4999）、login（0.4244）較遠。模型懂
*charge ≈ deduct money*、*credit card ≈ shopper card* —— 一個共同字都沒有。（用 mock
embedding 時，相似度只是 token 重疊，這種無關鍵字的查詢就不會把 billing 排第一 —— 這就是
真 embedding 買到的差別。）

---

## 8. 重現整件事

```bash
# 起真 stack（需 .env 裡的 MiniMax + Gemini 金鑰，見 §0）
docker compose up -d --build
curl -s localhost:8001/health

# 推一個 app
curl -s -X POST localhost:8001/process -H 'Content-Type: application/json' -d '{
 "markdowns":{"billing-api.md":"# Billing API\n\nPOST /billing/charge - Charge a saved credit card to collect payment for a completed purchase."},
 "timestamp":"2026-06-14T03:00:00","trigger_info":{"source":"walkthrough"},
 "source_app":"billing-api","source_version":"v1"}'

# MinIO 真相來源
docker compose exec -T wiki-processor python -c "from repository.minio_client import MinioStorage;import json;print(json.dumps(MinioStorage().get_json('wiki.json')['apis'],indent=2))"

# PG 列 + 向量
docker compose exec -T pg psql -U wiki -d wiki -x -c "SELECT module,api_key,source_app,embed_text,vector_dims(embedding) dim,embedding_model FROM api_entries WHERE source_app='billing-api';"

# 查詢 + psql 重現：見 §7
```

上面每個數字都配上產生它的指令。兩個 ✅ 交叉驗證（Gemini 向量 == PG 向量；mcp 分數 ==
psql cosine）讓這份文件是可驗證的，而非「相信我」。
</content>
