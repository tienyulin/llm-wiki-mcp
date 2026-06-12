---
name: sop-to-spec
description: Convert an operations SOP (any domain — DBA runbooks, infra procedures, deployment checklists) into an implementation-ready API spec markdown that an AI agent can build a three-layer FastAPI service from, without re-reading the SOP. Trigger - "SOP 轉 spec", "convert SOP", "/sop-to-spec <path>", or when the user wants to turn a procedure document into an API.
---

# SOP → Implementation Spec

把一份人類操作 SOP 轉成 **AI agent 可以直接照著寫 code 的 API spec markdown**。
spec 是唯一交接物：寫 code 的 agent 只讀 spec，不回頭讀 SOP。所以 SOP 裡所有
實作需要的資訊（指令、錯誤碼、前置條件）都必須搬進 spec，不可以只留參照。

## 輸入 / 輸出

- 輸入：SOP 檔案路徑（`$ARGUMENTS` 或使用者指定）
- 輸出：`specs/<sop-slug>-api.spec.md`（slug 取 SOP 檔名）

## 轉換步驟

### Step 1 — 萃取（讀 SOP，列五張清單）

1. **查詢類**：SOP 裡所有「檢查 / 查詢 / 確認」動作 → 候選 GET 端點
2. **操作類**：所有會改變系統狀態的動作 → 候選 POST/DELETE 端點
3. **前置條件**：每個操作執行前必須成立的條件（SOP 的 checklist / 前置章節），
   含檢查方式與不成立時的系統錯誤碼
4. **錯誤對照**：SOP 的故障排除表（錯誤碼 → 原因 → 處置）
5. **審計要求**：SOP 要求留存的欄位

### Step 2 — 風險分級（決定端點防護等級）

| 等級 | 判斷標準 | API 防護 |
|------|---------|---------|
| `read` | 純查詢 | 無 |
| `reversible` | 可被另一個操作撤銷（SOP 有回退步驟） | `dry_run` 參數（預設 `true`）；response 必含回退所需資訊（如操作前狀態） |
| `irreversible` | SOP 標示不可逆 / 需審批 | `dry_run` 預設 `true` ＋ 必填 `confirm` 字串（固定 token）＋ 必填審批欄位（SOP 有要求時）；缺一回 428 |

SOP 中「警告」「需審批」「無法復原」字樣 → 一律 `irreversible`。

### Step 3 — 產出 spec（固定模板，每節必填）

````markdown
# <名稱> API Spec
> Generated from: <SOP 路徑>（版本/編號）

## 1. Domain Model
（SOP 裡的核心實體與狀態。例：restore point、recycle bin entry。
 每個實體列欄位與型別 — 這直接變成 pydantic model 與 mock 狀態。）

## 2. Endpoints 總表
| Method | Path | 風險等級 | 對應 SOP 章節 |

## 3. 各端點規格
每個端點：
- Request schema（欄位、型別、必填、驗證規則）
- Response schema（含範例 JSON）
- 前置條件 → HTTP 對應表：
  | 前置條件 | 違反時 HTTP | body 內 error code（沿用 SOP 的系統錯誤碼） |
- 風險防護（依 Step 2 等級）
- 對應 SOP 章節編號（traceability）

## 4. 三層式落點
依 docs/architecture/service-layering.md 慣例：
- api/routers/ 檔案切分
- services/ 方法清單（前置條件檢查住這層）
- repository/ 介面：對外部系統（DB/OS/API）的每個呼叫一個方法，
  **必須有 mock 實作**（環境變數 `MOCK_<SYSTEM>=true`），mock 的初始狀態
  在此節寫死（測試與文件範例都用它）

## 5. 設定（環境變數）
連線資訊、API key、mock 開關 — 含預設值

## 6. 錯誤模型
統一 error body：`{"detail": str, "error_code": str|null}`；
SOP 故障排除表整張搬進來

## 7. 審計
SOP 審計欄位 → audit log schema 與寫入時機（所有非 read 操作）

## 8. 測試計畫
每個端點至少：happy path ×1、每個前置條件違反 ×1、風險防護 ×1
（irreversible：缺 confirm、dry_run 行為）

## 9. Out of Scope
SOP 中不自動化的部分（需人工的步驟），明確列出原因
````

### Step 3.5 — 共通 response 形狀（寫進 spec §3 開頭，端點不重複定義）

```json
// dry_run=true（reversible / irreversible 端點統一）：
{"dry_run": true, "checks": {"<前置條件名>": {"ok": bool, "detail"?: str, "error_code"?: str}}}
// dry_run=false 成功：{"dry_run": false, ...端點專屬欄位}
```
固定 confirm token 由 spec 指定字面值，實作中放單一常數（models 層）供
service 與測試共用。

### Step 4 — 自檢（產出後逐項確認）

- [ ] SOP 每個操作都出現在 spec（或列在 Out of Scope 並給原因）
- [ ] 每個前置條件都有對應的 4xx/5xx 與 error code
- [ ] 不可逆操作都有 confirm 防護
- [ ] spec 不含「見 SOP」字樣 — 內容必須自足
- [ ] mock 初始狀態足以跑完測試計畫的所有案例

### Step 5 — 實作回饋（寫完 code 之後執行）

實作過程中發現的缺漏要回流，不是只修 code：

1. **SOP 缺錯誤碼**：實作遇到 SOP 故障排除表沒列的系統錯誤
   （例：Flashback Drop 的名稱衝突 ORA-38312）→ 補進 SOP 錯誤表＋spec §6
2. **SOP 前置條件沒有系統錯誤碼**（例：ARCHIVELOG 關閉沒有單一 ORA 碼）→
   spec 中 `error_code: null`，但 detail 必須含前置條件編號（"P1 violated: ..."）
3. **模板缺漏**：同一資訊在多個端點重複定義 → 抽成 spec 共通節，並更新本 skill
4. 修改後重跑 Step 4 自檢

## 慣例

- 沿用目標 repo 的既有模式（看 `docs/architecture/service-layering.md`、
  既有服務的 auth/config 寫法），不發明新慣例
- 外部系統指令（SQL/shell）原文保留在 repository 介面的 docstring 規格中 —
  真實實作照抄，mock 實作模擬其效果
- SOP 中「人工確認 / 業務驗證」步驟不自動化 → Out of Scope ＋ 在相鄰端點
  response 提供人工驗證所需的資訊
