# 源頭文件標準（怎麼產第一版給 wiki）

> 這是「app 要怎麼產生餵給 wiki-processor 的源頭文件」的**單一真相**。CI 範本、pre-commit
> hook、`wiki-doc-author` skill、MCP 的 authoring-contract resource 全部引用這份。
>
> 名詞：**OpenAPI** API 的機器可讀標準規格（FastAPI 自動產）；**frontmatter** markdown 最上面
> `---` 之間的 YAML metadata；**Diátaxis** 文件四分類法；**OKF** Google Open Knowledge Format。

## 核心原則：README 一律寫 ＋ OpenAPI 有就加

| | 一律要 | 有就加 |
|---|---|---|
| **README**（每個 app 一份） | ✅ | |
| **openapi.json**（能產的 app） | | ✅ |

- **README** = 通用源頭：用途、概覽、使用方式（沒有 OpenAPI 的 app 再加 endpoint 清單）。
- **openapi.json** = 精準 endpoint（method/path/params/範例/error）。能產就附上，endpoint 不用手抄。
- 一次 push 同時帶 README markdown ＋（可選）openapi。processor：有 openapi → endpoint 走**確定性
  轉換**（準、免 LLM、免限流）；沒有 → README 的 endpoint 由 LLM 抽取。README 永遠提供 overview。

---

## README 格式

```markdown
---
type: api                    # 必填。api ｜ tutorial ｜ how-to ｜ reference ｜ explanation
source_app: payments-api     # 必填。app 識別（也用於 wiki 的 per-app 物件）
tags: [billing, payments]    # 選填。受控詞彙（小寫、連字號）
---

# Payments API

收款與退款服務。處理對已存信用卡扣款、以及退款給客戶。   ← 第一段＝一句話用途/摘要（會被 embed，影響搜尋）

## 使用方式
...

## Endpoints        ← 只有「沒有 openapi.json」的 app 才需要這段
POST /payments/charge — 對已存信用卡扣款收取一筆已完成購買的款項
POST /payments/refund — 退款給客戶
```

- **第一段最重要**：它是語意搜尋的料，寫清楚「這服務/這篇在幹嘛」。
- 有 openapi.json 的 app：README 專注用途/概覽/情境，**endpoint 區可省**（交給 openapi）。
- `type` 受控值：`api`（API 服務）或知識四類（見下）。

---

## 知識文件（不是 API spec 的散文）

用 **Diátaxis** 四分類當 `type`：

| type | 是什麼 | 例 |
|---|---|---|
| `tutorial` | 帶著做、學習導向 | 「第一次部署 X」 |
| `how-to` | 解決特定問題 | 「怎麼從誤刪救回資料」 |
| `reference` | 查閱用的事實 | 「設定參數一覽」 |
| `explanation` | 概念/背景 | 「Oracle Flashback 原理」 |

```markdown
---
type: how-to
source_app: oracle-kb
tags: [oracle, recovery]
---

# 從誤刪救回資料

當資料被誤刪時，用 Oracle Flashback 在不還原備份的情況下回溯。   ← 第一段＝摘要

## 步驟
- ...
```

---

## OpenAPI：怎麼讓它「push 時就最新」

FastAPI **預設就有** OpenAPI（從你的 route/參數/Pydantic model 即時算），不必加東西。
用 **pre-commit hook** 讓 committed 的 `openapi.json` 永遠最新：

```yaml
# app 的 .pre-commit-config.yaml（Mode A：能產 OpenAPI）
- repo: local
  hooks:
    - id: gen-openapi                 # 重生 openapi.json 並納入這次 commit
      name: regenerate openapi.json
      entry: python scripts/gen_openapi.py --app app.main:app
      language: system
      pass_filenames: false
      always_run: true
    - id: openapi-completeness        # 缺 description/範例/error → 擋下 commit
      name: openapi completeness gate
      entry: python scripts/openapi_completeness.py --fail
      language: system
      pass_filenames: false
      always_run: true
    - id: frontmatter-lint            # README frontmatter 合規
      name: frontmatter lint
      entry: python scripts/lint_frontmatter.py
      language: system
      files: '\.md$'
```

```yaml
# Mode B：沒有 OpenAPI（手寫 markdown）
- repo: local
  hooks:
    - id: frontmatter-lint
      name: frontmatter lint
      entry: python scripts/lint_frontmatter.py
      language: system
      files: '\.md$'
```

- `gen_openapi.py --app module:attr`：import 你的 app；**不是 FastAPI/不能產就優雅跳過、不擋 commit**。
- `openapi-completeness`：endpoint/param 缺 description、缺範例、缺 error schema → 擋下，提示用
  `wiki-doc-author` skill 補完（補在**程式碼**的 `summary=`/`description=`/Pydantic `Field`，因為
  openapi 由 code 生）。
- CI 另跑 `check_openapi_fresh.py` 防呆（有人沒裝 hook → committed 過期就 fail）。

這些腳本在 `ci-templates/`，`wiki-doc-author` skill 會幫你接好。

---

## 受控詞彙（避免各寫各的）

- `type`：`api | tutorial | how-to | reference | explanation`（其餘一律 lint 擋下）。
- `tags`：小寫 + 連字號（`incident-response`，不是 `IncidentResponse`）。團隊維護一份清單。
- frontmatter 規則由 `ci-templates/frontmatter.schema.json`（JSON Schema）定義，`lint_frontmatter.py` 強制。

---

## 一句話

**每個 app：寫一份合規 README（第一段講清楚用途）；能產 OpenAPI 的，pre-commit 自動附上最新
openapi.json。其餘交給 wiki。** 不會的就叫 `wiki-doc-author` skill 幫你寫。
</content>
