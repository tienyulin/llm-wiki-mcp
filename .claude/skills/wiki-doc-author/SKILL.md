---
name: wiki-doc-author
description: Author or fix the source docs an app feeds into the LLM Wiki (llm-wiki-mcp) — a compliant README, and for FastAPI apps an always-fresh openapi.json plus completeness gating. Trigger - "幫我寫 wiki 文件", "wiki doc", "author readme for wiki", "補完 openapi", "/wiki-doc-author", or when a developer needs to produce/fix the first-version docs pushed to wiki-processor.
---

# wiki-doc-author

教 agent 產生/修補「app 餵進 LLM Wiki 的源頭文件」。標準的**單一真相**是平台的
`docs/guides/authoring-source-docs.md`；本 skill 是它的可執行流程。工具在 `ci-templates/`
（純 stdlib）：`gen_openapi.py`、`lint_frontmatter.py`、`openapi_completeness.py`、
`check_openapi_fresh.py`。

> 核心原則：**每個 app 一律寫一份合規 README**；能產 OpenAPI 的 app **另附最新 openapi.json**
> （pre-commit 保持同步，endpoint 不用手抄）。

## Step 0 — 偵測模式（先做）

試著離線取得 OpenAPI（**不啟動服務**）：
```bash
python -c "import json,importlib; m='<module>:<attr>'.split(':'); \
  app=getattr(importlib.import_module(m[0]), m[1]); print(len(app.openapi()['paths']),'paths')"
```
- 成功（FastAPI 等）→ **Mode A**：README 專注用途 + 接 OpenAPI hook + 可 api-complete。
- 失敗/不是 → **Mode B**：README 內含手寫 endpoint 區。
（`<module>:<attr>` 是 uvicorn target，如 `app.main:app`；開發者通常知道。）

## 能力（依情況用）

### A. write-readme（一律要）
依標準產 README（見 `references/templates.md`）：
- frontmatter：`type`（api ｜ tutorial ｜ how-to ｜ reference ｜ explanation）、`source_app`（小寫-連字號）、選填 `tags`。
- body：H1；**第一段＝一句話用途/摘要**（會被 embed，影響語意搜尋，務必寫好）；使用方式。
- **Mode B 才加** Endpoints 區：每行 `METHOD /path — 用途`。
驗證：`python ci-templates/lint_frontmatter.py <file>` 必須 pass。

### B. wire-openapi（Mode A）
產 `.pre-commit-config.yaml`（見 `references/templates.md`）接上 `gen-openapi` +
`openapi-completeness` + `frontmatter-lint` hook；把 `gen_openapi.py` 等放進 app 的 `scripts/`。
commit 時 openapi.json 自動重生並納入 → push 上去就是最新。

### C. api-complete（補完缺漏）
```bash
python ci-templates/openapi_completeness.py openapi.json --fail
```
對每個缺漏（endpoint/param 沒 description、缺 request/response 範例、缺 error schema）：
- **補在程式碼**，不是改 openapi.json（它由 code 生，會被蓋掉）：
  - endpoint：route decorator 的 `summary="..."` / `description="..."`（或函式 docstring）。
  - 參數：FastAPI `Query(..., description="...")` / `Path(...)` / Pydantic `Field(..., description="...")`。
  - 範例：`responses={200: {"content": {"application/json": {"example": {...}}}}}` 或 Pydantic
    `model_config = {"json_schema_extra": {"example": {...}}}`。
  - error：在 `responses` 補 4xx/5xx + schema。
- 草擬建議文字 → 給開發者確認 → 改 code → 重生 → completeness 歸零。

### D. knowledge（非 API 的散文）
判 Diátaxis `type`：tutorial（帶著做）/ how-to（解決問題）/ reference（查閱）/ explanation（概念）。
產 frontmatter + **摘要先行** body（見 `references/templates.md`）。`lint_frontmatter.py` 驗證。

## 完成定義
- README 合規（lint pass）。
- Mode A：openapi.json 與 code 一致（`check_openapi_fresh.py`）、completeness 過、hook 接好。
- push 到 wiki-processor 成功、能在 wiki 查到（`search_apis` / `search_knowledge`）。

細節範本與 push 方式：`references/templates.md`。
</content>
