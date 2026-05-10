#!/usr/bin/env python3
"""
示例 generate_docs.py - 從應用代碼生成 Markdown 文檔

應用應自行實現此腳本來生成 markdown，例如：
1. 從 OpenAPI/Swagger 規格解析
2. 從代碼註釋提取
3. 從 Python 函數簽名和文檔字符串生成

此文件是示例，應根據實際應用的文檔生成方式修改。
"""

import json
import os
from datetime import datetime

def generate_api_markdown(app_name: str) -> dict[str, str]:
    """
    生成應用的 API 文檔 markdown。

    返回值：{filename: content}
    """
    markdowns = {}

    # 示例 1: API 文檔
    api_content = f"""---
title: "{app_name} API"
type: "api_module"
module: "{app_name}"
source_app: "{app_name}"
source_version: "$CI_COMMIT_SHA"
description: "API endpoints for {app_name}"
endpoints:
  - method: "GET"
    path: "/{app_name}"
    summary: "List all {app_name} resources"
    tags: ["list", "public"]
  - method: "POST"
    path: "/{app_name}"
    summary: "Create a new {app_name} resource"
    tags: ["create"]
related: []
tags: ["api", "{app_name}"]
last_updated: "{datetime.now().isoformat()}Z"
---

# {app_name.title()} API

Manage {app_name} resources.

## Endpoints

### GET /{app_name}

List all {app_name} resources.

**Response:**
```json
{{
  "items": []
}}
```

### POST /{app_name}

Create a new {app_name} resource.

**Request:**
```json
{{
  "name": "...",
  "description": "..."
}}
```
"""

    markdowns[f"{app_name}_api.md"] = api_content

    # 示例 2: 架構文檔
    architecture_content = f"""---
title: "{app_name} Architecture"
type: "architecture"
source_app: "{app_name}"
source_version: "$CI_COMMIT_SHA"
description: "System design of {app_name}"
related: []
tags: ["architecture", "{app_name}"]
last_updated: "{datetime.now().isoformat()}Z"
---

# {app_name.title()} Architecture

## Overview

{app_name} is responsible for managing ... [your description]

## Components

- **API Server**: FastAPI application handling HTTP requests
- **Database**: [Your database choice]
- **Cache**: [Your cache strategy]

## Data Flow

[ASCII diagram or description of data flow]
"""

    markdowns[f"{app_name}_architecture.md"] = architecture_content

    return markdowns


def main():
    """
    主函數：生成文檔並保存到 docs/ 目錄。

    實際應用應修改此函數以根據自己的需求生成文檔。
    """
    # 獲取應用名稱（從環境變數或硬編碼）
    app_name = os.getenv("CI_PROJECT_NAME", "app").split("/")[-1]

    # 確保 docs 目錄存在
    os.makedirs("docs", exist_ok=True)

    # 生成 markdown
    markdowns = generate_api_markdown(app_name)

    # 保存到 docs/ 目錄
    for filename, content in markdowns.items():
        filepath = os.path.join("docs", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Generated: {filepath}")

    # 可選：同時生成 JSON 格式方便 CI 傳遞
    with open("/tmp/app_markdowns.json", "w") as f:
        json.dump(markdowns, f, ensure_ascii=False, indent=2)
    print(f"Also saved to /tmp/app_markdowns.json")


if __name__ == "__main__":
    main()
