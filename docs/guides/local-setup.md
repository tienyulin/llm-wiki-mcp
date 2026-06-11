# 本地開發環境設置指南

在本地電腦上運行 LLM Wiki MCP 項目，無需 Docker。

## 系統要求

- **Python 3.11+** （項目代碼使用 3.11 特性）
- **pip** （Python 套件管理器，通常與 Python 一起安裝）
- **venv** （虛擬環境，通常內置於 Python）
- **Git** （用於克隆倉庫）
- **可選：Minimax API Key** （需要真實 LLM 功能）

### 檢查你的環境

```bash
# 檢查 Python 版本（需要 3.11+）
python3 --version
# 或
python --version

# 檢查 pip
pip --version

# 檢查 venv
python3 -m venv --help
```

---

## 安裝步驟

### 1. 克隆倉庫

```bash
git clone https://github.com/tienyulin/llm-wiki-mcp.git
cd llm-wiki-mcp
```

### 2. 創建虛擬環境

```bash
# 創建虛擬環境
python3 -m venv venv

# 激活虛擬環境
# 在 macOS/Linux：
source venv/bin/activate

# 在 Windows：
venv\Scripts\activate
```

### 3. 安裝依賴

首先，升級 pip：

```bash
pip install --upgrade pip
```

然後安裝兩個服務的依賴：

**wiki-processor 依賴：**
```bash
pip install -r wiki-processor/requirements.txt
```

**mcp-server 依賴：**
```bash
pip install -r mcp-server/requirements.txt
```

### 4. 配置環境變數

複製 `.env-example` 為 `.env` 並填入你的配置：

```bash
cp .env-example .env
```

編輯 `.env` 文件：

```env
# 必需：Minimax API Key（用於 LLM 功能）
# 如果沒有真實 key，可以使用 MOCK_LLM=true 進行測試
MINIMAX_API_KEY=sk-cp-xxxxxx...

# Minio 配置（本地開發用默認值即可）
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=wiki-data

# 可選：使用 Mock LLM（無需真實 API Key）
# MOCK_LLM=true

# 可選：/process 認證（生產環境建議啟用；不設定 = dev mode 不驗證）
# PROCESSOR_API_KEY=change-me

# 可選：mcp-server 限速（每 IP requests/sec；0 = 停用）
# RATE_LIMIT_RPS=0
```

> 啟用 `PROCESSOR_API_KEY` 後，所有對 `POST /process` 的呼叫都必須帶
> `X-API-Key` header（官方 CI template 與 `examples/send_to_processor.py`
> 會自動從同名環境變數帶上）。

---

## 啟動服務（3 種方式）

### 方式 A：使用 Docker Compose（推薦快速體驗）

最簡單的方式，包括 Minio：

```bash
docker-compose up -d
```

驗證服務：
```bash
curl http://localhost:8001/health   # wiki-processor
curl http://localhost:8002/health   # mcp-server
```

服務地址：
- **wiki-processor**：http://localhost:8001
- **mcp-server**：http://localhost:8002
- **Minio 控制台**：http://localhost:9001

### 方式 B：本地運行服務 + Docker Minio（推薦開發）

這種方式適合開發調試，Minio 用 Docker，Python 服務本地運行。

**第 1 步：啟動 Minio**
```bash
docker run -d \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio:latest \
  server /data --console-address ":9001"
```

**第 2 步：啟動 wiki-processor**

在一個終端中：
```bash
cd wiki-processor
# 可選：使用 Mock LLM（無需 API Key）
export MOCK_LLM=true
# 或使用真實 API Key：
export MINIMAX_API_KEY=sk-cp-xxxxx...

# 啟動服務
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**第 3 步：啟動 mcp-server**

在另一個終端中：
```bash
cd mcp-server
uvicorn http_api/main:app --host 0.0.0.0 --port 8002 --reload
```

驗證服務：
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### 方式 C：完全本地運行（包括 Minio）

需要額外安裝 Minio 本地服務（高級用戶）。

---

## 啟用向量索引（Postgres + pgvector，可選）

語意搜尋與大規模查詢加速（設計與實測見
`docs/architecture/vector-search.md`）。**不設定 `PG_DSN` 時系統行為與
原本完全相同**。

### Docker Compose（單一 pgvector 實例）

```bash
PG_DSN='postgresql://wiki:wikipass@pg:5432/wiki' \
MOCK_EMBEDDINGS=true \
docker compose --profile pg up -d
```

- `--profile pg` 啟動單一 `pgvector/pgvector:pg16` 實例；索引可選且可
  重建，PG 掛掉讀取自動 fallback、恢復後 reindex 即可，所以單實例足夠
- 客戶端已支援多主機 failover DSN，未來要上 HA 叢集只動 compose 與
  `PG_DSN`（見 `db/README.md`）
- 真實 embeddings：把 `MOCK_EMBEDDINGS` 改為 `false` 並設定
  `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY`（任何 OpenAI-compatible
  `/v1/embeddings`，見 `.env-example`）

### 本地開發（單節點 Postgres）

```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=pg -e POSTGRES_DB=wiki \
  pgvector/pgvector:pg16
