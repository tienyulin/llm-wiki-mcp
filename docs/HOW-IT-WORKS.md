# 這系統到底怎麼運作（從零看懂，含真實紀錄）

> **看這一份就好。** 這是唯一的「入口」文件。它用白話 + **我現場用真 Minimax M3 LLM +
> 本地 embedding 模型跑出來的真實輸出**，帶你看一筆資料怎麼從「某 app 推一份文件」一路變成
> 「Claude 查得到、還能跨領域推理」。每一步都有：**指令 → 真實輸出 → 這代表什麼 → 壞了會怎樣**。
>
> 紀錄擷取於 2026-06-22，環境：真 Minimax-M3 + 本地 bge-small embedding（384 維）+
> 真 MinIO + 真 Postgres/pgvector。LLM 輸出非確定性，你自己重跑數字會略不同。

---

## 1. 一句話：這是什麼？

公司有很多服務（app），每個都有自己的 API 文件、操作手冊。散在各處，AI 看不到全貌。
**這系統讓每個 app 把文件「推」進來，自動整理成一份團隊共享、給 AI（Claude）看的 Wiki**，
而且 Claude 可以「原生」連進來查、還能把不同領域的知識串起來推理。

解決的痛：**「我們到底有哪些 API？這件事哪個服務能做？怎麼做？」** —— 不用翻 100 個 repo，
問一句就好。

---

## 2. 名詞表（先看這個，後面就不卡）

| 名詞 | 一句白話 |
|------|----------|
| **LLM** | 大型語言模型（這裡用 Minimax M3）。負責「讀文件、抽出結構」。 |
| **embedding（向量）** | 把一段文字變成一串數字。意思相近的文字，數字也相近 → 能做「語意搜尋」。 |
| **embedding 模型** | 把文字轉成向量的模型（這裡用本地 bge-small，384 個數字）。 |
| **MinIO** | 本地版的「雲端檔案桶」（相容 S3）。存 wiki 檔案。**真相來源**。 |
| **Postgres / pgvector** | 資料庫 + 向量擴充。存「搜尋索引」（含向量），讓查詢又快又能比語意。 |
| **真相來源 vs 索引** | MinIO 的檔是正本；Postgres 是為了查得快、從正本算出來的副本（壞了可重建）。 |
| **每-app 物件** | 每個 app 的資料各存一個檔 `apps/<app>.json`，不是全部擠一個大檔 → 100 個 app 同時更新不互卡。 |
| **CAS** | 寫入前比對版本（ETag），相符才寫。防兩個人同時改、互相蓋掉。 |
| **hybrid search** | 「關鍵字搜尋」+「語意搜尋」兩種一起跑、合併結果。問法不同也找得到。 |
| **RRF** | 倒數排名融合。合併上面兩種搜尋結果的方法（只看名次，不管分數尺度）。 |
| **MCP** | 一套協議，讓 Claude 這種 AI agent 直接連外部工具。本系統開了 MCP，Claude 不用自寫程式就能查 wiki。 |

---

## 3. 系統地圖（四個服務 + 一套共用設施）

```
       各 app（payments-api、flashback-api、oracle 知識…）
            │  把 markdown 文件 POST 進來
            ▼
  ┌────────────────────┐   寫        ┌──────────────────────────┐
  │ wiki-processor :8001 │ ─────────▶ │  共用 infra (llm-wiki-infra)│
  │ 收文件→LLM抽取→寫檔   │            │   • MinIO（存 wiki 檔）       │
  └────────────────────┘ ◀───────── │   • Postgres + pgvector     │
            ▲                         └──────────────────────────┘
            │ 同步索引                          ▲
  ┌────────────────────┐                        │ 讀
  │  mcp-server :8002    │ ───────────────────────┘
  │  查詢（REST + MCP）   │
  └────────────────────┘
            ▲
            │ MCP / HTTP
        Claude / AI agent
```

| 服務 | 一句職責 |
|------|----------|
| **llm-wiki-infra** | 共用設施：一套 MinIO + Postgres。**先啟動它**，其他服務接上去。 |
| **wiki-processor** :8001 | **寫入端**：收文件 → 叫 LLM 抽取 → 寫進 wiki + 索引。唯一會改資料的。 |
| **mcp-server** :8002 | **唯讀查詢端**：給人用 REST、給 Claude 用 MCP。 |
| **flashback-api** :8003 | 範例 app（Oracle 救援 API），也示範「app 怎麼推文件進來」。 |

