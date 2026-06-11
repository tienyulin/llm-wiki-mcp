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

### wiki-processor 端點行為（2026-06-11 更新）

**`POST /process` 輸入驗證：**
- `markdowns` 不可為空 dict —— 空的 `markdowns` 會回傳 **422 Unprocessable Entity**
- 並發提交安全：processor 內部以 asyncio.Lock 序列化更新（詳見
  `docs/architecture/concurrency.md`）

**快取一致性：**
- mcp-server 讀取端點（`/list_apis`、`/search_apis`、`/get_api_detail`、
  `/wiki_info`）經由 TTL 快取（預設 1 小時）讀取 wiki
- wiki-processor 在每次成功更新後呼叫 mcp-server 的
  `POST /cache/invalidate`（透過 `MCP_SERVER_URL` 環境變數）主動失效快取
- `POST /cache/invalidate` 帶 `{"source_app": "app-x"}` 時以 key segment
  精確比對失效；不帶 `source_app` 時清空全部快取

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
