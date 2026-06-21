# LLM Wiki MCP

把「很多個應用程式的文件」自動匯集成一份**團隊共享、給 LLM 看的 Wiki**，並讓
AI agent（如 Claude）能直接連線查詢、跨領域推理。

支援 **100+ 應用程式**：每個 app 各自產生 markdown 文件，直接送進系統，幾乎即時、
**互不干擾**地增量更新。靈感來自 Andrej Karpathy 的 *LLM wiki*（用 LLM 把雜亂原始
文件「編譯」成結構化、互相連結的知識庫）。

> **名詞先講清楚**
> - **MCP（Model Context Protocol）**：一套讓 AI agent 連到外部工具/資料的標準協議。
>   本系統內建 MCP server，所以 Claude 可以「原生」連進來查 wiki，不用自己寫 API client。
> - **LLM（Large Language Model）**：大型語言模型，這裡用來讀文件、抽出結構化資料。
> - **embedding（向量）**：把文字轉成一串數字，意思相近的文字數字也相近 → 可做「語意搜尋」。
> - **pgvector**：PostgreSQL 的向量擴充，讓資料庫能存 embedding 並算相似度。

---

## 這系統解決什麼問題

公司有 100 個服務，每個都有自己的 API 文件、操作手冊。散在各處，AI 看不到全貌。
本系統讓每個 app 把文件「推」進來，自動：
1. 用 LLM 抽出每支 API 的結構（method、path、說明、來源）。
2. 也能吃**知識文件**（prose，例如「Oracle Flashback 怎麼救資料」「FastAPI 怎麼寫 endpoint」），不只 API spec。
3. 建立**跨應用概念（concepts）**連結 —— 例如「資料遺失」的知識文件會連到「flashback-api 的 /recover endpoint」。
4. 提供 **hybrid search（關鍵字 + 語意混合搜尋）**，問法不同也找得到。
5. 開 **MCP** 端點，讓 Claude 直接連進來，邊查邊推理。

---

## 架構

四個獨立服務，共用一套基礎設施（infra）：

```
        各應用程式 (fastapi-a, app-inventory, flashback-api …)
             │  CI 產生 markdown，POST 進來
             ▼
   ┌─────────────────────┐   寫入        ┌──────────────────────────┐
   │  wiki-processor :8001 │ ───────────▶ │  共用 infra (llm-wiki-infra) │
   │  收文件 → LLM 抽取     │              │   • MinIO（物件儲存）         │
   │  → 寫每-app 物件       │   讀取        │   • Postgres + pgvector      │
   └─────────────────────┘ ◀─────────── │                            │
             ▲                            └──────────────────────────┘
             │ 同步索引                              ▲
   ┌─────────────────────┐                          │ 讀取
   │  mcp-server :8002     │ ─────────────────────────┘
   │  查詢（REST + MCP）    │
   └─────────────────────┘
             ▲
             │ MCP / HTTP
        Claude / AI agent
```

| 服務 | 角色 |
|------|------|
| **llm-wiki-infra** | 共用基礎設施：一套 **MinIO**（物件儲存，存 wiki 檔）+ **Postgres/pgvector**（搜尋索引）。先啟動它，其他服務接上去。 |
| **wiki-processor** :8001 | **寫入端**。收 markdown → 呼叫 LLM 抽取 → 寫入 wiki。唯一會改資料的服務。 |
| **mcp-server** :8002 | **唯讀查詢端**。提供 REST API 與 **原生 MCP** 端點。Claude 連這個。 |
| **flashback-api** :8003 | 範例應用：把 Oracle 資料庫救援操作包成 API（同時當「推文件進 wiki」的示範）。 |

---

## 核心設計（重點）

| 設計 | 白話說明 |
|------|----------|
| **每-app 物件（per-app objects）** | 每個 app 的資料存成自己的檔 `apps/<app>.json`，不是擠在一個大檔。所以 100 個 app 同時更新也不會互卡，寫入速度不隨規模變慢。 |
| **source of truth + 衍生索引** | MinIO 裡的檔是「真相來源」；Postgres 索引是「為了查得快」從它衍生出來的副本。索引壞了可重建，不影響資料。 |
| **CAS（Compare-And-Swap）樂觀鎖** | 寫入時用 ETag 比對，確保並發寫入不會蓋掉彼此。每-app 物件各自一把鎖，互不競爭。 |
| **hybrid search（RRF 融合）** | 同時跑「關鍵字搜尋」(`pg_trgm`) 和「語意搜尋」(pgvector cosine)，再用 **RRF（Reciprocal Rank Fusion，倒數排名融合）** 合併結果。兩者互補：關鍵字抓精確字詞，語意抓同義改寫。 |
| **knowledge docs + concepts** | 除了 API spec，也吃 prose 知識文件，並自動把相關的知識↔API 連成「概念」，讓 agent 能跨領域推理。 |
| **graceful degradation（優雅降級）** | Postgres 掛了，自動退回直接掃 MinIO；embedding 服務掛了，退回關鍵字。查詢不會整個壞掉。 |
| **LLM 限流保護** | 大量 app 同時推送會撞到 LLM 供應商的 rate limit（429）。內建**指數退避重試** + **併發上限**，把失敗轉成「稍慢但成功」。 |

