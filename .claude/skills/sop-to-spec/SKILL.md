---
name: sop-to-spec
description: Convert an operations SOP (any domain — DBA runbooks, infra procedures, deployment checklists) into an API spec that BOTH a human approver can read and an AI agent can implement a three-layer FastAPI service from. Trigger - "SOP 轉 spec", "convert SOP", "/sop-to-spec <path>", or when the user wants to turn a procedure document into an API.
---

# SOP → Implementation Spec（v5）

把人類操作 SOP 轉成一份 API spec。spec 有**兩個讀者，缺一不可**：

| 讀者 | 需要什麼 | spec 對應部分 |
|------|---------|--------------|
| **人類審批者** | 白話看懂這 API 做什麼、風險在哪、哪些不自動化——才有辦法簽核 | **Part A 審批摘要**（先寫，放最前面） |
| **實作 agent** | 零猜測的精確規格（驗收準則、schema、mock 狀態） | **Part B 實作規格** |

三條鐵律：

1. **spec 是唯一交接物**——實作 agent 只讀 spec，不回讀 SOP；SOP 裡實作需要的
   資訊全部 inline
2. **自足**——禁止引用 SOP 與自身以外的檔案/慣例（「比照 xxx 服務」不行），
   全新 repo 也要能照 spec 開工
3. **未定義行為 = spec 的 bug**——實作中發現就回報修 spec，不是 code 自由發揮

## 輸入 / 輸出

- 輸入：SOP 檔案路徑（`$ARGUMENTS` 或使用者指定）
- 輸出：`specs/<sop-slug>-api.spec.md`

## 流程（六步，依序）

| Step | 做什麼 | 細節 |
|------|--------|------|
| 1 萃取 | 讀 SOP 列五張清單：查詢類→GET、操作類→POST/DELETE、前置條件、錯誤對照表、審計欄位 | — |
| 2 風險分級 | 每個操作分 `read` / `reversible` / `irreversible`（SOP 有「警告/需審批/無法復原」→ 一律 irreversible） | [references/spec-template.md](references/spec-template.md) §風險分級 |
| 3 產 spec | 先寫 Part A（給人），再照模板填 Part B（給 agent），逐端點過完逼問清單 | 模板：[references/spec-template.md](references/spec-template.md)；逼問清單：[references/checklists.md](references/checklists.md) |
| 4 自檢 | 跑完自檢清單（含 fresh-repo 測試、Part A 白話測試） | [references/checklists.md](references/checklists.md) |
| 5 盲審閘門 | 乾淨 context 的 agent 只讀 spec 盲審；**HIGH > 0 不准寫 code**；發現與處置記入 `specs/REVIEWS.md` | 盲審 prompt 與分流規則：[references/checklists.md](references/checklists.md) |
| 6 實作回饋 | 寫完 code 後，缺陷歸因（SOP/skill/spec/code）修對應層，不是只修 code | [references/checklists.md](references/checklists.md) §歸因表 |

## 實作交付物（Step 5 過了之後）

照 spec Part B 蓋三層式 FastAPI（api / service / repository + mock），並且
**必附 `README.md`**：快速啟動（mock 模式一行起服務）、端點白話表、
2–3 個 curl 實際走一遍的情境（含不可逆操作的 dry_run→confirm 全流程）、
環境變數表、怎麼跑測試。沒有 README 的 API 等於不能用。

## 歷史

v1→v4 三輪盲審迭代（缺陷歸因紀錄：`specs/REVIEWS.md`）。v5：依
Anthropic skill 規範改 progressive disclosure（本檔瘦身、細節進 references/），
依 spec-kit 規範加 Part A 人類審批層與 README 要求。