---

## 4. 真實實跑：一筆資料的一生

情境：推 **payments-api**（兩支 API）、**flashback-api**（兩支 API）、一份 **oracle-kb**
知識文件。全程看真實輸出。

### 步驟 0 — 確認服務活著
```bash
curl -s localhost:8001/health
```
真輸出：
```json
{"status":"ok","minio_connected":true,"llm_configured":true,"llm_provider":"minimax",
 "vector_index_connected":true,"embeddings_configured":true,"minimax_accessible":true}
```
**這代表什麼：** processor 連得到 MinIO、Postgres、真 Minimax。`minimax_accessible:true` = key 有效。
**壞了會怎樣：** 若 `minimax_accessible:false` → key 錯/空，抽取會失敗（但服務不會崩，回 `status:"failed"`）。

---

### 步驟 (a) — 推一個 app 的文件
```bash
curl -X POST localhost:8001/process -H 'Content-Type: application/json' -d '{
  "markdowns": {"payments.md": "# Payments API\nPOST /payments/charge - Charge a saved credit card to collect payment.\nPOST /payments/refund - Refund money back to a customer."},
  "timestamp": "2026-06-22T00:00:00", "trigger_info": {"source":"demo"},
  "source_app": "payments-api", "source_version": "v1"}'
```
真回應（耗時 **12868ms** —— 真 LLM 往返）：
```json
{
  "status": "success",
  "source_app": "payments-api",
  "files_updated": ["POST /payments/charge", "POST /payments/refund"],
  "changes_summary": {"added": ["payments.md"], "modified": [], "deleted": []},
  "processing_time_ms": 12868
}
```
**這代表什麼：** LLM 讀懂了 markdown，抽出兩支 endpoint。約 13 秒都花在真 LLM 上。
**壞了會怎樣：** 很多 app 同時推會撞 LLM 限流（429）；系統內建**退避重試 + 併發上限**，
把「失敗」轉成「稍慢但成功」（壓測實證：失敗率 65%→0%）。

---

### 步驟 (b) — 資料存進 MinIO（真相來源，每-app 一個檔）
```bash
docker exec wiki-processor python -c \
 "import json;from repository.minio_client import MinioStorage;print(json.dumps(MinioStorage().get_json('apps/payments-api.json'),ensure_ascii=False,indent=2))"
```
真內容：
```json
{
  "schema_version": 2,
  "source_app": "payments-api",
  "source_version": "v1",
  "apis": {
    "Payments": {
      "POST /payments/charge": {
        "method": "POST", "path": "/payments/charge",
        "description": "Charge a saved credit card to collect payment.",
        "sources": ["payments.md"],
        "source_app": "payments-api", "source_version": "v1"
      },
      "POST /payments/refund": { "method": "POST", "path": "/payments/refund",
        "description": "Refund money back to a customer.", "sources": ["payments.md"],
        "source_app": "payments-api", "source_version": "v1" }
    }
  },
  "knowledge": {},
  "overview": "The payments-api service ... processing charges against saved credit cards to collect payment, and issuing refunds ...（真 LLM 寫的一段總覽）",
  "updated_at": "2026-06-22T13:49:03.963944"
}
```
桶裡的物件：
```
apps/payments-api.json     apps/flashback-api.json     apps/oracle-kb.json    # 每 app 一個（真相來源）
snapshots/payments-api.json …                                                 # 原始輸入快照（變更偵測用）
audit/2026-06-22T13:49:03…json …                                              # 每次推送一筆紀錄
```
**這代表什麼：** payments-api 的資料只在**它自己的檔**。`sources` 記得每條來自哪個 markdown；
`source_app` 由系統蓋上（不信任 LLM 自報）。LLM 還順手生了一段 `overview`。
**壞了會怎樣：** 兩個請求同時改同一個 app → CAS 比對 ETag，輸的那個重讀重試，不會蓋掉資料。
不同 app 各自一個檔 → 根本不會互卡（這就是「每-app 物件」的好處）。

---

