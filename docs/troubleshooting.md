# 故障排除指南

常見問題和解決方案。

## Docker 相關問題

### 容器無法啟動

**症狀：** `docker-compose up` 時容器立即退出

**診斷：**
```bash
# 查看容器日誌
docker-compose logs wiki-processor
docker-compose logs mcp-server
docker-compose logs wiki-minio
```

**常見原因和解決方案：**

| 問題 | 症狀 | 解決方案 |
|------|------|--------|
| Port 已被占用 | `Address already in use` | 改變 docker-compose.yml 中的 port，或停止占用 port 的進程 |
| 依賴未安裝 | `ModuleNotFoundError` | 確保 Dockerfile 包含所有 requirements.txt |
| 環境變數缺失 | `KeyError` | 檢查 .env 文件是否存在和完整 |
| 磁盤空間不足 | `No space left` | 清理 Docker 資源：`docker system prune` |

### Port 已被占用

**症狀：**
```
bind: address already in use
```

**解決方案：**

```bash
# 查找占用 port 的進程
# macOS/Linux
lsof -i :8001
lsof -i :8002
lsof -i :9000

# Windows
netstat -ano | findstr :8001

# 終止進程
# macOS/Linux
kill -9 <PID>

# 或改變 docker-compose.yml 中的 port
ports:
  - "8011:8001"  # 改為 8011
  - "8022:8002"  # 改為 8022
```

### DNS 解析失敗

**症狀：** 容器內無法訪問 `api.minimax.io`
```
[Errno -5] No address associated with hostname
```

**解決方案：** 確認 docker-compose.yml 有 DNS 配置：

```yaml
dns:
  - 8.8.8.8      # Google DNS
  - 8.8.4.4      # Google DNS 備用
```

---

## Minimax API 問題

### 403 Host not in allowlist

**症狀：**
```
Client error '403 Forbidden' for url 'https://api.minimax.io/v1/text/chatcompletion_v2'
Response: Host not in allowlist
```

**原因：** API Key 被限制為特定主機/IP 訪問

**解決方案：**

1. **登錄 Minimax 平台**：https://platform.minimax.io
2. **找到 API Key 設定**
3. **添加白名單：**
   - 設置為 `*` （允許所有）
   - 或添加你的 IP 地址

4. **驗證：**
   ```bash
   # 重新測試 API
   docker-compose restart wiki-processor
   # 檢查日誌
   docker-compose logs wiki-processor | grep -i minimax
   ```

### API Key 格式錯誤

**症狀：**
```
401 Unauthorized
```

**檢查清單：**

```bash
# 1. 檢查 API Key 是否存在
cat .env | grep MINIMAX_API_KEY

# 2. 檢查容器是否收到 API Key
docker-compose exec wiki-processor env | grep MINIMAX_API_KEY

# 3. 驗證 API Key 格式（應以 sk-cp- 開頭）
# 示例：sk-cp-XEdjRvCpNzR46Gzv0kdUi...
```

### 配額用完/限流

**症狀：**
```
429 Too Many Requests
或 402 Payment Required
```

**解決方案：**

1. **檢查 Minimax 帳戶配額**：https://platform.minimax.io
2. **使用 Mock LLM 進行開發**：
   ```bash
   export MOCK_LLM=true
   docker-compose up
   ```
3. **升級帳戶或購買更多配額**

### 網絡超時

**症狀：**
```
TimeoutError: ('Connection aborted.', RemoteDisconnected(...))
```

**解決方案：**

```bash
# 1. 檢查網絡連接
ping api.minimax.io

# 2. 檢查防火牆
# 確保允許訪問 https://api.minimax.io

# 3. 增加超時時間
# 編輯 wiki-processor/services/llm.py，修改 timeout=60.0
```

---

## Wiki 生成失敗

### LLM 返回無效 JSON

**症狀：**
```
json.JSONDecodeError: Expecting value
或 Unexpected error during processing: ...
```

**原因：** LLM 返回的不是有效的 JSON

**解決方案：**

1. **檢查 LLM 日誌：**
   ```bash
   docker-compose logs wiki-processor | tail -50
   ```

2. **測試 LLM 連接：**
   ```bash
   # 在容器內測試
   docker-compose exec wiki-processor python3 << 'EOF'
   import httpx
   import os
   
   api_key = os.getenv("MINIMAX_API_KEY")
   response = httpx.post(
     "https://api.minimax.io/v1/text/chatcompletion_v2",
     headers={"Authorization": f"Bearer {api_key}"},
     json={
       "model": "MiniMax-M2.7",
       "messages": [{"role": "user", "content": "test"}],
     },
     verify=False
   )
   print(f"Status: {response.status_code}")
   print(f"Response: {response.text[:200]}")
   EOF
   ```

