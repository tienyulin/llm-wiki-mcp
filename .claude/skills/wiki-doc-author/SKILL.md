---
name: wiki-doc-author
description: 幫 app 產生/修補餵進 LLM 知識 wiki 的源頭文件 — 每個 app 一份合規 README，能產 OpenAPI 的框架（FastAPI / NestJS / Spring / DRF / Go / Rails / ASP.NET…）再附一份機器可讀規格，用 pre-commit 保持最新並檢查完整度。開發者要寫或修這些被 wiki 吃進去的文件時用。觸發詞 - "author wiki docs"、"write a README for the wiki"、"幫我寫 wiki 文件"、"fix my openapi"、"補完 openapi"、"/wiki-doc-author"。
---

# wiki-doc-author

教 agent 產生「app 餵進 LLM 知識 wiki 的源頭文件」—— 要好到讓**語意搜尋**（semantic search，
用向量比對語意而非關鍵字）和 AI agent 真的查得動。本 skill **自包含、不綁框架**：它需要的東西
（完整規範、各框架做法、lint/產生工具）全部放在這個 skill 資料夾裡。丟進任何 app repo 都能用。

> **模型 —— 一條規則。**
> **每個 app 一律寫一份合規 README。** 如果這個 app 的框架能產出 OpenAPI / Swagger 規格
> （API 的機器可讀標準），就**再附上那份規格**（`openapi.json`），讓 endpoint 精確、不用手抄。
> README 是通用源頭（用途、概覽、用法、知識）；有 OpenAPI 時它就是精準的 endpoint 層。其餘免。

本 skill **不綁 FastAPI、不綁 Python、不綁特定 wiki 後端**。規範就是純 markdown + frontmatter
（檔頭 `---` 之間的 YAML metadata），規格就是純 OpenAPI。某個 wiki 怎麼**吃進**這些，是附錄一節
（`references/contract.md` 的 §Ingestion）—— 寫作規則本身獨立成立。

## 什麼叫好（先讀這段 —— 這才是重點）

這些文件是給**語意搜尋和 AI agent** 看的，不只給人。所以「過關」不是「把範本填滿」，而是：

- **第一段要配得上被放進索引。** 它就是被 embed（轉成向量）的那段文字。要用一兩句白話講清楚
  *這服務/這篇在幹嘛、什麼時候會用到它* —— 用使用者會拿去搜尋的字眼。不是「這是 Payments API」，
  而是「對已存信用卡扣款、退款給客戶」。把標題重講一遍＝浪費掉那個 embedding。
- **每個 endpoint 的描述講意圖，不是語法。** `POST /payments/refund — 退款給客戶` 勝過
  `POST /payments/refund — 退款端點`。path 讀者看得到，你要講*它做什麼、為什麼*。這一句就是語意
  搜尋拿去比對的料。
- **知識文件誠實分類**（Diátaxis，見下）—— 「怎麼救回誤刪資料」要找到 how-to，不是概念長文。
- **有範例、有錯誤情況**就盡量放（框架能帶就帶）—— 這對 AI 讀者價值最高（它學到的是形狀，不只名字）。

只把範本弄到 linter 過、卻沒做到上面這些，就是沒做到真正的事。要為對面那個 agent 最佳化。

## Step 0 — 選模式（每個 repo 各自選，不是全域）

判斷這個 app 能不能產 OpenAPI。**別用猜的 —— 針對這個 app 的框架去試。**
`references/frameworks.md` 有各框架（FastAPI / NestJS / Spring Boot / Django+DRF / Go / Rails /
ASP.NET / express…）的確切指令，以及各自怎麼讓 committed 的規格保持最新。

- **產得出規格**（任何能出 OpenAPI 的框架）→ **Mode A**：README 專注用途/概覽；endpoint 由
  committed 規格帶。接上 freshness + completeness（Step B/C）。
- **產不出**（框架不行，或根本不是 HTTP API）→ **Mode B**：README 自己寫一段 Endpoints，wiki 從
  那幾行抽取。一樣完整支援。

常見 ASGI/WSGI 情況（FastAPI / Starlette，凡是有 `.openapi()` 的）離線快速測：
```bash
python scripts/gen_openapi.py --app <module>:<attr>   # 例 app.main:app — 寫出 openapi.json；不適用就 exit 0（跳過）
```
產不出時它**不會擋** —— 只會告訴你改走 Mode B。其他生態系（build plugin、CLI 匯出器等）看
`references/frameworks.md` 的對應做法。

## 能力（依情況用）

### A. write-readme —— 一律要
產一份合規 README。**完整規範**（frontmatter 欄位、受控詞彙、body 規則）在
`references/contract.md`；範本在 `references/templates.md`。
- frontmatter：`type`（`api` ｜ `tutorial` ｜ `how-to` ｜ `reference` ｜ `explanation`）+
  `source_app` + 選填 `tags`。
- body：H1；**第一段＝被 embed 的摘要**（見「什麼叫好」）；一段用法；**只有 Mode B 才加**
  Endpoints 區，每行 `METHOD /path — 意圖`。
- 驗證：`python scripts/lint_frontmatter.py <file>` 必須過。

### B. wire-openapi —— Mode A
讓 committed 的規格永遠最新、每次 push 都正確，**不用手動匯出**。機制是通用的（commit 時順手重生
規格、檢查完整度）；*指令*依框架而定 —— 見 `references/frameworks.md`。`.openapi()` 那種情況，把
內附的 `gen_openapi.py` + `openapi_completeness.py` 接成 `local` pre-commit hook
（`references/templates.md` 有 `.pre-commit-config.yaml`）。結果：push 當下 repo 裡的規格永遠跟
程式碼一致。

### C. api-complete —— 在原始碼補缺漏
找出 AI 讀者缺的東西，並在**源頭**補（不是改產出的規格）：
```bash
python scripts/openapi_completeness.py openapi.json --fail
```
每個缺漏（endpoint/param 沒描述、缺 request/response 範例、缺 error schema）：**規格由 code 生，
所以改 code 不是改 `openapi.json`**（它會被蓋掉）。`references/contract.md` 的 §api-complete 列出
各框架每種缺漏該補在哪（route/operation 標註、參數描述、schema/範例、error response）。
草擬文字 → 給開發者確認 → 改 code → 重生 → completeness 歸零。

### D. knowledge —— 非 API 的散文
用 **Diátaxis** 分類、摘要先行：
- `tutorial`（帶著學）· `how-to`（解決特定問題）· `reference`（查閱事實）· `explanation`（概念/背景）。
  依**讀者意圖**選，不是依主題。
- frontmatter + 第一段當摘要的 body（範本見 `references/templates.md`）；用 `lint_frontmatter.py` 驗。

## 完成定義
- README 合規（`lint_frontmatter.py` 過），第一段是真的意圖摘要。
- Mode A：committed `openapi.json` 跟 code 一致、completeness 乾淨、freshness 接好（會持續維持）。
- 文件在目標 wiki 裡能用「意圖」查到（用使用者會打的句子搜，不是用標題）。某 wiki 怎麼吃/查：
  `references/contract.md` §Ingestion。

深入：`references/contract.md`（規範）、`references/frameworks.md`（各框架做法）、
`references/templates.md`（範本 + push）。工具：`scripts/`（純 stdlib、無相依）。
