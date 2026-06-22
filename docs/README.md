# 文件索引

歡迎來到 LLM Wiki MCP 文件。此目錄依分類整理所有專案文件。

## 📋 快速導覽

### 🚀 開始上手
- **[端到端範例](guides/end-to-end-example.md)** — 跟著兩份真實 markdown 走完整條
  pipeline：每步產生什麼、MinIO/Postgres 存什麼、各查詢端點回什麼。**新手從這開始。**
- **[SOP → Wiki Pipeline](guides/sop-to-wiki-pipeline.md)** — 完整鏈：SOP → spec →
  API + README → 模擬 CI push → wiki → 查詢，含真實輸出。
- **[真實語意實跑](examples/real-semantic-walkthrough.md)** — 一個真實請求穿過每一層，
  全程**擷取真實資料**：embedding API 回應、MinIO `wiki.json`、PG 列 + 向量、語意查詢
  —— 並在 psql 重現 pgvector cosine 來證明 mcp 的分數。每個值都配上產生它的指令。
- **[本地設置指南](guides/local-setup.md)** — 如何本地建置、起服務、跑測試
- **[快速開始](../README.md#快速開始)** — 主 README 的快速開始

### 🏗️ 架構與設計
- **[架構圖](architecture/diagrams.md)** — 跨服務 mermaid 視圖：系統、匯入 pipeline、查詢/管理介面、資料模型、執行模式
- **[服務分層](architecture/service-layering.md)** — 三層架構（api/service/repository）、依賴注入、測試模式
- **[LLM Provider 抽象](../wiki-processor/docs/llm-provider-abstraction.md)** — 7-provider 抽象層設計與實作 *(住在 wiki-processor 元件)*
- **[並發模型](../wiki-processor/docs/concurrency.md)** — 多 replica 安全的兩階段 CAS 寫入 pipeline *(住在 wiki-processor 元件)*
- **[向量搜尋](architecture/vector-search.md)** — PG+pgvector 索引設計、實測評估、失敗語意（含圖）
- **[API Schema](api/schema.md)** — 完整 API 端點文件

### 👨‍💻 開發
- **[開發指南](guides/development.md)** — 程式碼結構、如何擴展、開發流程
- **[SOP → Spec → Service](../specs/oracle-flashback-recovery-api.spec.md)** — 文件驅動流程：SOP（`../sop/`）→ 經 `.claude/skills/sop-to-spec` 產 spec → `flashback-api/` 實作
- **[GitLab 整合](guides/gitlab-setup.md)** — CI/CD 設定與 GitLab 整合步驟

### 🔧 疑難排解與監控
- **[疑難排解指南](troubleshooting.md)** — 常見問題與解法
- **[測試結果](test-results.md)** — 最新測試與效能數據

---

## 📁 目錄結構

```
docs/
├── README.md                              # 本檔
├── guides/
│   ├── end-to-end-example.md             # 走完整 pipeline 的範例
│   ├── local-setup.md                    # 本地環境設置
│   ├── development.md                    # 開發規範
│   └── gitlab-setup.md                   # GitLab CI/CD 設定
├── architecture/
│   ├── service-layering.md               # 三層架構
│   └── vector-search.md                  # PG+pgvector 設計 + 評估
├── api/
│   └── schema.md                         # API 端點參考
├── troubleshooting.md                    # 疑難排解 & FAQ
└── test-results.md                       # 測試執行結果
```

---

## 🧪 測試

```bash
# 各服務 repo 的單元測試（從各 repo 目錄跑）
cd wiki-processor && python -m pytest
cd mcp-server && python -m pytest

# 平台整合/壓力測試
python -m pytest tests/integration/test_processor.py
```

---

## 📖 文件用途

| 檔 | 用途 | 讀者 |
|------|---------|----------|
| local-setup.md | 逐步環境設置 | 開發者 |
| development.md | 程式碼結構與擴展指南 | 貢獻者 |
| gitlab-setup.md | CI/CD pipeline 設定 | DevOps / 開發者 |
| llm-provider-abstraction.md | provider 模式設計決策 | 架構師 |
| schema.md | API 端點參考 | 後端開發者 |
| troubleshooting.md | 常見問題與修法 | 所有人 |
| test-results.md | 效能基準 | QA / Ops |

---

## 📝 更新紀錄

- **2026-06-20** — 真實 LLM 規模壓測 + P1–P4 修復（見 [test-results.md](test-results.md)）；文件中文化
- **2026-06-11** — 向量索引層（Postgres + pgvector）
- **2026-05-10** — Phase 8 完成：7-provider LLM 抽象
</content>