### 步驟 (c) — 每次推送留一筆 audit
```bash
docker exec wiki-processor python -c \
 "from repository.minio_client import MinioStorage;import json;s=MinioStorage();print(json.dumps(s.get_json([k for k in s.list_files('audit/')][0]),ensure_ascii=False))"
```
真紀錄：
```json
{"timestamp":"2026-06-22T13:49:03.980953","source_app":"payments-api","files_count":1,
 "status":"success","files_updated":["POST /payments/charge","POST /payments/refund"]}
```
**這代表什麼：** 每次寫入都有 append-only 紀錄，可追溯誰在何時改了什麼。

---

### 步驟 (d) — 同步進 Postgres 索引（含向量）
```bash
docker exec llm-wiki-pg psql -U wiki -d wiki -x -c \
 "SELECT module,api_key,source_app,embed_text,vector_dims(embedding) dim,embedding_model
  FROM api_entries WHERE api_key='POST /payments/charge';"
```
真列：
```
module          | Payments
api_key         | POST /payments/charge
source_app      | payments-api
embed_text      | Payments | POST /payments/charge | POST /payments/charge | Charge a saved credit card to collect payment.
dim             | 384
embedding_model | bge-small
```
向量前 8 維（共 384）：
```
{-0.061822545,-0.055060707,-0.015334889,0.025303239,0.027342524,-0.073736265,0.027584018,0.044032466}
```
**這代表什麼：** `embed_text`（不是原始 markdown）被丟給 embedding 模型，變成 384 個數字存起來。
查詢時就是拿這串數字比相似度。
**壞了會怎樣：** Postgres 掛了，查詢自動退回直接掃 MinIO；embedding 模型掛了，退回關鍵字。
索引整個壞了 → `POST /admin/reindex` 從 MinIO 重建。**索引是副本，壞了不影響正本。**

---

### 步驟 (e) — 知識文件走一樣的路，存到 knowledge_entries
推一份**不是 API spec** 的散文知識（`doc_type` 省略 → 系統看沒有 endpoint，自動判定為 knowledge）：
```bash
curl -X POST localhost:8001/process -H 'Content-Type: application/json' -d '{
  "markdowns":{"oracle.md":"# Oracle Flashback\nOracle Flashback recovers data after accidental data loss. FLASHBACK TABLE rewinds a table to a past point in time without restoring a backup."},
  "timestamp":"...","trigger_info":{},"source_app":"oracle-kb","source_version":"19c"}'
```
PG 裡的 knowledge 列：
```
doc_id          | oracle-kb:oracle_flashback
source_app      | oracle-kb
title           | Oracle Flashback
embed_text_head | Oracle Flashback | Oracle Flashback is a recovery feature used to restore data following a…
dim             | 384
```
**這代表什麼：** wiki 不只裝 API，也裝「通用知識」（怎麼救資料、怎麼寫 FastAPI…），一樣被向量化。
**壞了會怎樣：** 同 API；knowledge 也有 best-effort 同步。

到這裡資料庫計數：`api_entries=4`、`knowledge_entries=1`、`app_sync=3`（3 個 app）。

---

### 步驟 (f) — 建立「跨應用概念」+ 彙總視圖
```bash
curl -s -X POST localhost:8001/admin/rebuild-concepts
```
真輸出：
```json
{"status":"ok","concepts":2,"apps":2,"endpoints":4}
```
**這代表什麼：** 把所有 app 的資料掃一遍，產生「概念」（把相關的 endpoint / 知識歸到同一個主題），
並重建彙總 `wiki.json`（給查詢端讀概念/總覽）。這是**批次/排程**動作，不是每次推送都做
（早期版本每次都做整包 LLM → 規模下會逾時，已改成確定性、毫秒級）。

---

### 步驟 (g) — 查詢（hybrid：問法不同也找得到）
**A. search_apis** —— 問「退錢給客戶」（跟存的字「refund / charge」零重疊）：
```bash
curl 'localhost:8002/search_apis?query=give a customer their money back'
```
真結果（`mode: hybrid`）第 1 名：
```json
{"module":"Payments","api_key":"POST /payments/refund","description":"Refund money back to a customer.","source_app":"payments-api"}
```
**B. semantic_search** —— 問「undo a deleted database row」：
```
mode: semantic
  Flashback API  POST /recover        0.7731   ← 第 1（靠語意）
  Flashback API  GET /recover/{id}    0.5906
  Payments       POST /payments/refund 0.5362
```
**C. search_knowledge** —— 問「how to recover lost data」：
```
mode: hybrid  hits: ['oracle-kb:oracle_flashback']
```
**這代表什麼：** 三種查詢都靠**意思**命中，不靠剛好用對字。`mode` 告訴你走了哪條路
（`hybrid` = 關鍵字+語意都跑；`semantic` = 純向量；`wiki_scan`/`keyword_fallback` = 降級）。
**壞了會怎樣：** PG/embedding 不可用時 `mode` 會變成降級值，仍答得出來，只是少了語意。

