# 文件索引

文件分三層。**新手只要看 🟢 那層**，其餘想深入再看。

## 🟢 從這開始（新手必看）
- **[這系統到底怎麼運作（含真實紀錄）](HOW-IT-WORKS.md)** ← **先看這份。** 白話 + 真實實跑，
  帶你看一筆資料從 push 到被 Claude 查到、每層存什麼、為什麼這樣答。
- **[平台 README](../README.md)** — 全貌、四個服務、兩種啟動方式。
- **[本地設置](guides/local-setup.md)** — 在自己機器上把整套跑起來。

## 🔵 想深入（看實作細節）
- 架構：[service-layering](architecture/service-layering.md)（三層架構）、
  [vector-search](architecture/vector-search.md)（向量搜尋設計 + 實測）
- 寫入端細節：`llm-wiki-processor/docs/`（CAS 並發、LLM 抽取、概念連結、diagram）
- 查詢端細節：`llm-mcp-server/docs/`（hybrid 搜尋、MCP transport、diagram）
- [開發指南](guides/development.md) — 程式碼結構、如何擴展
- [SOP → Wiki Pipeline](guides/sop-to-wiki-pipeline.md) — 文件驅動的 flashback 範例鏈

## ⚪ 參考（需要時查）
- [API Schema](api/schema.md) — 完整端點規格
- [測試結果](test-results.md) — 真實 LLM 規模壓測 + P1–P4 修復數據
- [疑難排解](troubleshooting.md) — 常見問題與解法
- [GitLab CI 設定](guides/gitlab-setup.md) — app 端怎麼自動推文件
- [壓測 runbook](../tests/stress/STRESS_TEST_PLAN.md)、[測試說明](../tests/README.md)
- SOP → spec 範例素材：`../sop/`、`../specs/`

---
其餘各服務 repo 都有自己的 README（中文）。最新更新：2026-06-22（新增 HOW-IT-WORKS、精簡文件）。
</content>
