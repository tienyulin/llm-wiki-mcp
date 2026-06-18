# API Schema 和 Wiki 數據結構

完整的 Wiki JSON 數據結構說明和示例。

## Wiki JSON 結構概述

Wiki 系統的核心數據存儲在 **Minio** 中的 `wiki.json` 文件。該文件包含所有提取的 API 端點和元數據。

```json
{
  "apis": {
    "module_name": {
      "METHOD /path": {
        "method": "GET|POST|PUT|DELETE|PATCH",
        "path": "/endpoint/{id}",
        "description": "簡短描述",
        "parameters": [...],
        "response": {...}
      }
    }
  },
  "metadata": {
    "version": "1.0",
    "modules": ["module1", "module2"],
    "updated_at": "2026-05-09T10:00:00Z"
  }
}
```

---

## 完整示例

### 實際的 wiki.json 示例

```json
{
  "apis": {
    "inventory": {
      "GET /inventory": {
        "method": "GET",
        "path": "/inventory",
        "description": "取得所有庫存項目",
        "parameters": [
          {
            "name": "limit",
            "type": "integer",
            "description": "最多返回筆數 (預設 10)"
          },
          {
            "name": "offset",
            "type": "integer",
            "description": "分頁起始位置 (預設 0)"
          }
        ],
        "response": {
          "type": "object",
          "properties": {
            "items": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "id": {"type": "string"},
                  "name": {"type": "string"},
                  "quantity": {"type": "integer"}
                }
              }
            }
          }
        }
      },
      "POST /inventory": {
        "method": "POST",
        "path": "/inventory",
        "description": "創建新的庫存項目",
        "parameters": [],
        "request_body": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "quantity": {"type": "integer"},
            "unit": {"type": "string"}
          },
          "required": ["name", "quantity"]
        }
      },
      "GET /inventory/{id}": {
        "method": "GET",
        "path": "/inventory/{id}",
        "description": "取得單個庫存項目的詳細資訊",
        "parameters": [
          {
            "name": "id",
            "type": "string",
            "location": "path",
            "description": "物品 ID"
          }
        ]
      },
      "PUT /inventory/{id}": {
        "method": "PUT",
        "path": "/inventory/{id}",
        "description": "更新庫存項目"
      },
      "DELETE /inventory/{id}": {
        "method": "DELETE",
        "path": "/inventory/{id}",
        "description": "刪除庫存項目"
      }
    },
    "order": {
      "GET /orders": {
        "method": "GET",
        "path": "/orders",
        "description": "取得所有訂單",
        "parameters": [
          {
            "name": "status",
            "type": "string",
            "description": "訂單狀態 (pending, confirmed, shipped, delivered)"
          }
        ]
      },
      "POST /orders": {
        "method": "POST",
        "path": "/orders",
        "description": "建立新訂單",
        "request_body": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "string"},
            "items": {"type": "array"},
            "delivery_address": {"type": "string"}
          }
        }
      },
      "GET /orders/{id}": {
        "method": "GET",
        "path": "/orders/{id}",
        "description": "取得訂單詳細資訊"
      }
    }
  },
  "metadata": {
    "version": "1.0",
    "modules": ["inventory", "order"],
    "updated_at": "2026-05-09T10:00:00Z",
    "created_at": "2026-05-09T09:00:00Z",
    "total_endpoints": 8
  }
}
```

---

## API 條目字段說明

### 頂級結構

| 字段 | 類型 | 說明 |
|------|------|------|
| `apis` | object | 按模組分組的所有 API 端點 |
| `concepts` | object | 跨應用概念合成（由 `/admin/rebuild-concepts` 產生）。`{概念名: {description, related, apps}}` |
| `overviews` | object | 每個應用的總覽（每次 ingest 更新）。`{app: {text, updated_at}}` |
| `metadata` | object | Wiki 的元數據 |

### APIs 結構

```
apis: {
  "module_name": {
    "METHOD /path": { API Entry }
  }
}
```

- **module_name**：模組名稱（如 "inventory", "order"）
- **METHOD /path**：API 鍵值（如 "GET /users", "POST /orders/{id}"）

### API Entry（API 條目）

