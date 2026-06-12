---
name: sop-to-spec
description: Convert an operations SOP (any domain — DBA runbooks, infra procedures, deployment checklists) into an implementation-ready API spec markdown that an AI agent can build a three-layer FastAPI service from, without re-reading the SOP. Trigger - "SOP 轉 spec", "convert SOP", "/sop-to-spec <path>", or when the user wants to turn a procedure document into an API.
---

# SOP → Implementation Spec（v4）

> 調優紀錄與每版的缺陷歸因見 `specs/REVIEWS.md`。

把人類操作 SOP 轉成 **AI agent 可以直接照著寫 code 的 API spec markdown**。

**鐵律：spec 是唯一交接物。** 寫 code 的 agent 只讀 spec——所以：
1. SOP 裡實作需要的資訊（指令、錯誤碼、前置條件）全部 inline 進 spec
2. spec **禁止引用 SOP 與自身以外的任何檔案或慣例**。「比照 xxx 服務」「見
   service-layering.md」都不行——在沒有那些檔案的全新 repo 也要能照 spec 開工。
   需要的慣例（auth 模式、DI 模式）把內容寫出來
3. 實作中發現 spec 沒定義的行為 = spec 的 bug，不是 code 自由發揮的空間

## 輸入 / 輸出

- 輸入：SOP 檔案路徑（`$ARGUMENTS` 或使用者指定）
- 輸出：`specs/<sop-slug>-api.spec.md`

## 流程總覽

```
Step 1 萃取 → Step 2 風險分級 → Step 3 產 spec（含逼問清單）
→ Step 4 自檢 → Step 5 盲審閘門（過了才准寫 code）
→ [實作] → Step 6 實作回饋（缺陷歸因回流）
```

## Step 1 — 萃取（讀 SOP，列五張清單）

1. **查詢類**：所有「檢查/查詢/確認」動作 → 候選 GET
2. **操作類**：所有改變系統狀態的動作 → 候選 POST/DELETE
3. **前置條件**：每個操作前必須成立的條件＋檢查方式＋違反時的系統錯誤碼
4. **錯誤對照**：SOP 故障排除表（錯誤碼→原因→處置）
5. **審計要求**：SOP 要求留存的欄位

## Step 2 — 風險分級

| 等級 | 判斷標準 | API 防護 |
|------|---------|---------|
| `read` | 純查詢 | 無 |
| `reversible` | 可被另一操作撤銷（SOP 有回退步驟） | `dry_run` 預設 `true`；執行 response 必含回退所需資訊（操作前狀態） |
| `irreversible` | SOP 標示不可逆/需審批/警告 | `dry_run` 預設 `true` ＋ 必填 `confirm` 固定 token ＋ 必填審批欄位；缺一回 428 |

SOP 操作耗時數分鐘以上（停機、重啟、大量資料）→ spec 必須明定 sync 或
202+輪詢 job 模式，並寫出選擇理由。

## Step 3 — 產出 spec（固定模板，每節必填）

### 3a. 標準閘門順序（寫進 spec §0，全端點一體適用，端點不得自定）

```
1. auth                  → 401（缺/錯 API key；read 端點免）
2. schema 驗證           → 422（pydantic：必填、型別、互斥輸入）
3. 資源解析              → 404（路徑/body 指到的資源不存在）
4. 風險閘門              → 428（irreversible 且 dry_run=false：confirm/審批缺漏）
5. 前置條件              → 409（領域狀態不允許）
6. 執行
dry_run=true：跑 1–3（404 照常擲出），接著執行閘門 5 的全部檢查但以
「收集不擲出」模式填進 checks；閘門 4 與 6 完全跳過
```
（dry_run 行為這句**照抄進 spec**，不要改寫——兩輪盲審都在這裡誤讀過改寫版）

### 3b. 統一 response 形狀（spec §0，端點只補專屬欄位）

```json
// dry_run=true：
{"dry_run": true,
 "checks": {"<條件名>": {"ok": bool, "detail"?: str, "error_code"?: str}},
 ...端點唯讀附加資訊（如預估值）}
// dry_run=false 成功：{"dry_run": false, ...端點專屬欄位}
// 錯誤（統一 exception handler）：{"detail": str, "error_code": str|null}
```
固定 confirm token 由 spec 給字面值；實作放單一常數（models 層）。

### 3c. 每端點 = EARS 驗收準則（核心改變）

每個端點不寫散文，寫**編號驗收準則**，格式：

```
AC-<端點代號>-<序號>: WHEN <條件> THE SYSTEM SHALL <可驗證的行為>
```

覆蓋三類，缺一不可：
- **happy**：正常輸入 → 確切的 response 欄位與狀態變化
- **edge**：每個 optional 欄位為 None/省略時、每個邊界值（用 ≥ ≤ < > 明確寫，
  禁止「以內」「之後」這種含糊詞）
- **failure**：每個前置條件違反 → HTTP code ＋ error_code

