# 範本與細節

## README — Mode A（有 openapi.json）

```markdown
---
type: api
source_app: payments-api
tags: [billing, payments]
---

# Payments API

收款與退款服務：對已存信用卡扣款、退款給客戶。   ← 第一段＝摘要（被 embed）

## 使用方式
- 設定 `PAYMENTS_API_KEY`；base URL `…`。

（endpoint 不用寫 —— 由 committed openapi.json 帶，processor 走確定性轉換）
```

## README — Mode B（沒有 OpenAPI，手寫 endpoint）

```markdown
---
type: api
source_app: legacy-billing
tags: [billing]
---

# Legacy Billing API

對舊系統收款。   ← 摘要

## Endpoints
POST /charge — 對信用卡扣款收取款項
POST /refund — 退款給客戶
GET  /balance — 查目前餘額
```
- 每行 `METHOD /path — 用途`；`— 用途` 那句會被 LLM 當 description（影響語意搜尋），寫清楚。

## 知識文件

```markdown
---
type: how-to
source_app: oracle-kb
tags: [oracle, recovery]
---

# 從誤刪救回資料

當資料被誤刪，用 Oracle Flashback 在不還原備份下回溯。   ← 第一段＝摘要

## 步驟
- ...
## 注意
- ...
```
- `type` 用 Diátaxis：tutorial / how-to / reference / explanation。

## .pre-commit-config.yaml（Mode A）

```yaml
repos:
  - repo: local
    hooks:
      - id: gen-openapi
        name: regenerate openapi.json
        entry: python scripts/gen_openapi.py --app app.main:app
        language: system
        pass_filenames: false
        always_run: true
      - id: openapi-completeness
        name: openapi completeness gate
        entry: python scripts/openapi_completeness.py --fail
        language: system
        pass_filenames: false
        always_run: true
      - id: frontmatter-lint
        name: frontmatter lint
        entry: python scripts/lint_frontmatter.py
        language: system
        files: '\.md$'
```
把 `ci-templates/{gen_openapi,openapi_completeness,lint_frontmatter,frontmatter.schema}.{py,json}`
複製進 app 的 `scripts/`（schema 與 lint 同目錄）。

## 推送到 wiki（本地測試 / CI）

```bash
python - <<'PY'
import json, os, urllib.request
md = {"README.md": open("README.md", encoding="utf-8").read()}
body = {"markdowns": md, "timestamp": "t", "trigger_info": {},
        "source_app": "payments-api", "source_version": "local"}
if os.path.exists("openapi.json"):
    body["openapi"] = json.load(open("openapi.json", encoding="utf-8"))   # 有就附上 → 確定性匯入
req = urllib.request.Request("http://localhost:8001/process",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req, timeout=120))["status"])
PY
```
正式環境由 CI 範本 `ci-templates/generate-and-push-wiki.yml` 自動做（push 時附 committed openapi.json）。

## 驗證查得到
```bash
curl 'localhost:8002/search_apis?query=退款給客戶'
curl 'localhost:8002/search_knowledge?query=救回資料&type=how-to'
```

## api-complete：缺漏補在哪（對照）

| 缺漏 | 補在程式碼 |
|---|---|
| endpoint 沒 description | route decorator `summary=`/`description=` 或函式 docstring |
| 參數沒 description | `Query(..., description=...)` / `Path(...)` / Pydantic `Field(..., description=...)` |
| 缺範例 | `responses={200: {"content": {"application/json": {"example": {...}}}}}` 或 Pydantic `json_schema_extra` |
| 缺 error | `responses` 補 4xx/5xx + schema |

改完跑 `python scripts/gen_openapi.py --app <module:attr>` 重生，再 `openapi_completeness.py --fail` 確認歸零。
</content>
