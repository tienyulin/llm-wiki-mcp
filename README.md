# LLM Wiki MCP

自動從 Markdown API 文檔生成結構化 Wiki，使用 Karpathy 風格的增量學習。

## 架構

```
Central Markdown Repo
      ↓ (CI: send markdowns)
wiki-processor (FastAPI)
      ↓ (LLM: analyze + merge)
Minio (wiki.json)
      ↓
mcp-server (HTTP API)
      ↓
Claude (query APIs)
```

## 組件

| 組件 | 功能 | Port |
|------|------|------|
| **wiki-processor** | FastAPI 服務，接收 markdown，調用 Minimax LLM | 8001 |
| **mcp-server** | HTTP API，提供工具查詢 wiki | 8002 |
| **Minio** | 對象存儲，存放 wiki.json 和快照 | 9000, 9001 |

## 快速開始

### 1. 準備環境

```bash
# 複製 .env 範例
cp .env-example .env

# 編輯 .env，填入你的 Minimax API key
nano .env
```

`.env` 內容（最重要的是 `MINIMAX_API_KEY`）：

```env
MINIMAX_API_KEY=your-key-here
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

### 2. 啟動服務

```bash
docker-compose up -d
```

服務已啟動：
- **Minio 控制台**：http://localhost:9001 (admin:minioadmin)
- **wiki-processor**：http://localhost:8001
- **mcp-server**：http://localhost:8002（HTTP API）

### 3. 測試

```bash
# wiki-processor 健康檢查
curl http://localhost:8001/health

# mcp-server 健康檢查
curl http://localhost:8002/health

# 查詢所有 API
curl http://localhost:8002/list_apis

# 搜尋 API
curl http://localhost:8002/search_apis?query=inventory
```

## 工作流程

### 1. 中央 Markdown Repo（GitLab CI）

```yaml
# .gitlab-ci.yml
update-wiki:
  script:
    - pip install httpx
    - python3 send_to_processor.py
  rules:
    - changes:
        - markdowns/**/*.md
```

詳見 [GITLAB_SETUP.md](GITLAB_SETUP.md)

### 2. Wiki Processor

- 接收 markdown 集合
- 與舊快照比較，偵測變化
- **首次運行**：調用 LLM 生成完整 wiki
- **增量更新**：LLM 只分析變化的文件，合併到現有 wiki
- 保存結果到 Minio

### 3. MCP Server（HTTP API）

通過 HTTP API 查詢 wiki：

```bash
# 列出所有 API（可依 module 過濾）
curl "http://localhost:8002/list_apis?module=inventory"

# 搜尋 API
curl "http://localhost:8002/search_apis?query=create"

# 取得 API 詳細資訊
curl "http://localhost:8002/get_api_detail?module=inventory&api_key=GET%20/inventory/{id}"

# Wiki 統計
curl http://localhost:8002/wiki_info
```

## 設定檔

| 檔案 | 用途 |
|------|------|
| `.env` | 環境變數（**不上傳**） |
| `.env-example` | 環境變數範例（提交） |
| `docker-compose.yml` | 服務編排 |
| `IMPLEMENTATION_GUIDE.md` | 完整部署指南 |
| `GITLAB_SETUP.md` | GitLab CI 設置 |

## API 端點

### wiki-processor（8001）

```
POST /process              處理 markdown，更新 wiki
GET  /status              查詢 wiki 統計
GET  /health              健康檢查
```

### mcp-server（8002，HTTP API）

```
GET /health                           健康檢查
GET /list_apis?module=""              列所有 API（可依 module 過濾）
GET /search_apis?query=""             關鍵字搜尋
GET /get_api_detail?module=&api_key=  取得詳細資訊
GET /wiki_info                        Wiki 統計
```

## 環境變數

```env
# Minimax API
MINIMAX_API_KEY=           # 必需，從 https://platform.minimaxi.com 取得

# Minio
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=wiki-data
MINIO_SECURE=false         # 若用 HTTPS 改為 true
```

## 開發

```bash
# 運行測試
cd wiki-processor && pytest tests/ -v
cd ../mcp-server && pytest tests/ http_api/test_http_api.py -v

# 語法檢查
python3 -m py_compile wiki-processor/main.py
python3 -m py_compile mcp-server/http_api/main.py
```

## 故障排除

### Processor 無法連線到 Minimax

```
❌ Minimax API error
```

**解決**：檢查 `.env` 中的 `MINIMAX_API_KEY` 是否正確。

### Minio 連線失敗

```
❌ Minio error: S3Error
```

**解決**：確認 Minio 已啟動：
```bash
docker-compose ps
curl http://localhost:9000/minio/health/live
```

### MCP Server 無法讀取 wiki

```
Wiki is empty.
```

**原因**：wiki.json 尚未生成。先執行 `/process` endpoint 創建它。

## 相關文檔

- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) — 完整架構與部署說明
- [GITLAB_SETUP.md](GITLAB_SETUP.md) — GitLab CI 集成步驟
- `examples/` — CI 配置範例

## 架構設計

### 三層式

```
Presentation  Service           Storage
─────────────────────────────────────────────
FastAPI       WikiProcessor     MinioStorage
MCP Server    WikiService       MinioReader
```

### 增量更新（Karpathy 風格）

- **首次**：LLM 分析全部 markdown → 生成 wiki
- **更新**：LLM 只看變化 + 現有 wiki → 合併結果

優勢：
- Token 成本線性增長（不是指數）
- 保持 wiki 語義連貫
- 與現有結構整合

## 測試覆蓋

- **wiki-processor**：12 tests（extract_json / detect_changes / API routes）
- **mcp-server**：23 tests（13 wiki_service + 10 http_api tests）

全部通過 ✅
