# 測試套件

此目錄含 LLM Wiki MCP 專案的所有測試，依分類整理。

## 📁 結構

```
tests/
├── integration/             # 整合測試
└── stress/                  # 效能 & 壓力測試

wiki-processor/tests/        # 單元測試（wiki-processor）
mcp-server/tests/            # 單元測試（mcp-server）
```

> ⚠️ `wiki-processor` 與 `mcp-server` 是**獨立的 import root**。單元測試要從各 package
> 目錄跑（`python -m pytest` 會把 cwd 放進 `sys.path`）。從 repo 根目錄跑
> `pytest wiki-processor/tests/ mcp-server/tests/` **不會動**（import error + 重複的
> `tests` package 名）。

## 🧪 測試分類

### 單元測試（hermetic／隔離）
**位置：** 各服務 package 內

重點檔（wiki-processor）：`test_llm.py`（LLM 抽象）、`test_routes.py`（端點：空 markdown 422、
X-API-Key 驗證）、`test_processor.py`（變更偵測）、`test_concurrency.py`（**並發回歸**：per-app
物件、CAS 衝突注入、重送只取代該 app）、`test_storage_cas.py`（MinIO 條件寫入，無 server 自動 skip）、
`test_embeddings.py`、`test_vector_sync.py`（PG 索引同步 best-effort）、`test_pg_store.py`（對**真
Postgres+pgvector**，無 server 自動 skip）、`test_dominant_app_links.py`（概念連結 dominant-app 邊界）、
`test_llm_retry.py`（限流退避 + 併發上限）。

重點檔（mcp-server）：`test_rate_limit.py`、`test_wiki_service.py`、`test_cache.py`、
`test_pg_read_path.py`（PG 優先讀 + fallback、語意降級、斷路器）、`test_embeddings.py`
（**golden-pinned** 與 wiki-processor 的 mock_embed 一致）、`test_query_embed_cache.py`（query 向量 LRU 快取）、
`test_mcp_server.py`（MCP initialize → tools/list → tools/call）。

單元測試**hermetic** —— 不需 MinIO 或 LLM API（各 package 的 `conftest.py` stub 掉 Minio SDK；
wiki-processor 另設 `MOCK_LLM=true` / `MOCK_EMBEDDINGS=true`）。例外：真-MinIO CAS 測試與真-PG store
測試，無 server 時自動 skip。

```bash
cd wiki-processor && python -m pytest          # 78 passed, 15 skipped（無 server 時 CAS/PG skip）
cd mcp-server && python -m pytest              # 59 passed

# 真-PG store 測試需要任一裝 pgvector 的 Postgres：
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=pg -e POSTGRES_DB=wiki pgvector/pgvector:pg16
```

### 整合測試
**位置：** `tests/integration/`

- `test_processor.py` —— payload/邏輯驗證（pytest，免 server）
- `test_docker_integration.py` —— 端到端：對運行中的服務跑多個情境（單 app、多 app、wiki 結構、
  API 細節、10 並行 app、增量更新、語意搜尋 —— 語意情境在 `wiki_info.vector_index.available`
  為 false 時自動 skip）

**需要運行中的服務** —— `docker compose up`，或本地 MinIO binary + 兩個 uvicorn（設 `MOCK_LLM=true`
與 `MCP_SERVER_URL`）。

### 壓力測試
**位置：** `tests/stress/` —— 這些是**腳本，用 `python` 跑、非 pytest**

- `test_mock_stress.py` —— in-memory CAS storage 上 100 路併發更新：無 lost update、重送取代、
  app 隔離、audit 完整
- `test_real_service_stress.py` —— **100 並發 app 對真 HTTP 服務 + 真 MinIO（真 ETag 條件寫入）**；
  逐 app 驗證完整性。印 p50/p95 `processing_time_ms`；PG 索引啟用時另驗 PG 條目數與語意可尋性
- `STRESS_TEST_PLAN.md` —— 100+ app 壓測的逐步**runbook**

```bash
python tests/stress/test_mock_stress.py            # hermetic，免 server
python tests/stress/test_real_service_stress.py    # 需運行中的服務
```

## 📊 測試環境變數

| 變數 | 預設 | 用途 |
|----------|---------|---------|
| `MOCK_LLM` | false | 用 mock LLM（跳過 API 呼叫） |
| `LLM_PROVIDER` | minimax | 測試用 LLM provider |
| `LLM_API_KEY` | (未設) | 測試真 LLM API |
| `MINIO_ENDPOINT` | minio:9000 | MinIO 位址（本地用 `localhost:9000`） |
| `MCP_SERVER_URL` | (未設) | 啟用 wiki-processor → mcp 的快取失效 |
| `PROCESSOR_API_KEY` | (未設) | /process 驗證 key；整合/壓測 client 自動帶 |
| `PG_DSN` | (未設) | 在兩個服務啟用 PG 向量索引 |
| `MOCK_EMBEDDINGS` | false（unit conftest 為 true） | 確定性本地 embedding，免網路 |

## 📊 預期結果

| 套件 | 預期 | 時間 |
|-----------|-----------------|----------|
| 單元（processor 78 / mcp 59） | 全過 | ~6s |
| 整合（多情境） | 全過 | ~10s |
| 壓力 | 全過 | ~15s（`MOCK_LLM=true`） |

最新驗證結果見 `docs/test-results.md`。

## 🐛 除錯

```bash
python -m pytest -v --log-cli-level=DEBUG          # 詳細 log
python -m pytest tests/test_concurrency.py -v      # 單檔（從 package 目錄）
python -m pytest --pdb                             # 失敗時進 pdb
```

---

**最後更新：** 2026-06-20
</content>
