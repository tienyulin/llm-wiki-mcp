# 源頭文件標準（怎麼產第一版給 wiki）

> **單一真相已移至 `wiki-doc-author` skill** —— 它自包含、不綁框架、可丟進任何 app repo 用。
> 本頁只是平台內的指標，避免規範兩份漂移。

完整規範與做法看 skill：

| 要找什麼 | 看這裡 |
|---|---|
| **規範本體**（README/OpenAPI 模型、frontmatter 欄位、受控詞彙、Diátaxis、§Ingestion） | [`.claude/skills/wiki-doc-author/references/contract.md`](../../.claude/skills/wiki-doc-author/references/contract.md) |
| **各框架怎麼產 OpenAPI 並保持最新**（FastAPI / NestJS / Spring / DRF / Go / Rails / ASP.NET / express） | [`.claude/skills/wiki-doc-author/references/frameworks.md`](../../.claude/skills/wiki-doc-author/references/frameworks.md) |
| **範本 + push 方式** | [`.claude/skills/wiki-doc-author/references/templates.md`](../../.claude/skills/wiki-doc-author/references/templates.md) |
| **流程總覽**（什麼叫好、Mode A/B、四種能力） | [`.claude/skills/wiki-doc-author/SKILL.md`](../../.claude/skills/wiki-doc-author/SKILL.md) |
| **lint/產生工具**（純 stdlib） | `.claude/skills/wiki-doc-author/scripts/`（CI 用的副本在 `ci-templates/`） |

## 一句話

**每個 app：寫一份合規 README，第一段用一句可搜尋的話講清用途。能產 OpenAPI 的 app 再附一份
pre-commit 保持最新的 `openapi.json`。其餘交給 wiki。** 不會寫就叫 `wiki-doc-author` skill 幫你。