| 字段 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `method` | string | ✅ | HTTP 方法：GET, POST, PUT, DELETE, PATCH |
| `path` | string | ✅ | API 路徑（如 /users/{id}） |
| `description` | string | ✅ | API 功能描述 |
| `sources` | array | ✅ | 此條目萃取自哪些 markdown 檔（溯源） |
| `source_app` | string | ✅ | 來源應用（由處理器標記，非 LLM 輸出） |
| `source_version` | string | ✅ | 來源版本 / commit |
| `parameters` | array | ❌ | 查詢參數或路由參數 |
| `request_body` | object | ❌ | 請求體的 JSON Schema |
| `response` | object | ❌ | 回應的 JSON Schema |
| `status_codes` | object | ❌ | 可能的 HTTP 狀態碼 |
| `authentication` | string | ❌ | 認證方式（如 "Bearer Token"） |

### Parameters（參數）

```json
{
  "name": "limit",
  "type": "integer",
  "location": "query",
  "description": "最多返回筆數",
  "default": 10,
  "required": false
}
```

| 字段 | 說明 |
|------|------|
| `name` | 參數名稱 |
| `type` | 數據類型（string, integer, boolean, array, object） |
| `location` | 參數位置（query, path, header, body） |
| `description` | 參數說明 |
| `default` | 默認值（可選） |
| `required` | 是否必需（可選） |

### JSON Schema（request_body, response）

遵循 JSON Schema 標準：

```json
{
  "type": "object",
  "properties": {
    "field_name": {
      "type": "string|integer|boolean|array|object",
      "description": "字段描述"
    }
  },
  "required": ["field_name"]
}
```

### Metadata（元數據）

| 字段 | 類型 | 說明 |
|------|------|------|
| `version` | string | Wiki 版本（如 "1.0"） |
| `modules` | array | 所有模組名稱列表 |
| `updated_at` | string | 最後更新時間（ISO 8601） |
| `created_at` | string | 創建時間（ISO 8601） |
| `total_endpoints` | integer | API 端點總數 |

---

## 數據流圖

```
┌──────────────────────┐
│   Markdown Files     │
│ (API documentation) │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   wiki-processor     │
│ (FastAPI service)   │
│ - Detects changes    │
│ - Calls Minimax LLM  │
│ - Parses JSON        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Minio Storage     │
│   (Object storage)   │
│ - wiki.json          │
│ - snapshot.json      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│     mcp-server       │
│  (HTTP API server)   │
│ - /list_apis         │
│ - /search_apis       │
│ - /get_api_detail    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   AI Client (Claude) │
│  Query & use APIs    │
└──────────────────────┘
```

---

## Markdowns Snapshot 結構

系統會在 Minio 中存儲 `markdowns_snapshot.json`，用於追蹤文件變更。

```json
{
  "inventory-api.md": "# Inventory API\n\n## GET /inventory\n...",
  "order-api.md": "# Order API\n\n## GET /orders\n...",
  "payment-api.md": "# Payment API\n..."
}
```

**用途：**
- 檢測新增、修改、刪除的文件
- 支持增量更新（只處理變化的文件）
- 保持歷史記錄

---

## API 條目的最小和完整示例

### 最小示例（只有必需字段）

```json
{
  "method": "GET",
  "path": "/users",
  "description": "取得所有用戶"
}
```

### 完整示例（包含所有可選字段）

```json
{
  "method": "POST",
  "path": "/users",
  "description": "創建新用戶",
  "parameters": [
    {
      "name": "notify",
      "type": "boolean",
      "location": "query",
      "description": "是否發送通知",
      "default": true
    }
  ],
  "request_body": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "email": {"type": "string"},
      "age": {"type": "integer"}
    },
    "required": ["name", "email"]
  },
  "response": {
    "type": "object",
    "properties": {
      "id": {"type": "string"},
      "name": {"type": "string"},
      "email": {"type": "string"},
      "created_at": {"type": "string"}
    }
  },
  "status_codes": {
    "201": "用戶創建成功",
    "400": "請求驗證失敗",
    "409": "郵箱已存在"
  },
  "authentication": "Bearer Token"
}
```

---

## 如何從 Wiki 查詢數據

### 使用 MCP Server API

**列出所有 API：**
```bash
curl http://localhost:8002/list_apis
```

回應示例：
```json
{
  "modules": {
    "inventory": [
      "GET /inventory",
      "POST /inventory",
      "GET /inventory/{id}",
      "PUT /inventory/{id}",
      "DELETE /inventory/{id}"
    ],
    "order": [
      "GET /orders",
      "POST /orders",
      "GET /orders/{id}"
    ]
  }
}
```

