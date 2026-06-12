# Spec 模板（sop-to-spec v5）

產出檔：`specs/<sop-slug>-api.spec.md`。結構固定兩部分：Part A 給人類審批者
（白話、技術無關），Part B 給實作 agent（精確、零猜測）。**先寫 Part A**——
寫不出白話摘要代表你還沒讀懂 SOP。

## 風險分級（Step 2）

| 等級 | 判斷標準 | API 防護 |
|------|---------|---------|
| `read` 🟢 | 純查詢 | 無 |
| `reversible` 🟡 | 可被另一操作撤銷（SOP 有回退步驟） | `dry_run` 預設 `true`；執行 response 必含回退所需資訊（操作前狀態） |
| `irreversible` 🔴 | SOP 標示不可逆/需審批/警告 | `dry_run` 預設 `true` ＋ 必填 `confirm` 固定 token ＋ 必填 `approval_id`；缺一回 428 |

SOP 操作耗時數分鐘以上（停機、重啟、大量資料）→ 明定 sync 或 202+job 模式，
寫出選擇理由。

---

## Part A — 審批摘要（白話，禁止 EARS/JSON/狀態機術語）

```markdown
# <名稱> API Spec

> 來源 SOP：<路徑>（<編號>）｜產生方式：.claude/skills/sop-to-spec
> **Part A 給審批者（看完這節即可決定簽不簽）；Part B 給實作 agent。**

## A1. 這個 API 做什麼（三句話以內）
把 <SOP 名> 的人工操作包成 API：哪些事可以用它做、給誰用。

## A2. 端點一覽（白話）
| 端點 | 一句話說明 | 風險 |
|------|-----------|------|
| GET /...  | 查 ○○ | 🟢 查詢 |
| POST /... | 做 ○○，做之前會先檢查 ○○ | 🟡 可逆 |
| POST /... | ○○，**做了就回不去**，需要審批單號 | 🔴 不可逆 |

## A3. 三個典型情境（Given/When/Then 白話）
情境一「<名稱>」：
- Given <現況>
- When 呼叫 <端點>（先 dry_run 看檢查結果，再真的執行）
- Then <結果>，audit 留下紀錄

（至少三個，必含一個不可逆操作的完整流程＋一個被擋下的失敗情境）

## A4. 安全防護（白話）
- 所有「會動到東西」的操作預設只試算不執行（dry_run）
- 不可逆操作要打兩個通關密語：固定確認字串 ＋ 變更審批單號，缺一不執行
- 每個操作（含試算、被拒絕的）都留審計紀錄：誰、何時、對什麼、結果

## A5. 不自動化的事（仍需人工）
| SOP 步驟 | 為什麼不自動化 | API 給的替代支援 |

## A6. 審批者簽核點
簽核這份 spec = 同意 A2 的端點範圍、A4 的防護等級、A5 的人工保留項。
```

## Part B — 實作規格（給 agent，零猜測）

### §0 全域規則

**閘門順序**（照抄，不要改寫——兩輪盲審都在改寫版上誤讀過）：

```
1. auth        → 401（mutation 端點缺/錯 API key；read 端點不驗）
2. schema 驗證 → 422（pydantic：必填、型別、互斥輸入）
3. 資源解析    → 404（請求指到的資源不存在；dry_run 也 404）
4. 風險閘門    → 428（irreversible 且 dry_run=false：confirm/審批缺漏）
5. 前置條件    → 409（領域狀態不允許）
6. 執行
dry_run=true：跑 1–3（404 照常擲出），接著執行閘門 5 的全部檢查但以
「收集不擲出」模式填進 checks；閘門 4 與 6 完全跳過
```

**統一 response 形狀**：

```json
// dry_run=true：
{"dry_run": true,
 "checks": {"<條件名>": {"ok": bool, "detail"?: str, "error_code"?: str}},
 ...端點唯讀附加欄位}
// dry_run=false 成功：{"dry_run": false, ...端點專屬欄位}
// 錯誤（統一 exception handler）：{"detail": str, "error_code": str|null}
```

**全域型別約定**：時間欄位一律 ISO8601 秒精度 naive UTC；bool 欄位永遠出現；
比較性詞彙（最新、之內）給可計算定義含平手規則。

**風險閘門常數**：confirm token 給字面值，唯一出處 `models/schemas.py`；
§7.1 固定文案同樣集中常數。`approval_id` strip 後長度 > 0，驗證在閘門 4
（schema 上是 `Optional[str] = None`）。

**auth 與 DI 模式（inline 寫出，不引用外部檔案）**：`X-API-Key` ↔ env
`<SERVICE>_API_KEY` 用 `secrets.compare_digest`，**每 request 讀 env**；未設 =
dev 模式不驗。DI 用 `functools.lru_cache(maxsize=1)` providers ＋ FastAPI
`Depends`，附 `reset_singletons()` 測試 seam；`main.py` lifespan 呼叫一次
service provider warm-up（real 模式缺連線設定 → boot fail-hard）。

**同步模型與並發**：明寫 sync/202 與理由、並發防護（狀態機擋 or 「未防護＋
風險說明」）、冪等行為。

### §1 Domain Model
實體欄位與型別 → 直接變成 pydantic model 與 mock 狀態。

### §2 Endpoints 總表 ＋ 狀態機
| Method | Path | 風險 | AC 前綴 | SOP 章節 |

實體有 >1 狀態值 → 轉移表（目前狀態 × 端點 → 結果狀態；其他狀態下呼叫 → ?），
狀態檢查屬於哪個閘門要明寫（含刻意不對稱的理由）。

### §3 各端點驗收準則（EARS）

格式：`AC-<端點代號>-<序號>: WHEN <條件> THE SYSTEM SHALL <可驗證行為>`
每端點 happy/edge/failure 三類缺一不可；request/response 給 formal JSON 區塊
（含範例值）。寫每條 AC 時過一遍逼問清單（references/checklists.md）。

### §4 三層落點
目錄樹 ＋ repository 介面表（每個外部呼叫一個方法，docstring 寫原始指令；
**repository 永不擲業務錯誤**——查無回空值/None，404/409 判定在 service）＋
**mock 初始狀態與每個方法的模擬效果寫死**（含解析類方法的換算公式）。

### §5 設定
環境變數表：預設值、合法範圍、**讀取時機**（boot 快取 or 每 request）。

### §6 錯誤模型
SOP 故障排除表整張搬入（error_code → 條件 → HTTP → detail 處置建議）；
SOP 沒給系統碼的 → `error_code: null`，detail 以前置條件編號開頭。

### §7 審計
欄位 schema、寫入時機（每個 mutation request 恰好一筆；401/422 在 service 前
擋掉不留）、result 封閉枚舉 `success`/`dry_run`/`rejected:<error_code 或
snake_case 短原因>`/`error:<msg>`、各 operation 欄位對應表、§7.1 固定文案字面值。

### §8 測試計畫
每條 AC ≥1 測試、測試名含 AC 編號；mock 狀態操縱類案例；audit 三種 result
各至少一次斷言；conftest autouse `reset_singletons()`。

### §9 Out of Scope
SOP 不自動化步驟 ＋ 原因 ＋ API 替代支援（與 Part A5 一致，這裡可帶技術細節）。