3. **使用 Mock LLM：**
   ```bash
   export MOCK_LLM=true
   docker-compose up
   ```

### Minio 寫入失敗

**症狀：**
```
Minio error: S3Error
或 Failed to save wiki.json to Minio
```

**診斷：**

```bash
# 1. 檢查 Minio 健康狀態
curl http://localhost:9000/minio/health/live

# 2. 檢查 Minio 日誌
docker-compose logs wiki-minio | tail -20

# 3. 驗證 Minio 連接
docker-compose exec wiki-processor python3 << 'EOF'
from minio import Minio
client = Minio("minio:9000", access_key="minioadmin", secret_key="minioadmin")
print("✓ Minio connected!")
EOF
```

**解決方案：**

```bash
# 1. 重啟 Minio
docker-compose restart wiki-minio
sleep 5

# 2. 檢查磁盤空間
docker system df

# 3. 清理 Minio 數據（謹慎！會刪除所有 wiki 數據）
docker-compose down -v
docker-compose up -d
```

### 磁盤空間不足

**症狀：**
```
No space left on device
```

**解決方案：**

```bash
# 1. 檢查磁盤使用情況
df -h

# 2. 清理 Docker 資源
docker system prune -a
docker volume prune

# 3. 如果仍然不足，增加分區大小或刪除其他文件
```

---

## MCP Server 問題

### Wiki 為空

**症狀：**
```bash
curl http://localhost:8002/list_apis
# 回應：{"detail":"Wiki is empty"}
```

**原因：** wiki.json 尚未生成

**解決方案：**

1. **發送 Markdown 給 wiki-processor：**
   ```bash
   curl -X POST http://localhost:8001/process \
     -H "Content-Type: application/json" \
     -d '{
       "markdowns": {
         "test.md": "# Test API\n## GET /test\nTest endpoint"
       },
       "timestamp": "2026-05-09T10:00:00Z",
       "trigger_info": {"source": "test"}
     }'
   ```

2. **驗證處理：**
   ```bash
   curl http://localhost:8001/status
   # 應該返回 wiki_size > 0
   ```

3. **檢查 Minio 中是否存在 wiki.json：**
   ```bash
   # 登錄 Minio 控制台：http://localhost:9001
   # 或使用命令行
   docker-compose exec wiki-minio mc ls minio/wiki-data/
   ```

### 搜尋返回 0 結果

**症狀：**
```bash
curl "http://localhost:8002/search_apis?query=test"
# 回應：{"results":[],"count":0}
```

**原因：** Wiki 中沒有匹配的 API

**解決方案：**

1. **列出所有 API 檢查是否存在：**
   ```bash
   curl http://localhost:8002/list_apis
   ```

2. **嘗試搜尋已知 API：**
   ```bash
   # 首先生成 wiki，然後搜尋
   curl "http://localhost:8002/search_apis?query=GET"
   ```

3. **檢查搜尋關鍵字：**
   - 搜尋區分大小寫嗎？（通常不區分）
   - 是否在 API 描述中？

### 編碼問題（亂碼）

**症狀：** 返回的中文字符顯示為亂碼

**解決方案：**

```bash
# 1. 確保使用 UTF-8 編碼
export PYTHONIOENCODING=utf-8

# 2. 驗證 wiki.json 的編碼
file wiki-data/wiki.json
# 應該是 UTF-8

# 3. 重新生成 wiki
docker-compose restart wiki-processor
```

---

## 本地開發問題

### 導入模塊失敗

**症狀：**
```
ModuleNotFoundError: No module named 'fastapi'
```

**解決方案：**

```bash
# 1. 確認在正確的虛擬環境中
which python
# 應該顯示 venv/bin/python

# 2. 重新安裝依賴
pip install -r wiki-processor/requirements.txt

# 3. 檢查 Python 版本
python --version  # 需要 3.11+
```

### 修改代碼後未生效

**症狀：** 修改了代碼，但 uvicorn 服務沒有重新加載

**解決方案：**

```bash
# 1. 確認使用了 --reload 標誌
uvicorn main:app --reload

# 2. 檢查文件是否真的被保存
# IDE 設置 → 自動保存

# 3. 手動重啟服務
# Ctrl+C 停止，然後重新啟動
```

---

## 網絡和連接問題

### 無法連接本地服務

**症狀：**
```
Connection refused
或 Failed to connect to localhost:8001
```

**診斷：**