**按模組篩選：**
```bash
curl "http://localhost:8002/list_apis?module=inventory"
```

**搜尋 API：**
```bash
curl "http://localhost:8002/search_apis?query=inventory"
```

回應示例：
```json
{
  "results": [
    {
      "module": "inventory",
      "api_key": "GET /inventory",
      "description": "取得所有庫存項目"
    }
  ],
  "count": 1
}
```

**獲取 API 詳細資訊：**
```bash
curl "http://localhost:8002/get_api_detail?module=inventory&api_key=GET%20/inventory"
```

> 注意：`/get_api_detail` 的 `module` 與 `api_key` 都是必填參數，
> 缺少任一個會回傳 422。

**Wiki 統計：**
```bash
curl http://localhost:8002/wiki_info
```

回應示例：
```json
{
  "modules": 2,
  "total_endpoints": 8,
  "metadata": {
    "version": "1.0",
    "modules": ["inventory", "order"],
    "updated_at": "2026-05-09T10:00:00Z"
  }
}
```

---

### Wiki Schema v2（2026-06-11）

頂層結構新增 `schema_version: 2`，且每個 API entry 帶有 processor 蓋章的
provenance 欄位（LLM 輸出不被信任）：

```json
{
  "schema_version": 2,
  "apis": {
    "inventory": {
      "GET /inventory": {
        "method": "GET",
        "path": "/inventory",
        "description": "...",
        "source_app": "app-inventory",
        "source_version": "a1b2c3d"
      }
    }
  },
  "metadata": {"version": "1.0", "created_at": "...", "updated_at": "..."}
}
```

v1 的混合形態（wiki 中夾帶 `"file.md": "<markdown>"` 條目）已移除；
舊資料讀取時自動遷移（詳見 `docs/architecture/concurrency.md`）。

### wiki-processor 端點行為（2026-06-11 更新）

**`POST /process` 認證：**
- 設定 `PROCESSOR_API_KEY` 後，請求須帶 `X-API-Key` header，否則回 **401**
- 未設定時為 dev mode（不驗證，啟動時記 warning）

**`POST /process` 輸入驗證：**
- `markdowns` 不可為空 dict —— 空的 `markdowns` 會回傳 **422 Unprocessable Entity**
- 並發提交安全：兩階段更新 + MinIO ETag 條件寫入（多副本安全，詳見
  `docs/architecture/concurrency.md`）

**mcp-server rate limiting：**
- 設定 `RATE_LIMIT_RPS` > 0 後，單一 client IP 超過限速回 **429**
  （含 `Retry-After` header）；`/health` 豁免

**快取一致性：**
- mcp-server 讀取端點（`/list_apis`、`/search_apis`、`/get_api_detail`、
  `/wiki_info`）經由 TTL 快取（預設 1 小時）讀取 wiki
- wiki-processor 在每次成功更新後呼叫 mcp-server 的
  `POST /cache/invalidate`（透過 `MCP_SERVER_URL` 環境變數）主動失效快取
- `POST /cache/invalidate` 帶 `{"source_app": "app-x"}` 時以 key segment
  精確比對失效；不帶 `source_app` 時清空全部快取

---

## 向量索引端點（2026-06-11，PG + pgvector）

設計與實測數據見 `docs/architecture/vector-search.md`。`PG_DSN` 未設定時
以下行為全部自動退回原有 wiki.json 路徑。

**`GET /semantic_search?query=...&top_k=10`（mcp-server，新端點）：**

```json
{
  "results": [
    {
      "module": "inventory",
      "api_key": "GET /inventory/health",
      "description": "Inventory health check",
      "source_app": "app-inventory",
      "score": 0.6202
    }
  ],
  "count": 1,
  "mode": "semantic"
}
```

- `score` = cosine 相似度（僅 `mode: "semantic"` 時存在）
- `top_k` 上限 50；空 query 回 **400**
- PG 或 embeddings 不可用時降級為關鍵字搜尋並回 `"mode": "keyword_fallback"`
  （不回 5xx）

**`GET /search_apis` 新增 `mode` 欄位**（結果項目形狀不變，向後相容）：
- `"pg_keyword"` — PG trigram 索引查詢
- `"wiki_scan"` — 原本的 cached-wiki 掃描（fallback）

**`GET /wiki_info` 新增 `vector_index` 區塊：**