---

## 快速開始

兩種啟動方式，**一次只能跑一種**（都會用到 9000/5432 連接埠）：

### 方式 A：獨立服務 + 共用 infra（推薦，最接近真實部署）

```bash
# 1) 先起共用 infra（MinIO + Postgres）
cd llm-wiki-infra && docker compose up -d

# 2) 起寫入端
cd ../llm-wiki-processor
cp .env.example .env          # 不想填 key 就保持 MOCK_LLM=true
docker compose up -d --build

# 3) 起查詢端
cd ../llm-mcp-server
cp .env.example .env
docker compose up -d --build

# 4) 健康檢查
curl localhost:8001/health    # wiki-processor
curl localhost:8002/health    # mcp-server
```

或平台 repo 一鍵全起：`scripts/dev-up.sh`（關閉：`scripts/dev-down.sh`）。

### 方式 B：平台 repo 一份 compose 全包

```bash
docker compose up -d          # 平台根目錄，自帶一套 infra
```

---

## 用起來：推文件 + 查詢

```bash
# 推一個 app 的文件（實務上由該 app 的 CI 自動做）
curl -X POST localhost:8001/process -H 'Content-Type: application/json' -d '{
  "markdowns": {"api.md": "# Payments API\nPOST /refunds 退款給客戶"},
  "timestamp": "2026-06-20T00:00:00", "trigger_info": {},
  "source_app": "payments-api", "source_version": "v1"}'

# 批次推送後，重建跨應用概念 + 衍生彙總（非每次推送都要，批次後或排程跑）
curl -X POST localhost:8001/admin/rebuild-concepts

# 查詢（hybrid search）
curl 'localhost:8002/search_apis?query=退錢給客戶'        # 語意也找得到
curl 'localhost:8002/search_knowledge?query=undo a delete' # 知識文件
curl 'localhost:8002/wiki_info'                            # 統計
```

### 讓 Claude 直接連（MCP）

```bash
claude mcp add --transport http llm-wiki http://localhost:8002/mcp/
```
之後在 Claude 裡直接問「我誤刪了資料表怎麼救？有沒有內部 API？」，它會自己
查 knowledge + API 並串起來回答。

---

## 環境變數（重點）

```env
# LLM 供應商（7 選 1）：minimax / openai / anthropic / gemini / groq / azure / openai-compatible
LLM_PROVIDER=minimax
LLM_API_KEY=your-key          # 沒 key 想試 → 設 MOCK_LLM=true
LLM_MODEL=MiniMax-M3

# 共用 infra（預設值就指向 infra 服務名，通常不用改）
MINIO_ENDPOINT=minio:9000
PG_DSN=postgresql://wiki:wikipass@pg:5432/wiki   # 設空字串可關掉向量索引

# embedding（mcp-server 與 wiki-processor 必須一致，向量才在同一空間）
EMBEDDING_BASE_URL=...         # 本地模型或 OpenAI-相容端點
EMBEDDING_DIM=1536
MOCK_EMBEDDINGS=true           # 測試用，不呼叫真 API
```
完整範例見各 repo 的 `.env.example`。

---

## 測試

```bash
cd llm-wiki-processor && python -m pytest    # 寫入端單元測試
cd ../llm-mcp-server   && python -m pytest    # 查詢端單元測試
```
真實規模 + 效能測試結果見 [TEST_RESULTS.md](TEST_RESULTS.md)。

---

## 各 repo 文件

| repo | 看什麼 |
|------|--------|
| **llm-wiki-infra** | 共用 infra 怎麼起 |
| **llm-wiki-processor** | 寫入端：抽取 pipeline、CAS、概念/知識、向量同步 |
| **llm-mcp-server** | 查詢端：hybrid search、MCP 端點 |
| **flashback-api** | 範例應用（Oracle 救援 API），也是「推文件進 wiki」示範 |
</content>