```bash
# 1. 檢查服務是否在運行
ps aux | grep uvicorn
# 或
docker-compose ps

# 2. 檢查端口
netstat -an | grep 8001

# 3. 測試連接
curl -v http://localhost:8001/health
```

### 跨域 CORS 問題

**症狀：** 瀏覽器控制台出現 CORS 錯誤

**原因：** mcp-server 未配置 CORS

**解決方案：** 見 [DEVELOPMENT.md](DEVELOPMENT.md) 的 FastAPI 設置部分

---

## 調試技巧

### 啟用詳細日誌

**wiki-processor：**
```bash
export PYTHONUNBUFFERED=1
uvicorn main:app --log-level debug
```

**mcp-server：**
```bash
export PYTHONUNBUFFERED=1
uvicorn http_api/main:app --log-level debug
```

### 使用 Python 交互式調試

```bash
# 在 Python REPL 中測試（從 wiki-processor 目錄執行）
python3
>>> from services.llm import LLMConfig, LLMProviderFactory
>>> config = LLMConfig(provider="minimax", api_key="...", model="MiniMax-M2.7")
>>> llm = LLMProviderFactory.create(config)
>>> # 測試代碼
```

### 檢查環境變數

```bash
# 本地運行時
env | grep MINIMAX
env | grep MINIO

# Docker 容器中
docker-compose exec wiki-processor env | grep MINIMAX
```

---

## Schema v2 遷移與認證（2026-06-11）

### 症狀：`POST /process` 回 401

`PROCESSOR_API_KEY` 已設定但請求未帶（或帶錯）`X-API-Key` header。
CI 端把 `PROCESSOR_API_KEY` 設為 masked variable 即可（官方 template 與
`send_to_processor.py` 會自動帶上）。本地開發可不設定該變數（dev mode）。

### 症狀：升級後 wiki 中的舊文件條目消失

v2 schema 移除了 v1 的 file-map 條目（`"file.md": "<markdown>"` 形態）。
首次更新時 processor 會 lazy 遷移：保留結構化的 `apis`，丟棄 file-map
條目並記 warning。受影響的應用在下一次 CI 提交時自動重建自己的 entries。

### 症狀：mcp-server 查詢回 429

`RATE_LIMIT_RPS` 已啟用且超過限速。回應帶 `Retry-After: 1`；
調高該值或設為 0 停用。

---

## 並發更新問題（2026-06-11 修復）

### 症狀：多個應用同時提交時，部分更新遺失

**原因：** `WikiProcessor.process()` 的 read-modify-write 流程橫跨一次 awaited
LLM 呼叫。在修復前，並發請求會讀到相同的 wiki 狀態並互相覆蓋（lost update）。
實測 20 個並發更新只有 1 個存活。

**修復（v2，現行）：** 兩階段更新 —— LLM 呼叫完全並行，merge+寫入走
MinIO ETag 條件寫入（CAS loop）+ 進程內小鎖。**多副本部署安全**。
回歸測試：`wiki-processor/tests/test_concurrency.py`（含 CAS 衝突注入）。
詳見 `docs/architecture/concurrency.md`。

### 症狀：第二次起的 app-level 更新都回傳 `status: failed`

**原因：** app-level merge 對 wiki 中的 dict 值（`apis`/`metadata` 等結構化
條目）呼叫字串方法導致 `AttributeError`。已加上 `isinstance(content, str)`
防護；空的 `markdowns` 現在也會在 API 層被擋下（422）。

### 症狀：wiki 更新後 mcp-server 查到舊資料

**原因：** mcp-server 讀取路徑帶有 TTL 快取（1 小時）。wiki-processor 在每次
成功更新後會呼叫 mcp-server 的 `POST /cache/invalidate` 主動失效；此行為
需要設定 `MCP_SERVER_URL` 環境變數（docker-compose 已預設
`http://mcp-server:8002`）。未設定時快取只能等 TTL 過期。

---

## 在沒有 Docker 的環境執行測試

CI 或雲端沙箱可能沒有 docker daemon。可以用本地 MinIO binary + uvicorn 取代
docker-compose：

```bash
# 1. 下載並啟動 MinIO
curl -fsSL https://dl.min.io/server/minio/release/linux-amd64/minio -o ~/minio
chmod +x ~/minio
MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin \
  ~/minio server ~/minio-data --address :9000 &

# 2. 啟動兩個服務
cd wiki-processor
MOCK_LLM=true LLM_API_KEY=test-key MINIO_ENDPOINT=localhost:9000 \
  MCP_SERVER_URL=http://localhost:8002 uvicorn main:app --port 8001 &
cd ../mcp-server
MINIO_ENDPOINT=localhost:9000 uvicorn http_api.main:app --port 8002 &

# 3. 執行整合測試
cd ..
python tests/integration/test_docker_integration.py
```

