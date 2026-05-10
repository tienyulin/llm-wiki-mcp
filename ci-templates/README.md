# CI/CD 模板：Wiki 自動同步

在 ci-scripts repo 中使用的通用 GitLab CI 模板。所有應用通過 `include` 使用，無需修改。

## 文件說明

### generate-and-push-wiki.yml

**通用的 GitLab CI/CD 模板**，包含 2 個 stage：

1. **generate** - 執行應用的 `scripts/generate_docs.py`
   - 驗證 markdown 生成
   - 創建 artifacts

2. **push** - 發送 markdown 到 wiki-processor
   - 蒐集 `docs/` 中的所有 markdown
   - POST 到 `$WIKI_PROCESSOR_URL/process`
   - 附帶 source_app 和 source_version

**使用方式**：

```yaml
# 你的應用的 .gitlab-ci.yml
include:
  - remote: 'https://gitlab.com/t.tienyulin/ci-scripts/raw/master/templates/generate-and-push-wiki.yml'
```

**環境變數**：
- `WIKI_PROCESSOR_URL`: wiki-processor 地址（預設：http://localhost:8001）
- `WIKI_PROCESSOR_TIMEOUT`: 請求超時秒數（預設：300）

### generate_docs.py

**示例文檔生成腳本**

展示如何從應用代碼生成 markdown：

```python
#!/usr/bin/env python3
import os
from datetime import datetime

def generate_markdown(app_name: str) -> dict[str, str]:
    """生成應用的文檔"""
    return {
        "api.md": f"""---
title: "{app_name} API"
type: "api_module"
module: "{app_name}"
source_app: "{app_name}"
description: "..."
---
# API Docs
..."""
    }
```

**使用方式**：

1. 複製此腳本到你的應用
2. 根據應用的實際 API 修改
3. 在 GitLab CI 中執行（通過 CI 模板自動調用）

---

## 工作流程

```
應用 push to master/main
    ↓
CI 包含 generate-and-push-wiki.yml
    ↓
Stage 1: generate
  ├─ 執行 scripts/generate_docs.py
  ├─ 生成 docs/*.md
  └─ 建立 artifacts
    ↓
Stage 2: push
  ├─ 蒐集 docs/ 中的所有 markdown
  ├─ POST 到 wiki-processor
  └─ 傳遞 source_app=${CI_PROJECT_NAME}
    ↓
wiki-processor 應用級增量更新
    ↓
Minio 存儲 + 審計日誌
    ↓
mcp-server 緩存失效
    ↓
✅ 完成
```

## 自訂文檔生成

### 從 OpenAPI 規格生成

```python
import json
import requests

def generate_from_openapi(app_name: str):
    """從 OpenAPI endpoint 生成 markdown"""
    spec = requests.get("http://localhost:8000/openapi.json").json()
    # 解析 spec，轉換為 markdown...
```

### 從代碼註釋生成

```python
import ast

def extract_docstrings(python_files):
    """從 Python docstrings 提取文檔"""
    # 使用 ast 模組解析...
```

### 混合模式

```python
def generate_markdown(app_name: str):
    return {
        **generate_from_openapi(app_name),  # API 文檔
        **generate_from_architecture(),      # 架構文檔
        **generate_from_comments(),          # 手寫評論
    }
```

## 範例應用

### fastapi-a

```
fastapi-a/
├── .gitlab-ci.yml
│   include:
│     - remote: 'https://gitlab.com/t.tienyulin/ci-scripts/raw/master/templates/generate-and-push-wiki.yml'
├── scripts/
│   └── generate_docs.py  # 自訂：從 FastAPI app 讀取路由，生成 markdown
├── docs/  # 自動生成
│   ├── api.md
│   └── architecture.md
└── src/
    └── main.py
```

### fastapi-b

相同結構，只需：
1. 複製 `.gitlab-ci.yml` (include 相同模板)
2. 修改 `scripts/generate_docs.py` (適應 fastapi-b 的 API)
3. Push → CI 自動執行

## 故障排除

### 模板加載失敗

```
❌ Couldn't find include '/templates/generate-and-push-wiki.yml'
```

**原因**：遠端 URL 錯誤

**解決**：確認正確的 ci-scripts 分支和路徑

```yaml
# 正確
include:
  - remote: 'https://gitlab.com/t.tienyulin/ci-scripts/raw/master/templates/generate-and-push-wiki.yml'

# 錯誤
include:
  - remote: 'https://gitlab.com/t.tienyulin/ci-scripts/raw/main/...'  # 分支錯誤
```

### generate_docs.py 失敗

```
❌ FileNotFoundError: No such file or directory: 'scripts/generate_docs.py'
```

**解決**：確保應用中有 `scripts/generate_docs.py`

### POST 到 wiki-processor 失敗

```
❌ Connection refused: wiki-processor:8001
```

**解決**：
- 檢查 WIKI_PROCESSOR_URL 環境變數
- 確認 wiki-processor 已運行
- 本地測試時使用 `http://localhost:8001`

---

## 自訂 CI 模板

如果需要修改模板：

1. 複製 `generate-and-push-wiki.yml`
2. 修改 stage、script 等
3. 在 `.gitlab-ci.yml` 中改用 `remote` 或 `local` 路徑

```yaml
# 修改後的 ci-scripts 模板
include:
  - remote: 'https://gitlab.com/t.tienyulin/ci-scripts/raw/master/templates/custom-wiki-ci.yml'
```

---

## 相關文檔

- [README.md](../README.md) - 整體系統架構
- [GITLAB_SETUP.md](../GITLAB_SETUP.md) - GitLab 集成指南
- [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) - 技術細節

---

**第一次使用？** 參考 [GITLAB_SETUP.md](../GITLAB_SETUP.md) 的「快速開始」
