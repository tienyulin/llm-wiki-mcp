# LLM Wiki MCP — Platform（平台 / 總集 repo）

> 👉 **想真正搞懂這系統怎麼運作（含真實實跑紀錄），先看
> [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)。** 那是唯一的「從這開始」文件。

把「很多個應用程式的文件」自動匯集成一份**團隊共享、給 LLM 看的 Wiki**：每個 app
各自產生 API 文檔 → 推送到處理器 → LLM 萃取 → 存入 MinIO + Postgres/pgvector
→ 透過 **MCP** 給 Claude/agent 查詢（關鍵字 + 語意），並能跨領域推理。

這個 repo 是**平台 / 總集（umbrella）**。各服務有自己的 repo，在這裡以
**git submodule（子模組）**接進來 —— 每個服務都能獨立 build / 跑 / 部署，平台只是
把它們組起來做全棧本地開發與整合。

> **名詞先講清楚**
> - **MCP（Model Context Protocol）**：讓 AI agent 原生連到外部工具/資料的標準協議。本平台開 MCP 端點，Claude 可直接連進來查 wiki。
> - **LLM**：大型語言模型，用來讀文件、抽出結構化資料。
> - **embedding（向量）**：文字轉成數字陣列，意思近數字也近 → 可做語意搜尋。
> - **pgvector**：Postgres 的向量擴充，存 embedding 並算相似度。
> - **submodule（子模組）**：一個 git repo 以指標方式嵌進另一個 repo。

## 組成（各自獨立的 repo）

| 服務 | Repo | 角色 |
|------|------|------|
| **llm-wiki-infra** | [tienyulin/llm-wiki-infra](https://github.com/tienyulin/llm-wiki-infra) | 共用基礎設施：一套 MinIO（物件儲存）+ Postgres/pgvector（索引） |
| **wiki-processor** | [tienyulin/llm-wiki-processor](https://github.com/tienyulin/llm-wiki-processor) | **寫入端**：`POST /process` → LLM 萃取 → MinIO（每-app 物件，CAS）→ pgvector 索引 |
| **mcp-server** | [tienyulin/llm-mcp-server](https://github.com/tienyulin/llm-mcp-server) | **唯讀查詢端**：hybrid search（關鍵字 + 語意），PG 優先、可退回 MinIO；內建 MCP 端點 |
| **flashback-api** | [tienyulin/flashback-api](https://github.com/tienyulin/flashback-api) | 範例上游 app（Oracle Flashback 救援 API），兼示範「推文件進 wiki」 |

每個 repo 都有自己的 README、`.env.example`、`docker-compose.yml`、`docs/`、測試。

## 架構

```
100+ apps ──(CI: ci-templates/)──> wiki-processor:8001 /process
                                        │  LLM 萃取（app 級增量、ETag CAS）
                                        ▼
                          MinIO：每-app 物件 apps/<app>.json（真相來源）
                                        │  盡力同步（best-effort）
                                        ▼
                          Postgres + pgvector（衍生索引）
                                        ▲
                          mcp-server:8002（REST + MCP）──> Claude / agent
```

- **每-app 物件**：每個 app 存自己的檔，一次推送只寫自己的（O(1)），100+ app 同時更新不互卡。彙總 `wiki.json`（概念/總覽）由 `/admin/rebuild-concepts` 按需重建。
- **hybrid search**：關鍵字（`pg_trgm`）+ 語意（pgvector cosine）用 **RRF（倒數排名融合）**合併，互補；有相似度下限擋雜訊。
- **knowledge docs + concepts**：除 API spec 也吃 prose 知識文件，並自動連成跨應用「概念」供 agent 跨領域推理。
- 索引層可選（`PG_DSN=` 空字串關閉 → 退回掃 MinIO）。

## 兩種啟動方式

```bash
git clone --recurse-submodules https://github.com/tienyulin/llm-wiki-mcp
cd llm-wiki-mcp
```
（已 clone 但沒帶 submodule？`git submodule update --init`。）

### 方式 A — 一份 compose 全包（self-contained）
全部在一個 compose 專案，自帶 minio + pg：
```bash
cp .env-example .env            # 不想填 key → 保持 MOCK_LLM=true
docker compose up -d --build    # minio + pg + wiki-processor + mcp-server
curl localhost:8001/health && curl localhost:8002/health
```

### 方式 B — 獨立服務 + 共用 infra（開發用）
一套**共用** minio + pg（[`infra/`](infra) = `llm-wiki-infra` 子模組），各服務用自己的
compose 接上去，可獨立跑/重啟/開發，共用資料且 infra 不撞埠：
```bash
scripts/dev-up.sh        # infra + wiki-processor + mcp-server + flashback-api
scripts/dev-down.sh      # 停止（加 -v 清空共用資料）
```
或手動：`(cd infra && docker compose up -d)` 再 `cd <service> && docker compose up -d`。

> **一次只能跑一種** —— 兩者都用主機埠 9000/9001/5432。

把各服務更新到最新：`git submodule update --remote`。

### 讓 Claude 直接連（MCP）
```bash
claude mcp add --transport http llm-wiki http://localhost:8002/mcp/
```

## 平台內容物

- `docker-compose.yml` — 方式 A 全棧（自帶 infra）
- `infra/` — 子模組 [llm-wiki-infra](https://github.com/tienyulin/llm-wiki-infra)：共用 minio + pg（方式 B）
- `scripts/dev-up.sh`・`scripts/dev-down.sh` — 方式 B 編排
- `ci-templates/` — 各 app include 的 GitLab CI 模板（產文件 + 推送）
- `sop/`、`specs/` — 範例「SOP → spec → API」原始素材
- `examples/` — `simulate-app-push.sh`、`send_to_processor.py`
- `tests/` — 跨服務整合 + 壓力測試
- `db/init/` — pgvector + pg_trgm 擴充初始化
- `docs/` — 跨領域文件（見下）

## 文件

- **[docs/README.md](docs/README.md)** — 完整索引
- 測試結果：**[docs/test-results.md](docs/test-results.md)**（含最新真實 LLM 規模壓測 + P1–P4 修復實測）；壓測計畫：[SCALE_STRESS_PLAN.md](SCALE_STRESS_PLAN.md)
- 架構（跨領域）：[service-layering](docs/architecture/service-layering.md)、[vector-search](docs/architecture/vector-search.md)
- 指南：[local-setup](docs/guides/local-setup.md)、[sop-to-wiki-pipeline](docs/guides/sop-to-wiki-pipeline.md)、[gitlab-setup](docs/guides/gitlab-setup.md)
- 真實資料實跑：見 [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)（逐層真實紀錄）
- 各服務細節在該服務 repo 的 `docs/`。

## 測試

- 各服務 repo：`cd <repo> && python -m pytest`（隔離測試）。
- 平台整合/壓力：`tests/` —— 見 [tests/README.md](tests/README.md)。
</content>
