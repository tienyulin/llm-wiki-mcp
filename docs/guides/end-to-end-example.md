# 端到端完整範例：兩個 markdown 從提交到查詢

這份文件用**一個真實跑過的例子**走完整條 pipeline：兩個應用各提交一份
markdown，看每一步資料變成什麼樣子、MinIO 和 Postgres 各存了什麼、
查詢時用什麼撈到什麼。所有 JSON / SQL 輸出都是在本機環境
（`MOCK_LLM=true`、`MOCK_EMBEDDINGS=true`）實際執行的結果，你可以照著
[本地設置指南](local-setup.md) 起服務後原樣重現。

登場角色：

| 角色 | 說明 |
|---|---|
| `app-inventory` | 庫存服務，提交 `inventory_api.md`，之後會改版一次 |
| `app-orders` | 訂單服務，提交 `orders_api.md` |
| wiki-processor :8001 | 收 markdown → LLM 萃取 → 寫入 MinIO → 同步 PG |
| mcp-server :8002 | 查詢 API（給 Claude / LLM agents 用） |

---

## 第 0 步：原始輸入 —— 兩份 markdown

`app-inventory` 的 repo 裡有 `docs/inventory_api.md`：

```markdown
# Inventory Service API（庫存服務）

提供庫存查詢與管理。

## Endpoints

- GET /inventory/health — 健康檢查
- GET /inventory/{id} — 查詢單一庫存品項
- POST /inventory — 新增庫存品項
```

`app-orders` 的 `docs/orders_api.md`：

```markdown
# Orders Service API（訂單服務）

- GET /orders — 列出訂單
- POST /orders — 建立訂單
```

## 第 1 步：CI 提交 —— `POST /process`

應用 push 後，GitLab CI 把 markdown 連同身分資訊送給 wiki-processor。
實際的 request：

```json
POST http://wiki-processor:8001/process
{
  "markdowns": {
    "inventory_api.md": "# Inventory Service API（庫存服務）\n\n提供庫存查詢與管理。\n..."
  },
  "timestamp": "2026-06-11T10:00:00",
  "trigger_info": {"source": "gitlab-ci", "branch": "main"},
  "source_app": "app-inventory",
  "source_version": "a1b2c3d"
}
```

實際的 response（290ms）：

```json
{
  "status": "success",
  "message": "Wiki generated successfully",
  "changes_summary": {"added": ["inventory_api.md"], "modified": [], "deleted": []},
  "source_app": "app-inventory",
  "files_updated": ["GET /inventory/health", "GET /inventory/{id}", "POST /inventory"],
  "processing_time_ms": 290
}
```

`app-orders` 同樣提交一次（`source_version: "9f8e7d6"`）。

## 第 2 步：wiki-processor 內部發生了什麼

**(a) 變更偵測**——拿這次的 markdowns 跟上次的快照
（`snapshots/app-inventory.json`）比對。第一次提交時快照不存在，所以
`changes = {"added": ["inventory_api.md"], "modified": [], "deleted": []}`。
若完全沒變，這裡直接回 success 並跳過後面所有步驟（不花 LLM 錢）。

**(b) LLM 萃取**——markdown 交給 LLM，要求輸出結構化的 API entries。
（mock 模式用正則確定性地推導，真實模式由 LLM 解析。）得到：

```json
{"apis": {"inventory": {
  "GET /inventory/health": {"method": "GET", "path": "/inventory/health",
                            "description": "Inventory Service API（庫存服務）"},
  "GET /inventory/{id}":   {"method": "GET", "path": "/inventory/{id}", "description": "..."},
  "POST /inventory":       {"method": "POST", "path": "/inventory", "description": "..."}
}}}
```

**(c) 蓋章（stamp）**——processor 在每個 entry 上蓋 `source_app` /
`source_version`。**LLM 的輸出不被信任帶身分**，身分永遠由 processor 控制。

**(d) 向量化（可選）**——每個 entry 先用統一格式轉成一段文字再 embed：

```
embed_text = "inventory | GET /inventory/health | GET /inventory/health | Inventory Service API（庫存服務）"
            （格式：module | api_key | METHOD path | description | params）

embedding  = 1536 維向量。mock 模式下是稀疏的 token hash，例如這條只有
             5 個非零維度：{43: 0.3922, 695: -0.3922, 900: -0.1961, 1112: 0.7845, 1477: 0.1961}
             真實模式則是 OpenAI-compatible API 回的稠密向量。
```

**(e) CAS 寫入 MinIO**——合併進 `wiki.json`（If-Match 條件寫入，多副本
並發也不會互相蓋掉），然後 best-effort 同步 PG、通知 mcp-server 清快取。

## 第 3 步：MinIO 裡現在有什麼

