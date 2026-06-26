# 源頭文件規範（contract）

「app 餵進 LLM 知識 wiki 的文件」的單一、自包含定義。**不綁框架、不綁後端。**（某個特定 wiki
怎麼吃這些，放在最後的 **§Ingestion** 附錄 —— 上面的規則本身獨立成立。）

名詞：**OpenAPI** = HTTP API 形狀的機器可讀標準（很多框架能自動產）；**frontmatter** = markdown
檔頭 `---` 之間那段 YAML metadata；**Diátaxis** = 依「讀者意圖」把文件分四類的方法。

## 核心規則：每個 app 寫 README；框架能產 OpenAPI 就再附上

| | 一律要 | 能產就加 |
|---|---|---|
| **README**（每個 app 一份） | ✅ | |
| **openapi.json**（能產 OpenAPI 的 app） | | ✅ |

- **README** 是通用源頭：用途、概覽、用法，以及（沒有 OpenAPI 的 app）一段手寫 endpoint 清單。
- **openapi.json** 帶精準 endpoint（method/path/params/範例/error）。框架能產就附上，**別手抄 endpoint**。
- 一次 push 帶 README markdown ＋（可選）OpenAPI 規格。有規格 → wiki 用它拿精準 endpoint；沒有 →
  從 README 抽 endpoint。README 的概覽永遠會被用到。

## README 格式

```markdown
---
type: api                    # 必填。api | tutorial | how-to | reference | explanation
source_app: payments-api     # 必填。穩定的 app 識別（小寫、連字號）
tags: [billing, payments]    # 選填。受控詞彙（小寫、連字號）
---

# Payments API

對已存信用卡扣款、退款給客戶。   ← 第一段＝被 embed 的摘要

## 使用方式
...

## Endpoints        ← 只有「沒有 openapi.json」的 app 才需要這段
POST /payments/charge — 對已完成購買的已存卡扣款
POST /payments/refund — 退款給客戶
```

- **第一段是整份檔案最重要的一行。** 它是被 embed（轉向量）拿去搜尋的那段。用使用者的字眼講清楚
  用途與何時會用到。別把 H1 重講一遍。
- **有** `openapi.json` 的 app：README 專注用途/概覽/情境 —— 省略 Endpoints 區（endpoint 歸規格管）。
- `type`：API 服務用 `api`，散文用下面知識四類其一。

## 知識文件（不是 API spec 的散文）—— Diátaxis

依**讀者意圖**選 `type`，不是依主題：

| type | 是什麼 | 例 |
|---|---|---|
| `tutorial` | 帶著做、課程式 | 「第一次部署 X」 |
| `how-to` | 解決一個特定問題 | 「誤刪後救回資料」 |
| `reference` | 查閱用事實 | 「設定參數一覽」 |
| `explanation` | 概念/背景 | 「Oracle Flashback 原理」 |

```markdown
---
type: how-to
source_app: oracle-kb
tags: [oracle, recovery]
---

# 救回誤刪的資料

當資料被誤刪，用 Oracle Flashback 在不還原備份下回溯。   ← 第一段＝摘要

## 步驟
- ...
```

## 受控詞彙（避免各寫各的）

- `type`：只能是 `api | tutorial | how-to | reference | explanation` 其一。其餘 linter 擋下。
- `tags`：小寫 + 連字號（`incident-response`，不是 `IncidentResponse`）。團隊維護一份清單。
- `source_app`：小寫、字母數字開頭、可含連字號。
- 規則由 `scripts/frontmatter.schema.json`（JSON Schema）定義、`scripts/lint_frontmatter.py` 強制。
  放進 pre-commit 跑。

## 讓 OpenAPI 保持最新（每次 push 都正確）

規格是**從 code 生的**，所以唯一要的紀律是「commit 時順手重生」—— 沒有另外一個會忘記的手動匯出
步驟。機制通用、指令依框架（見 `references/frameworks.md`）。凡是 app 物件有 `.openapi()` 的框架
（FastAPI/Starlette），內附 `scripts/gen_openapi.py` 在 `local` pre-commit hook 裡做這件事；
`scripts/openapi_completeness.py` 把缺描述/範例/error 的擋在 commit 當下，缺漏不會流到 wiki。
CI 防呆（`check_openapi_fresh` 模式）重生再 diff，防有人沒裝 hook。現成
`.pre-commit-config.yaml` 見 `references/templates.md`。

## api-complete —— 每種缺漏該補在原始碼哪裡

規格跟著 code，所以缺漏要在 code 補（直接改 `openapi.json` 下次重生會被蓋）。依框架家族：

| 缺漏 | FastAPI（Python） | Spring（Java） | NestJS（TS） | DRF（Python） | 通則 |
|---|---|---|---|---|---|
| endpoint 描述 | route 上 `summary=`/`description=` 或 docstring | `@Operation(summary=…, description=…)` | `@ApiOperation({summary})` | `@extend_schema(summary=…)` | 該 operation 的標註/doc |
| 參數描述 | `Query(..., description=…)` / `Path(...)` | `@Parameter(description=…)` | `@ApiQuery({description})` | serializer 欄位 `help_text` | 該參數的標註 |
| request/response 範例 | `responses={200:{"content":{...:{"example":…}}}}` 或 Pydantic `json_schema_extra` | `@ExampleObject` / schema `example` | `@ApiResponse({ schema })` | `examples=[OpenApiExample(...)]` | schema 的 `example`/`examples` |
| error response | 在 `responses` 加 4xx/5xx + schema | `@ApiResponse(responseCode="409", …)` | `@ApiResponse({ status, type })` | `@extend_schema(responses={409: …})` | 宣告 error 狀態碼 + schema |

改完 code：重生規格，再跑 `openapi_completeness.py openapi.json --fail` 到乾淨。

## 一句話

**每個 app：一份合規 README，第一段用一句可搜尋的話講清用途。能產 OpenAPI 的 app 再附一份
pre-commit 保持最新的 `openapi.json`。其餘交給 wiki。**

---

## §Ingestion —— llm-wiki 後端怎麼吃這些（附錄；綁特定後端）

這是唯一綁特定 wiki 的部分。別的後端會不同；上面的寫作規則不受影響。

- push 目標：`POST <wiki-processor>/process`，body
  `{"markdowns": {"README.md": "<text>"}, "source_app": "<name>", "source_version": "<sha>",
  "openapi": <規格 dict，選填>, "timestamp": "...", "trigger_info": {...}}`。
- 有 `openapi` → endpoint 從規格**確定性**匯入（不走 LLM、不撞限流、不幻覺）；沒有 → README 的
  `METHOD /path — 意圖` 行由 LLM 抽取。README 第一段兩種情況都會被 embed 做語意搜尋。
- frontmatter 的 `type`/`tags` 會存起來、可查（`search_knowledge?type=how-to`、`search_apis`）。
  本地 push 片段見 `references/templates.md`；自動化路徑見 CI 範本 `generate-and-push-wiki.yml`。
