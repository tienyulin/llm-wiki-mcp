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
# 在 Python REPL 中測試
python3
>>> from wiki_processor.services.llm import MinimaxClient
>>> client = MinimaxClient(api_key="...")
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