兩個應用提交完後，`wiki-data` bucket 的完整內容（5 個 objects）：

```
audit/2026-06-11T19:50:23-8dffcfe3.json     ← 每次提交一筆審計記錄
audit/2026-06-11T19:50:36-b04ff54f.json
snapshots/app-inventory.json                 ← 各 app 上次提交的 markdown 原文（變更偵測用）
snapshots/app-orders.json
wiki.json                                    ← ★ 唯一事實來源
```

`wiki.json` 實際內容（完整）：

```json
{
  "schema_version": 2,
  "apis": {
    "inventory": {
      "GET /inventory/health": {
        "method": "GET", "path": "/inventory/health",
        "description": "Inventory Service API（庫存服務）",
        "source_app": "app-inventory", "source_version": "a1b2c3d"
      },
      "GET /inventory/{id}":  { "...同上格式...": "source_version a1b2c3d" },
      "POST /inventory":      { "...同上格式...": "source_version a1b2c3d" }
    },
    "orders": {
      "GET /orders":  { "...": "source_app app-orders, source_version 9f8e7d6" },
      "POST /orders": { "...": "source_app app-orders, source_version 9f8e7d6" }
    }
  },
  "metadata": {"version": "1.0", "created_at": "2026-06-11T19:50:23", "updated_at": "2026-06-11T19:50:36"}
}
```

audit 記錄長這樣（append-only，永不改寫）：

```json
{"timestamp": "2026-06-11T19:50:23", "source_app": "app-inventory",
 "files_count": 1, "status": "success",
 "files_updated": ["GET /inventory/health", "GET /inventory/{id}", "POST /inventory"]}
```

## 第 4 步：Postgres 裡現在有什麼

同一份資料在 PG 是**一個 API 一列**（attached 向量），這就是查詢索引：

```
wiki=# SELECT module, api_key, source_app FROM api_entries ORDER BY module, api_key;
  module   |        api_key        |  source_app
-----------+-----------------------+---------------
 inventory | GET /inventory/health | app-inventory
 inventory | GET /inventory/{id}   | app-inventory
 inventory | POST /inventory       | app-inventory
 orders    | GET /orders           | app-orders
 orders    | POST /orders          | app-orders
```

單列放大看（節錄）：

```
module          | inventory
api_key         | GET /inventory/health
source_version  | a1b2c3d
detail          | {完整的 entry JSON，直接服務 get_api_detail}
embed_text      | inventory | GET /inventory/health | GET /inventory/health | Inventory …
embedding       | [1536 維向量]（HNSW 索引）
embedding_model | text-embedding-3-small
```

另外兩張輔助表：

```
wiki=# SELECT * FROM app_sync;            -- 防止舊請求覆蓋新資料的時間戳守衛
  source_app   |         synced_at          | source_version
---------------+----------------------------+----------------
 app-inventory | 2026-06-11 19:50:23.76+00  | a1b2c3d
 app-orders    | 2026-06-11 19:50:36.47+00  | 9f8e7d6

wiki=# SELECT key, value FROM index_state; -- 給監控看的同步狀態
 last_sync | {"entries": 2, "synced_at": "...19:50:36", "source_app": "app-orders"}
```

**分工一句話**：MinIO 存整份 wiki（事實來源，壞了一切以它為準）；
PG 把同樣的資料攤平成可以建索引的列（語意/關鍵字/點查都快，但隨時可以
從 wiki.json 重建，`POST /admin/reindex` 一鍵完成）。

## 第 5 步：用什麼撈什麼（mcp-server 查詢端）

**列出全部 API**（背後：PG B-tree 索引掃 `module, api_key`）：

```
$ curl "localhost:8002/list_apis"
{"modules": {"inventory": ["GET /inventory/health", "GET /inventory/{id}", "POST /inventory"],
             "orders":    ["GET /orders", "POST /orders"]}}
```

**單一 API 詳情**（背後：PG 以 UNIQUE(module, api_key) 點查 `detail` 欄）：

```
$ curl "localhost:8002/get_api_detail?module=inventory&api_key=GET%20/inventory/{id}"
{"detail": {"method": "GET", "path": "/inventory/{id}",
            "description": "Inventory Service API（庫存服務）",
            "source_app": "app-inventory", "source_version": "a1b2c3d"}}
```

**關鍵字搜尋**（背後：PG trigram 索引 `embed_text ILIKE '%inventory%'`；
`mode` 告訴你答案從哪條路來）：

```
$ curl "localhost:8002/search_apis?query=inventory"
{"results": [ ...3 筆 inventory entries... ], "count": 3, "mode": "pg_keyword"}
```

**語意搜尋 vs 關鍵字搜尋的差別**——用一句完整的問題查「check inventory
health status」：