# 兩個服務都帶上：
export PG_DSN='postgresql://postgres:pg@localhost:5432/wiki'
export MOCK_EMBEDDINGS=true
```

（沒有 Docker 時：`apt install postgresql-16 postgresql-16-pgvector` 也可。）

### 在既有資料上啟用（bootstrap）

wiki.json 已有資料時，啟用 PG 後做一次全量重建：

```bash
curl -X POST http://localhost:8001/admin/reindex \
  -H "X-API-Key: $PROCESSOR_API_KEY"
# {"status":"ok","apps":150,"entries":3000,"embedded":3000}
```

之後每次 `/process` 提交會自動增量同步。驗證：

```bash
curl http://localhost:8002/wiki_info            # vector_index 區塊
curl 'http://localhost:8002/semantic_search?query=inventory%20health&top_k=5'
```

---

## 驗證安裝

### 1. 檢查服務健康狀態

```bash
# wiki-processor 健康檢查
curl http://localhost:8001/health
# 預期回應：{"status":"ok","minio_connected":true,"minimax_accessible":true}

# mcp-server 健康檢查
curl http://localhost:8002/health
# 預期回應：{"status":"ok"}
```

### 2. 運行單元測試

```bash
# 測試 wiki-processor
cd wiki-processor
pytest tests/ -v

# 測試 mcp-server
cd ../mcp-server
pytest tests/ -v
```

### 3. 測試完整工作流

```bash
# 發送 Markdown 給 wiki-processor（使用 Mock LLM）
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{
    "markdowns": {
      "test.md": "# Test API\n## GET /test\nTest endpoint"
    },
    "timestamp": "2026-05-09T10:00:00Z",
    "trigger_info": {"source": "test"}
  }'

# 預期回應：{"status":"success",...}

# 查詢 Wiki
curl http://localhost:8002/wiki_info
```

---

## 開發工作流

### 修改代碼並重啟服務

由於啟動時使用了 `--reload` 標誌，修改 Python 文件後會自動重啟：

```bash
# 修改文件（例如 wiki-processor/services/llm.py）
# 保存後，服務會自動重啟
# 你會看到 "Application startup complete" 的消息
```

### 調試

如果使用 Mock LLM 進行開發：

```bash
# 在 .env 中設置
MOCK_LLM=true

# 或在啟動時設置
export MOCK_LLM=true
```

Mock 模式不需要真實 API Key，適合開發和測試。

### 使用 IDE 進行調試

如果使用 VS Code 或 PyCharm，可以設置調試器：

**VS Code launch.json 示例：**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "wiki-processor",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--host", "0.0.0.0", "--port", "8001"],
      "cwd": "${workspaceFolder}/wiki-processor",
      "jinja": true
    }
  ]
}
```

---

## 常見問題

### Q: 我沒有 Minimax API Key

**A:** 有兩個選擇：

1. **使用 Mock LLM**（推薦開發）：
   ```bash
   export MOCK_LLM=true
   uvicorn main:app --port 8001 --reload
   ```

2. **從 Minimax 獲取 API Key**：
   - 訪問 https://platform.minimax.io
   - 創建帳戶並獲取 API Key
   - 記得配置 API Key 的白名單（見下方）

### Q: 403 Host not in allowlist

**A:** 這表示你的 API Key 配置了主機限制。解決方法：

1. 登錄 Minimax 平台
2. 找到 API Key 設置
3. 在 Host Allowlist 中添加 `*` 或當前 IP

### Q: 無法連接 Minio

**A:** 確保 Minio 正在運行：

```bash
# 如果使用 Docker：
docker ps | grep minio

# 如果手動啟動，檢查端口是否在監聽：
netstat -an | grep 9000
```

### Q: Python 版本不對

**A:** 檢查並升級 Python：

```bash
python3 --version  # 需要 3.11+

# 如果沒有 Python 3.11：
# - macOS: brew install python@3.11
# - Linux: apt-get install python3.11
# - Windows: 從 python.org 下載
```

### Q: pip 安裝失敗（SSL 錯誤）

**A:** 使用 `--trusted-host` 標誌：

```bash
pip install --trusted-host pypi.python.org \
            --trusted-host pypi.org \
            --trusted-host files.pythonhosted.org \
            -r wiki-processor/requirements.txt
```

---

## 下一步

- **理解數據結構**：見 [API_SCHEMA.md](API_SCHEMA.md)
- **修改代碼**：見 [DEVELOPMENT.md](DEVELOPMENT.md)
- **遇到問題**：見 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **GitLab CI 集成**：見 [GITLAB_SETUP.md](GITLAB_SETUP.md)

---

## 環境變數參考

| 變數 | 必需 | 默認值 | 說明 |
|------|------|--------|------|
| `MINIMAX_API_KEY` | 否 | 無 | Minimax LLM API 密鑰（若使用真實 API） |
| `MOCK_LLM` | 否 | false | 使用 Mock LLM（true/false），用於測試 |
| `MINIO_ENDPOINT` | 否 | minio:9000 | Minio 服務地址 |
| `MINIO_ACCESS_KEY` | 否 | minioadmin | Minio 訪問密鑰 |
| `MINIO_SECRET_KEY` | 否 | minioadmin | Minio 秘密密鑰 |
| `MINIO_BUCKET` | 否 | wiki-data | Minio 存儲桶名稱 |

---

## 故障排除

如果遇到任何問題，請參考 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