單元測試完全不需要外部服務（conftest.py 會 stub Minio 並設定 MOCK_LLM）：

```bash
cd wiki-processor && python -m pytest tests/
cd mcp-server && python -m pytest
```

---

## 獲取幫助

如果問題未在本指南中列出：

1. **檢查服務日誌**：
   ```bash
   docker-compose logs -f <service_name>
   ```

2. **查看項目文檔**：
   - [README.md](README.md) - 項目概述
   - [LOCAL_SETUP.md](LOCAL_SETUP.md) - 本地設置
   - [API_SCHEMA.md](API_SCHEMA.md) - 數據結構
   - [DEVELOPMENT.md](DEVELOPMENT.md) - 開發指南

3. **查看代碼中的註釋和 docstrings**

4. **運行測試：**
   ```bash
   pytest -v
   ```

---

## 向量索引（PG + pgvector）問題

### PG 掛了 / 連不上，查詢還能用嗎？

能。這是設計保證：mcp-server 每個讀取端點在 PG 出錯或回空時自動退回
cached-wiki 路徑（`/search_apis` 回應的 `mode` 欄位會顯示 `wiki_scan`），
circuit breaker（`PG_RETRY_SECONDS`，預設 30 秒）期間不再嘗試 PG。
wiki-processor 端的索引同步是 best-effort —— **wiki 寫入永不因 PG 失敗
而失敗**，失敗會在 audit log 記一筆 `success_index_sync_failed`。

### PG 與 wiki.json 內容不一致（漂移）

PG 停機期間的提交不會進索引。偵測：比較
`GET /wiki_info` 的 `vector_index.last_sync.synced_at` 與
`metadata.updated_at`；audit log 搜 `success_index_sync_failed`。
修復：`POST /admin/reindex`（全量重建，30k entries 約 94 秒）。

### 啟動報錯 `embedding is vector(N) but EMBEDDING_DIM=M`

換了 embedding 模型或維度。舊向量與新向量不可比較，系統拒絕混用。
處理：

```sql
DROP TABLE api_entries, index_state, app_sync CASCADE;
```

然後 `POST /admin/reindex` 重建。

### `/semantic_search` 回 `mode: keyword_fallback`

依序檢查：(1) `PG_DSN` 是否設定（兩個服務都要）；(2) `GET /wiki_info`
的 `vector_index.available`；(3) embeddings 是否設定
（`EMBEDDING_BASE_URL` 或 `MOCK_EMBEDDINGS=true`）；(4) 索引是否為空
（`entries: 0` → 先 reindex）；(5) mcp-server log 中的具體錯誤。

### repmgr failover 後寫入失敗 / 出現兩個 primary

- 客戶端 DSN 必須是多主機 + `target_session_attrs=read-write`，failover
  後新連線會自動跳過 demoted 節點。promotion 窗口內的同步失敗走
  best-effort 路徑，事後 reindex 即可。
- 舊 primary 重新上線可能自認 primary（split-brain）。以
  `docker exec wiki-pg-0 repmgr node rejoin` 重新加入；若資料狀態可疑，
  直接 wipe volume 重建 —— PG 只是衍生索引，事實來源永遠是 wiki.json。

### 寫入變慢了？

每筆 app 同步 ≈ 5.5 ms（交易內 `synchronous_commit=off`）；100 並發
burst 實測 +12%。明顯更慢時檢查 PG 主機 I/O 與
`EMBEDDING_TIMEOUT`（真實 embeddings API 慢時，最多拖到 timeout 後降級
為 NULL 向量）。

---

## 常見錯誤參考

| 錯誤代碼 | 常見原因 | 解決方案 |
|---------|--------|--------|
| 400 | 請求格式錯誤 | 檢查 JSON 格式和必需字段 |
| 401 | 認證失敗 | 檢查 API Key |
| 403 | 權限不足/Host 限制 | 添加白名單 |
| 404 | 資源不存在 | 檢查 URL 和 Wiki 數據 |
| 500 | 服務器錯誤 | 查看詳細日誌 |
| 503 | 服務不可用 | 檢查服務是否運行 |

---

## 相關文檔

- [LOCAL_SETUP.md](LOCAL_SETUP.md) - 本地環境設置
- [DEVELOPMENT.md](DEVELOPMENT.md) - 開發和自定義
- [API_SCHEMA.md](API_SCHEMA.md) - 數據結構參考