加上 request/response 的 **formal JSON 區塊**（含範例值），不收散文 schema。

### 3d. 逼問清單（產 spec 時逐端點回答，答案寫進 AC——不准留白）

- 每個 **optional 欄位**：None 時行為？
- 每個**比較**：邊界含不含等號？
- 每個**替代輸入形式**（如 scn vs timestamp vs name）：
  **誰負責解析成 canonical 形式？用什麼方法？解析失敗回什麼？**
  每個替代形式都要有自己的 AC——不能只給其中一種寫行為
- **dry_run** response 裡有哪些欄位？回退資訊（如 prior state）在 dry_run 給不給？
- 操作**耗時**？sync 或 202？timeout？
- **並發**：兩個請求同時打同一資源會怎樣？（至少要寫「以狀態機擋」或「未防護，
  風險說明」）
- **重複呼叫**（idempotency）：同請求打兩次，第二次回什麼？
- **輔助性 mutation**（如自動修復前置條件的 ALTER）：必須在**其餘全部前置條件
  確定通過後**才執行——注定失敗的請求不得留下副作用
- **操作後的「結果狀態」欄位**：鏈式/遞迴情境下指什麼？（例：移除最新
  delete marker 後浮上來的可能還是 marker——爬不爬鏈要明寫）
- dry_run response 的預測範圍：執行後才知道的值（新 etag、新 id）**不預測**，
  明寫哪些欄位 dry_run 不給
- 固定文案/token：spec 給字面值，實作集中於單一常數模組（models 層），
  spec 寫明確切檔名

### 3e. 狀態機（有狀態實體必畫）

任何實體有 >1 個狀態值（如 db_state）→ 給轉移表：

| 目前狀態 | 端點 | 結果狀態 | 其他狀態下呼叫 → |
|---------|------|---------|------------------|

### 3f. 其餘必填節

- **Domain Model**：實體欄位與型別（→ pydantic model 與 mock 狀態）
- **三層落點**：目錄樹＋repository 介面（每個外部呼叫一個方法，docstring 寫原始
  指令；**必須有 mock 實作**，`MOCK_<SYSTEM>=true`，mock 初始狀態與每個方法的
  模擬效果寫死在 spec——含解析類方法如 timestamp→SCN 的 mock 換算公式）。
  **repository 永不擲業務錯誤**：查無回空值/None，404/409 判定一律在 service
- **DI 與 auth 模式**：把模式內容寫出來（lazy lru_cache providers ＋ Depends、
  API key request 時讀 env、lifespan warm-up fail-fast）——不引用外部檔案
- **設定**：環境變數表（含預設值與合法範圍）
- **錯誤模型**：SOP 故障排除表整張搬入；SOP 沒給系統錯誤碼的前置條件
  → `error_code: null`，但 detail 必含前置條件編號（"P1 violated: ..."）
- **審計**：欄位 schema＋寫入時機（所有非 read，含 dry_run 與被拒；result 字串
  模式枚舉：`success` / `dry_run` / `rejected:<error_code或原因>` / `error:<msg>`）
- **測試計畫**：每條 AC ≥1 測試，測試名含 AC 編號；另列 mock 狀態操縱類案例
- **Out of Scope**：SOP 中不自動化的步驟＋原因＋API 的替代支援

## Step 4 — 自檢

- [ ] SOP 每個操作都在 spec（或 Out of Scope＋原因）
- [ ] 每條 AC 可單獨驗證（有確切的輸入、HTTP code、欄位值）
- [ ] 每個端點 happy/edge/failure 三類 AC 都有
- [ ] 逼問清單（3d）每題每端點都有對應 AC
- [ ] **fresh-repo 測試**：通讀 spec，任何「比照」「見」「沿用」指向 spec 外
      （SOP 編號除外）→ 改成 inline
- [ ] mock 初始狀態足以執行測試計畫全部案例

## Step 5 — 盲審閘門（寫 code 前，必過）

派一個**乾淨 context 的 agent**（不給 SOP、不給 repo 背景），只讀 spec，要求：
「列出實作者必須猜測或發明的每一處，分 HIGH/MED/LOW」。

- HIGH > 0 → 修 spec、重審。**不准開工。**
- 審畢將發現與處置記入 `specs/REVIEWS.md`（迭代紀錄）。

## Step 6 — 實作回饋（寫完 code 之後）

每個實作中發現的缺陷做**歸因**，修對應層（不是只修 code）：

| 歸因 | 動作 |
|------|------|
| SOP 缺資訊（如錯誤碼缺漏） | 補 SOP ＋ spec |
| skill 模板沒逼問到 | 改本 skill（模板/逼問清單）＋ 重產 spec |
| spec 產出沒照模板 | 重產 spec 該節 |
| 純 code bug | 修 code ＋ 補 AC 對應測試 |

修完重跑 Step 4 自檢；重大修改重跑 Step 5 盲審。全程記入 `specs/REVIEWS.md`。
