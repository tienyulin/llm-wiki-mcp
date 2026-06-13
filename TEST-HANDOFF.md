# 端到端測試交接（E2E TEST HANDOFF）

這份給**另一個有 docker daemon 的環境/session**，把整條 pipeline 真起服務跑一遍：
flashback-api 的 README → 模擬 GitLab CI push → wiki-processor → MinIO → mcp-server 查詢。

（開發 repo 的環境沒有 docker daemon，只能 in-process 驗核心邏輯；這份交接是去
有 docker 的地方跑真實 HTTP + MinIO 全鏈。）

## 給接手 session 的一句話 prompt

> Checkout branch `claude/e2e-pipeline-test`，讀根目錄 `TEST-HANDOFF.md`，
> 照「執行步驟」跑完端到端測試，把每個 curl 的實際輸出貼出來，並對照
> 「預期輸出」回報通過或哪裡不符。

## 前置需求

- `docker` + `docker compose`（需 daemon 真的在跑）
- `git`、`curl`、`python3`
- 對外網路（首次 `docker compose build` 要裝 pip 套件）

## .env 需要什麼

**Mock 模式（推薦先跑這個）：完全不需要任何 API key、不需要建 .env。**
`docker-compose.yml` 的預設值已足夠：

| 變數 | compose 預設 | 意義 |
|------|-------------|------|
| `MOCK_LLM` | `true` | wiki-processor 用確定性 mock 萃取（不呼叫真 LLM） |
| `MOCK_EMBEDDINGS` | `true` | 不呼叫真 embedding |
| `PROCESSOR_API_KEY` | 空 | `/process` dev 模式不驗 key |
| `PG_DSN` | 空 | 不啟用 PG 向量層（純 MinIO 路徑） |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO 帳密 |

→ 直接跳到「執行步驟」即可。

**（可選）真 LLM 萃取**：想看真實 LLM（非 mock）把 README 萃取成 wiki，建 `.env`：

```env
# 例：MiniMax 國際版
LLM_PROVIDER=minimax
LLM_API_KEY=sk-...your-key...
LLM_MODEL=MiniMax-M3
MOCK_LLM=false
MOCK_EMBEDDINGS=true        # embedding 仍可 mock；要真語意搜尋才需設 embedding 變數 + PG
```

其他 provider（openai / anthropic / gemini / groq / azure / openai-compatible）
設定範例見 `.env-example`。

## 執行步驟

```bash
# 0. 取得這個 branch
git fetch origin && git checkout claude/e2e-pipeline-test

# 1. 起 mock 全鏈（minio + wiki-processor + mcp-server）
docker compose up -d minio wiki-processor mcp-server

# 2. 等服務 healthy（約 10-30 秒）
docker compose ps
curl -s localhost:8001/health        # wiki-processor → {"status":...}
curl -s localhost:8002/health        # mcp-server     → {"status":"ok"}

# 3. 模擬 flashback-api 的 GitLab CI push（拿它的 README 當 markdown POST /process）
bash examples/simulate-app-push.sh

# 4. 在 mcp-server 查到剛進去的 flashback-api 端點
curl -s localhost:8002/list_apis | python3 -m json.tool
curl -s 'localhost:8002/search_apis?query=flashback' | python3 -m json.tool
curl -s 'localhost:8002/get_api_detail?module=flashback-api&api_key=POST%20/flashback/database' | python3 -m json.tool
curl -s localhost:8001/status | python3 -m json.tool

# 5. 清理
docker compose down -v
```

## 預期輸出

第 3 步 `simulate-app-push.sh` 應印：

```
✅ flashback-api/README.md -> flashback-api.md (~5200 bytes)
   source_app: flashback-api ...
📥 Response: HTTP 200
   Status: success
✅ Wiki updated successfully!
```

第 4 步 `GET /list_apis` 應含 module `flashback-api`、11 個端點
（module 名取檔名 stem，mock 與真 LLM 一致；端點掃描略過 fenced code block，
所以 README 範例註解裡的 `POST /process` 不會被誤收）：

```json
{
  "modules": {
    "flashback-api": [
      "DELETE /restore_points/{name}",
      "GET /audit/log",
      "GET /flashback/status",
      "GET /health",
      "GET /recyclebin",
      "GET /restore_points",
      "POST /flashback/database",
      "POST /flashback/database/finalize",
      "POST /flashback/drop",
      "POST /flashback/table",
      "POST /restore_points"
    ]
  }
}
```

`GET /search_apis?query=flashback` → `count: 11`、`mode: "wiki_scan"`（無 PG 時）。

`GET /get_api_detail?module=flashback-api&api_key=POST /flashback/database`
（mock 模式 `description` 取 README 的 H1；真 LLM 會回較豐富的萃取文字）：

```json
{
  "detail": {
    "method": "POST",
    "path": "/flashback/database",
    "description": "flashback-api — Oracle Flashback Recovery API",
    "source_app": "flashback-api",
    "source_version": "0.1.0"
  }
}
```

`GET /status`（wiki-processor）→ `wiki_size: 1`（= 已收錄的 app/module 數，非端點數）、
`last_updated` 為剛才時間。

## 成功標準

- 兩個 `/health` 都回 200
- `simulate-app-push.sh` 回 `status: success`
- `list_apis` 出現 module `flashback-api` 且 11 個端點到齊
- `get_api_detail` 取得 method/path/description

任一不符 → 貼 `docker compose logs wiki-processor` 的尾段回報。

## 整條鏈說明

完整 pipeline（SOP → skill → spec → API + README → push → wiki → 查詢）的
設計與背景見 `docs/guides/sop-to-wiki-pipeline.md`。
契約測試（不需 docker）：`python -m pytest tests/integration/test_readme_to_wiki.py -q`。
