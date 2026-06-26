# 各框架怎麼產 OpenAPI 並保持最新

Step 0 用這份判斷模式。核心問題只有一個：**這個 app 的框架能不能產出 OpenAPI 規格？**
能 → Mode A（附 `openapi.json`，endpoint 不用手抄）；不能 → Mode B（README 手寫 endpoint 區）。

每個框架兩件事：(1) **怎麼離線/build 時把規格匯成檔案**（測能不能、給 hook 用）；
(2) **怎麼讓 committed 的 `openapi.json` 保持最新**（pre-commit 或 build step）。

> 通用原則：規格**從 code 生**，所以「commit 時順手重生」就保證最新。指令依框架不同，紀律相同。
> 不確定指令版本/旗標就查該框架現行文件 —— 下面是定位用的起點，不是版本鎖定。

## 有 app 物件、可呼叫 `.openapi()`（Python ASGI）

**FastAPI / Starlette / 任何暴露 `.openapi()` 的** —— 內附工具直接支援。
- 離線測 + 產檔：`python scripts/gen_openapi.py --app <module>:<attr>`（例 `app.main:app`，就是
  uvicorn target，開發者通常知道）。它 import app、呼叫 `.openapi()`、寫 `openapi.json`；不適用就
  exit 0 不擋。
- 保持最新：`gen-openapi` pre-commit hook（見 `references/templates.md`）。
- 模式：**A**。

## 其他框架（離線/build 匯出器 + freshness）

| 框架 | 匯出規格成檔（離線/build） | 保持最新 | 模式 |
|---|---|---|---|
| **NestJS**（TS/Node） | 在 bootstrap 用 `SwaggerModule.createDocument(app, config)` 拿 document，`fs.writeFileSync('openapi.json', JSON.stringify(doc))`；包成一支 `npm run gen:openapi` 腳本 | pre-commit `local` hook 跑該腳本 | A |
| **Spring Boot**（Java，springdoc-openapi） | build 期用 `springdoc-openapi-maven-plugin`（或 gradle 對應）產 `openapi.json`，**不必起服務的 runtime**（plugin 會短暫拉起 context 匯出） | 綁進 maven/gradle build；或 pre-commit 跑該 goal | A |
| **Django + DRF**（drf-spectacular） | `python manage.py spectacular --file openapi.yaml`（純離線、不起 server） | pre-commit `local` hook 跑該指令 | A |
| **Go**（swaggo/swag） | `swag init`（從註解產 `docs/swagger.json`） | pre-commit 跑 `swag init`；註解寫好就同步 | A |
| **Rails**（rswag） | 從 request specs 產：`rake rswag:specs:swaggerize` | pre-commit/CI 跑該 rake task | A |
| **ASP.NET Core**（Swashbuckle） | `dotnet swagger tofile --output openapi.json <dll> <docname>`（CLI 離線匯出） | build step 或 pre-commit | A |
| **express**（手接 swagger-jsdoc 等） | 跑產生腳本把 spec dump 成檔 | pre-commit 跑該腳本 | A |
| **不是 HTTP API / 框架無法產 OpenAPI / 不想接** | —— | —— | **B**：README 手寫 Endpoints 區 |

各列「保持最新」都是同一招：把「產規格」那個指令接成 commit 會跑的步驟（pre-commit `local` hook 最
直接），讓 push 當下檔案就跟 code 一致。CI 再跑一次重生＋diff 當防呆。

## 判斷流程

1. 上表找這個 app 的框架。
2. 有對應匯出指令 → 跑它、確認真的吐出 `openapi.json`/`.yaml` → **Mode A**。接 freshness hook
   （`references/templates.md` 的 `.pre-commit-config.yaml`，把 entry 換成該框架的指令）。
3. 沒有、或匯出失敗、或根本不是 HTTP API → **Mode B**。README 寫 Endpoints 區（每行
   `METHOD /path — 意圖`），裝 `frontmatter-lint` hook，wiki 用 LLM 抽 endpoint。
4. 兩種模式都**一律要**一份合規 README（見 `references/contract.md`）。

## Mode A 還是要寫 README

有 OpenAPI **不等於**不用 README。OpenAPI 給精準 endpoint；README 給**用途、概覽、情境**那段
被 embed 的摘要 —— 那是語意搜尋的料，規格裡沒有。Mode A 的 README 省掉 Endpoints 區即可，第一段
摘要照樣最重要。