---

### 步驟 (h) — 跨領域：把「知識」連到「能做這件事的 API」
```bash
curl 'localhost:8002/get_concept?name=recover'
```
真輸出：
```json
{"concept": {
  "description": "Concept 'recover'.",
  "related": [
    "Flashback API::POST /recover",
    "Flashback API::GET /recover/{id}",
    "knowledge::oracle-kb:oracle_flashback"
  ],
  "apps": ["flashback-api", "oracle-kb"]
}}
```
**這代表什麼：** `recover` 這個概念同時連到 **flashback-api 的 endpoint** 和 **Oracle 知識文件**。
所以 agent 問「資料誤刪怎麼辦」時，能從「概念」一步跳到「知識（怎麼救）+ 內部 API（用哪支救）」。
這就是「跨領域推理」的橋。

---

### 步驟 (i) — Claude 怎麼連進來（MCP）
人接 Claude Code：`claude mcp add --transport http llm-wiki http://localhost:8002/mcp/`

底層其實是標準 MCP 協議。真 handshake：
```bash
curl -s -X POST localhost:8002/mcp/ -H 'Accept: application/json, text/event-stream' \
 -H 'Content-Type: application/json' \
 -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"cli","version":"0"}}}'
```
→ `serverInfo: {'name':'llm-wiki', ...}  protocol: 2025-03-26`

真的呼叫一個工具 `search_knowledge("recover lost data")`：
```json
{"results":[{"doc_id":"oracle-kb:oracle_flashback","title":"Oracle Flashback",
 "summary":"Oracle Flashback is a recovery feature used to restore data following accidental data loss, with FLASHBACK TABLE enabling point-in-time recovery ...",
 "source_app":"oracle-kb","score":0.0167}], "mode":"hybrid"}
```
**這代表什麼：** Claude 不用自寫 REST client —— 它把這些查詢當「工具」直接呼叫。
查詢端的邏輯和 REST 完全同一套（MCP 只是薄包裝）。
**壞了會怎樣：** 正式環境要設 `MCP_ALLOWED_HOSTS` 開 DNS-rebinding 保護；dev 預設關。

---

## 5. 整條流程一句話總結

**app 推 markdown → LLM 抽成結構 → 存進它自己的 MinIO 檔（正本）+ Postgres 向量（索引）
→ 批次建立跨應用概念 → 人/Claude 用 hybrid 查詢，靠意思命中，還能跨「知識↔API」推理。**

---

## 6. 我想做 X，看哪份文件

| 我想… | 看這裡 |
|-------|--------|
| 在本機把整套跑起來 | 平台 `README.md`、`docs/guides/local-setup.md` |
| 看實測效能/規模數字 | `docs/test-results.md` |
| 懂寫入端細節（CAS、抽取、限流） | `llm-wiki-processor/` 的 README + `docs/` |
| 懂查詢端細節（hybrid、MCP） | `llm-mcp-server/` 的 README + `docs/architecture/` |
| 懂向量搜尋設計與評估 | `docs/architecture/vector-search.md` |
| 查完整 API 端點規格 | `docs/api/schema.md` |
| 出問題排錯 | `docs/troubleshooting.md` |
| 跑大規模壓測 | `tests/stress/STRESS_TEST_PLAN.md` |

---

## 7. 自己重跑這份紀錄

```bash
# 1) 共用 infra
cd llm-wiki-infra && docker compose up -d
# 2) 寫入端 + 查詢端（.env 設真 LLM key，或 MOCK_LLM=true 免 key）
cd ../llm-wiki-processor && docker compose up -d --build
cd ../llm-mcp-server && docker compose up -d --build
# 3) 推文件 → 重建概念 → 查詢（見上面步驟 a–i 的指令）
```
每個指令旁邊都配了真實輸出。LLM 是真的、非確定性的，所以你的數字會略不同 —— 但**每一層存什麼、
怎麼流、為什麼這樣答**都一樣。這份文件的目的就是：**讓它不再是黑盒子。**
</content>