```json
{
  "vector_index": {
    "available": true,
    "semantic_search": true,
    "entries": 168,
    "embedded": 168,
    "last_updated_at": "2026-06-11T11:49:05+00:00",
    "last_sync": {"source_app": "app-x", "synced_at": "...", "entries": 4}
  }
}
```

PG 停用或不可達時為 `{"available": false}`。`last_sync.synced_at` 對照
`metadata.updated_at` 可偵測 wiki↔PG 漂移。

---

## 概念、總覽、技能、知識圖譜端點（2026-06-18）

採用自 nashsu/llm_wiki 與 VectifyAI/OpenKB。萃取改為兩段式（analyze → generate），
每個 API 條目帶 `sources` 溯源。

**wiki-processor（admin，受 `X-API-Key` 保護）：**
- `POST /admin/recompile` — 以已存的 per-app snapshot 重新萃取（不需重新 ingest），
  用於萃取 / prompt 變更後刷新。回 `{recompiled_apps, count}`。
- `POST /admin/rebuild-concepts` — 對整個 wiki 做跨應用概念合成，寫入 `wiki.concepts`。
  整庫掃描（如 reindex），非每次 ingest 觸發。回 `{concepts: N}`。

**mcp-server（讀取，皆讀 cached wiki.json）：**
- `GET /list_concepts` → `{concepts: {名稱: {description, apps, related_count}}}`
- `GET /get_concept?name=` → `{concept: {description, related, apps}}` 或 404
- `GET /get_overview?app=` → `{overview: {text, updated_at}}` 或 404
- `GET /skill?name=` → 將 wiki 打包為 Anthropic Skill 資料夾
  `{files: {"<name>/SKILL.md": ..., "<name>/references/concepts.md": ...}}`
- `GET /graph` → `{nodes, edges}`；edge kind：`shared_source`（4.0）、`concept`（3.0）

**`POST /admin/reindex`（wiki-processor，新端點，受 `X-API-Key` 保護）：**

從 wiki.json 全量重建 PG 索引（首次啟用 PG 的 bootstrap、漂移修復）。
回應：`{"status": "ok", "apps": 150, "entries": 3000, "embedded": 3000}`。
`PG_DSN` 未設定時回 **503**。

**`GET /health`（wiki-processor）新增欄位：**
`vector_index_connected`（PG 可達）、`embeddings_configured`（embedding
provider 已設定或 mock）。

---

## 修改 Wiki 結構

### 添加新 API 字段

如果想在 API 條目中添加新字段（如 `deprecated`, `rate_limit`），可以：

1. **修改 LLM 提示**（見 [DEVELOPMENT.md](DEVELOPMENT.md)）
2. **更新 wiki-processor/services/processor.py** 中的 LLM 提示
3. **新 wiki.json 會包含新字段**

### 修改模組分組邏輯

模組分組由 LLM 自動決定。要自定義模組分組：

1. 編輯 **wiki-processor/services/llm.py**
2. 修改 `generate_wiki()` 和 `update_wiki()` 中的提示
3. 指定模組的命名規則

---

## JSON Schema 驗證

Wiki.json 應該通過以下 JSON Schema 驗證：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["apis", "metadata"],
  "properties": {
    "apis": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": {
          "type": "object",
          "required": ["method", "path", "description"],
          "properties": {
            "method": {"type": "string"},
            "path": {"type": "string"},
            "description": {"type": "string"},
            "parameters": {"type": "array"},
            "request_body": {"type": "object"},
            "response": {"type": "object"}
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "version": {"type": "string"},
        "modules": {"type": "array"},
        "updated_at": {"type": "string"}
      }
    }
  }
}
```

---

## 常見模式

### 分頁 API

```json
{
  "parameters": [
    {"name": "page", "type": "integer", "default": 1},
    {"name": "limit", "type": "integer", "default": 20}
  ]
}
```

### 過濾和排序

```json
{
  "parameters": [
    {"name": "status", "type": "string", "description": "過濾狀態"},
    {"name": "sort_by", "type": "string", "description": "排序字段"},
    {"name": "order", "type": "string", "description": "升序/降序"}
  ]
}
```

### 批量操作

```json
{
  "method": "POST",
  "path": "/items/batch",
  "description": "批量創建項目",
  "request_body": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"}
          }
        }
      }
    }
  }
}
```

---

## 相關文檔

- **[LOCAL_SETUP.md](LOCAL_SETUP.md)** - 如何在本地運行項目
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - 如何修改 Wiki 結構和 LLM 提示
- **[README.md](README.md)** - 項目概述