```
$ curl "localhost:8002/semantic_search?query=check inventory health status&top_k=3"
{"results": [
   {"module": "inventory", "api_key": "GET /inventory/health", "score": 0.5883, ...},
   {"module": "inventory", "api_key": "POST /inventory",        "score": 0.4264, ...},
   {"module": "inventory", "api_key": "GET /inventory/{id}",    "score": 0.3922, ...}],
 "count": 3, "mode": "semantic"}

$ curl "localhost:8002/search_apis?query=check inventory health status"
{"results": [], "count": 0, "mode": "wiki_scan"}      ← 子字串比對：整句找不到，0 筆
```

語意搜尋把 health check endpoint 排第一（分數 = cosine 相似度）；
同一句話用子字串比對什麼都找不到。這就是向量索引存在的理由。

**系統狀態**（背後：wiki metadata + PG `index_state`）：

```
$ curl "localhost:8002/wiki_info"
{"modules": 2, "total_endpoints": 5, "metadata": {...},
 "vector_index": {"available": true, "semantic_search": true,
                  "entries": 5, "embedded": 5,
                  "last_sync": {"source_app": "app-orders", "synced_at": "...", "entries": 2}}}
```

## 第 6 步：應用改版 —— 只取代自己的 entries

`app-inventory` 發 v1.1.0：把 `POST /inventory` 換成 `POST /inventory/batch`，
重新提交（`source_version: "e5f6a7b"`）。response：

```json
{"status": "success",
 "changes_summary": {"added": [], "modified": ["inventory_api.md"], "deleted": []},
 "files_updated": ["GET /inventory/health", "GET /inventory/{id}", "POST /inventory/batch"]}
```

前後對照（wiki.json 與 PG 同步變化）：

| | 改版前 | 改版後 |
|---|---|---|
| inventory | health / {id} / **POST /inventory** (a1b2c3d) | health / {id} / **POST /inventory/batch** (e5f6a7b) |
| orders | GET、POST /orders (9f8e7d6) | **完全不變** (9f8e7d6) |

```
wiki=# SELECT module, api_key, source_version FROM api_entries ORDER BY 1,2;
 inventory | GET /inventory/health | e5f6a7b      ← 全部換成新版
 inventory | GET /inventory/{id}   | e5f6a7b
 inventory | POST /inventory/batch | e5f6a7b      ← 舊的 POST /inventory 消失了
 orders    | GET /orders           | 9f8e7d6      ← 別人的 entries 一根毛都沒動
 orders    | POST /orders          | 9f8e7d6
```

這就是「應用級增量更新」：每次提交**整批取代該 app 自己的 entries**，
100 個應用並行提交也互不干擾。

## 第 7 步：PG 掛掉會怎樣（實際把 PG 停掉）

```
$ sudo service postgresql stop

$ curl "localhost:8002/search_apis?query=inventory"
{"results": [...同樣 3 筆...], "count": 3, "mode": "wiki_scan"}   ← 答案相同，改走 MinIO 快取路徑

$ curl "localhost:8002/semantic_search?query=check inventory health status"
{"results": [], "count": 0, "mode": "keyword_fallback"}           ← 語意能力消失，降級為關鍵字（不報錯）

$ curl "localhost:8002/wiki_info"   → "vector_index": {"available": false}
```

期間若有應用提交，wiki.json 照常更新（PG 同步失敗只在 audit 記一筆
`success_index_sync_failed`）。PG 回來後一鍵補齊：

```
$ sudo service postgresql start
$ curl -X POST localhost:8001/admin/reindex -H "X-API-Key: $PROCESSOR_API_KEY"
{"status": "ok", "apps": 2, "entries": 5, "embedded": 5}
```

## 速查表：資料在哪裡、誰寫、誰讀

| 資料 | 存哪裡 | 誰寫入 | 誰讀取 / 用什麼撈 |
|---|---|---|---|
| `wiki.json`（事實來源） | MinIO | wiki-processor（ETag CAS） | mcp-server fallback 路徑、`/admin/reindex` |
| `snapshots/{app}.json` | MinIO | wiki-processor | 下次提交的變更偵測 |
| `audit/*.json` | MinIO | wiki-processor（append-only） | 維運稽核、查 `success_index_sync_failed` |
| `api_entries`（一列一 API + 向量） | PG | processor 每次提交同步 / reindex | `/list_apis`(B-tree)、`/get_api_detail`(點查)、`/search_apis`(trigram)、`/semantic_search`(HNSW ANN) |
| `app_sync` | PG | processor（交易內守衛） | 防跨副本亂序覆蓋 |
| `index_state` | PG | processor | `/wiki_info.vector_index`（監控漂移） |

設計與效能數字見[向量檢索架構](../architecture/vector-search.md)；
故障處理見[故障排除](../troubleshooting.md)。
