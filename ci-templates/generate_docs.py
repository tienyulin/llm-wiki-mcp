#!/usr/bin/env python3
"""示例：產生一份合規的 README 給 wiki（新標準）。

新標準（見 docs/guides/authoring-source-docs.md）：
- 每個 app 寫一份**合規 README**（frontmatter type/source_app + 第一段摘要）。
- 能產 OpenAPI 的 app：committed `openapi.json` 由 pre-commit hook 保持最新，CI 一起送，
  **endpoint 不用手抄**（processor 走確定性轉換）。
- 不能產 OpenAPI：在 README 的 Endpoints 區手寫 `METHOD /path — 用途`，由 LLM 抽取。

實務上 README 多半是手寫 / 用 `wiki-doc-author` skill 產，不必這支腳本。這支只是示範格式。
"""
import os


def render_readme(app_name: str, has_openapi: bool) -> str:
    endpoints = "" if has_openapi else (
        "\n## Endpoints\n"
        f"GET /{app_name} — 列出 {app_name} 資源\n"
        f"POST /{app_name} — 建立一筆 {app_name} 資源\n"
    )
    return (
        f"---\n"
        f"type: api\n"
        f"source_app: {app_name}\n"
        f"tags: [{app_name}]\n"
        f"---\n\n"
        f"# {app_name.title()} API\n\n"
        f"一句話講清楚這個服務在做什麼（這段會被 embed，影響語意搜尋）。\n"
        f"{endpoints}"
    )


def main():
    app_name = (os.getenv("CI_PROJECT_NAME", "app").split("/")[-1])
    has_openapi = os.path.exists("openapi.json")  # pre-commit 產的話就有
    os.makedirs("docs", exist_ok=True)
    path = "docs/README.md" if os.path.isdir("docs") else "README.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_readme(app_name, has_openapi))
    print(f"Generated compliant README: {path} (openapi.json present={has_openapi})")


if __name__ == "__main__":
    main()
