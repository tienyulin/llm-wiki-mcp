# LLM Wiki MCP — 測試結果報告

**更新日期**：2026-06-20
**測試環境**：真實 LLM（Minimax **M3**）+ 本地 embedding 模型（fastembed **bge-small**，384 維）+ Postgres/pgvector，全 Docker。
**範圍**：規模壓力測試（100 app）、四個規模問題的修復前後對照、查詢品質與延遲。

> **名詞**
> - **embedding / 向量**：文字轉成數字陣列，意思近數字也近。
> - **hybrid search**：關鍵字搜尋 + 語意（向量）搜尋兩者合併。
> - **p50 / p95**：延遲的中位數 / 第 95 百分位（95% 的請求比這快）。
> - **q/s**：queries per second，每秒查詢數（吞吐量）。
> - **429 / rate limit**：LLM 供應商的「請求太多」限流錯誤。

---

## 一、規模壓力測試（100 app）

模擬 100 個 app（每個 10 支 endpoint）+ 200 份知識文件併發推進來，量測系統各環節。

### 讀取（查詢）— 表現優異，隨規模穩定

| 項目 | 結果 |
|------|------|
| 單次查詢延遲（hybrid / 語意 / 關鍵字） | p50 **4–10ms**，p95 ≤14ms |
| 併發查詢吞吐（32 並行，mock embedding） | **260 q/s** |
| 重建索引（reindex，1000 endpoint） | **1.07s** |
| 重建概念（rebuild-concepts） | **94ms** |

**結論**：讀取路徑（Postgres/pgvector）規模化良好，不是瓶頸。

### 寫入 — 找到瓶頸（後由 P3 修復）

舊設計每次推送都重寫**整個** `wiki.json`：app 越多檔越大，寫入越慢。
- 前 10 次推送平均 **596ms** → 後 10 次 **795ms**（+33%）。
- 成本是 O(N²)：N 個 app 各重寫含 N 個 app 的大檔。

---

## 二、真實 LLM 跑出來的四個問題 + 修復（P1–P4）

用真 Minimax M3 跑（每次抽取約 15–25 秒），抓到四個規模/穩定性問題，逐一修並用實測驗證。

| # | 問題 | 修法 | 修復前 → 後（實測） |
|---|------|------|----------------------|
| **P1** | 併發推送撞 LLM **rate limit（429）**，無重試 → 大量失敗 | 指數退避重試（exponential backoff）+ 併發上限（concurrency cap，信號量） | 失敗率 **65% → 0%** |
| **P2** | `rebuild-concepts` 在規模下 **HTTP 500 逾時**（把整個目錄塞進一個 LLM prompt） | 改用確定性分群（deterministic clustering），完全不呼叫 LLM | **500 逾時 → 0.20s** |
| **P4** | 每次查詢都同步算 query embedding，併發下卡在單一 embedder | query embedding 加 **LRU cache（最近最少用快取）** | 重複查詢吞吐 **57 → 221 q/s** |
| **P3** | 寫入重寫整個 `wiki.json`（O(N²)） | **每-app 物件** `apps/<app>.json`，一次只寫自己的檔 | 寫入延遲隨規模 **+33% → 持平** |

### P1 細節（限流保護）
真 M3、併發 8、30 個 app：修復前 **65% 失敗**（429 快速失敗），加上重試+併發上限後 **0% 失敗**（30/30 成功，較慢但全成功 —— 對 100+ app 的車隊，「可靠」比「快但掉資料」重要）。

### P3 細節（每-app 物件，最關鍵）
400 app 實測，每次推送延遲 **持平 ~35ms**（不隨已存 app 數惡化）；絕對值也從約 600–800ms 降到 ~35ms。彙總 `wiki.json` 改為按需重建（400 app / 4000 endpoint 重建 **0.83s**）。

| 已存 app 數 | 每次推送平均延遲 |
|------|------|
| 0–100 | 36ms |
| 100–200 | 34ms |
| 200–300 | 36ms |
| 300–400 | 35ms |

成長倍率 **1.33×（修前）→ 0.92×（持平，修後）**。

---

## 三、查詢品質（真 embedding）

真實 bge-small 向量下，自然語言問法（非精確關鍵字）都導到正確 endpoint：

| 問句 | 命中 |
|------|------|
| 「give a customer their money back」 | `payments-api POST /refunds` ✅ |
| 「recover lost data」 | `flashback-api POST /recover` ✅ |
| 「log in and get a token」 | `auth-api POST /login` ✅ |

**hybrid 召回對照**（flashback 文件，6 種改寫問法）：純關鍵字 **1/6** → hybrid **6/6**；
不相關問句（「how to bake bread」）正確回傳 **0 筆**（有相似度下限把關）。

**跨領域推理**（透過 Claude over MCP）：問「我誤刪了資料表怎麼救？有沒有內部 API？」
→ agent 自己查到 Oracle Flashback 知識文件 + `flashback-api POST /recover` 並串起來，附出處。

---

## 四、單元測試

| repo | 結果 |
|------|------|
| llm-wiki-processor | **78 passed, 15 skipped**（skip = 需真 Postgres 的測試，本地自動跳過） |
| llm-mcp-server | **59 passed** |

---

## 結論

- 讀取與跨領域推理：規模化良好、品質佳。
- 四個規模問題全修復，皆有修復前後實測佐證。
- **P3（每-app 物件）是核心**：寫入延遲不再隨 app 數惡化，可服務「大公司、很多 app」場景。

> 完整壓測計畫與逐步數據見 [SCALE_STRESS_PLAN.md](SCALE_STRESS_PLAN.md)。
</content>
