# 源頭文件標準（怎麼產第一版給 wiki）

> **單一真相 = `wiki-doc-author` skill**（一個自包含的 `SKILL.md`，讀完即可做）。skill 已獨立成
> repo [`tienyulin/llm-wiki-skills`](https://github.com/tienyulin/llm-wiki-skills)，在本平台掛在
> `.claude/skills`（git submodule）。本頁只是平台內指標。

完整規範、決策樹、各框架做法、範本、§Ingestion、工具，全在那一個檔：

- 規範本體：[`.claude/skills/wiki-doc-author/SKILL.md`](../../.claude/skills/wiki-doc-author/SKILL.md)
- lint/產生工具（純 stdlib）：`.claude/skills/wiki-doc-author/scripts/`（CI 用的副本在 `ci-templates/`）

## 一句話

**processor 只吃兩種來源：`openapi.json` 與 `README`。** 每個要被記錄的東西（API / cronjob / worker /
知識…）一律寫一份合規 README，第一段用一句可搜尋的話講清用途；是 HTTP API 且框架能產 OpenAPI 的，
再附一份 pre-commit 保持最新的 `openapi.json`。不會寫就叫 `wiki-doc-author` skill 幫你。
