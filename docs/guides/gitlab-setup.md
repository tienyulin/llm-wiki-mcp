# GitLab CI/CD 集成指南：應用直接提交 Wiki

**新架構**：應用獨立生成文檔 → 直接 POST 到 wiki-processor → 應用級增量更新

不再需要中央 markdown repo，每個應用自主管理文檔。

---

## 快速開始（5 分鐘）

### 前置條件

- ✅ wiki-processor 運行在 http://wiki-processor:8001（或你的服務器）
- ✅ ci-scripts repo 已含有通用 CI 模板：`templates/generate-and-push-wiki.yml`
- ✅ 你的應用有 `scripts/` 目錄

### 步驟 1：在應用中添加 `.gitlab-ci.yml`

```yaml
# fastapi-a/.gitlab-ci.yml 或任何應用
include:
  - remote: 'https://gitlab.com/t.tienyulin/ci-scripts/raw/master/templates/generate-and-push-wiki.yml'

stages:
  - generate
  - push

# 其他 CI 配置（如果有）...
```

**就這樣！** 無需修改模板，直接 include。

### 2️⃣ 複製 `.gitlab-ci.yml` 到 Repo 根目錄

選一個方式：

**方式 A：直接複製我們的範例**
```bash
curl -sSL https://raw.githubusercontent.com/tienyulin/llm-wiki-mcp/claude/general-session-ax0rl/examples/.gitlab-ci.yml \
  -o .gitlab-ci.yml
```

**方式 B：手動複製**
```yaml
# .gitlab-ci.yml
stages:
  - deploy

update-wiki:
  stage: deploy
  image: python:3.11-slim
  rules:
    - changes:
        - markdowns/**/*.md
  variables:
    WIKI_PROCESSOR_URL: "${WIKI_PROCESSOR_URL:-http://wiki-processor:8001}"
  script:
    - pip install httpx
    - curl -sSL https://raw.githubusercontent.com/tienyulin/llm-wiki-mcp/claude/general-session-ax0rl/examples/send_to_processor.py -o send.py
    - python3 send.py
```

### 3️⃣ Push 到 GitLab

```bash
git add .gitlab-ci.yml
git commit -m "Add wiki processor CI"
git push origin main  # 或你的分支
```

### 4️⃣ 修改任何 markdown 文件並 push

```bash
# 編輯 markdown
echo "## GET /users" >> markdowns/api-users.md

# Commit & push
git add markdowns/
git commit -m "Update API docs"
git push origin main
```

**GitLab CI 會自動觸發！** 🚀

---

## 詳細設置

### 環境變數配置

在 GitLab 項目中設置環境變數：

**Project Settings → CI/CD → Variables**

| 變數名 | 值 | 說明 |
|--------|-----|------|
| `WIKI_PROCESSOR_URL` | `http://wiki-processor:8001` | Processor API 位置 |
| `MARKDOWN_PATTERN` | `markdowns/**/*.md` | 尋找 markdown 的 Glob 模式 |

或直接在 `.gitlab-ci.yml` 中設定：

```yaml
update-wiki:
  variables:
    WIKI_PROCESSOR_URL: "http://wiki-processor:8001"
    MARKDOWN_PATTERN: "markdowns/**/*.md"
```

### 支持的 Runner 類型

✅ 任何 GitLab Runner 都可以（Docker, Shell, Kubernetes）

最簡單的方式：
```bash
# 使用 GitLab.com 的共享 runner（如果你用 gitlab.com）
# 無需配置，自動使用
```

---

## 分步驟說明

### 第一次運行

```
你在中央 repo push → 
GitLab 偵測 markdowns/ 有變化 → 
CI 觸發 update-wiki job →
Python 腳本蒐集所有 .md 文件 →
打包成 JSON →
POST 給 http://wiki-processor:8001/process →
Processor 調用 Minimax LLM →
返回處理結果 →
Wiki 存在 Minio ✅
```

### Markdown 文件結構

```bash
# 好的結構（會被收集）
markdowns/
├── api-users.md           ✅ 被收集
├── api/orders.md          ✅ 被收集
├── docs/getting-started/  ✅ 目錄也支持
│   ├── intro.md
│   └── setup.md
└── README.md              ❌ 根目錄不被收集

# 修改 MARKDOWN_PATTERN 如果需要
# "docs/**/*.md"  - 只收集 docs/ 目錄
# "**/*.md"       - 收集所有 markdown
```

---

## 測試 & 除錯

### 在本地測試（不需要 CI）

```bash
# 1. 安裝依賴
pip install httpx

# 2. 下載 Python 腳本
curl -sSL https://raw.githubusercontent.com/tienyulin/llm-wiki-mcp/claude/general-session-ax0rl/examples/send_to_processor.py \
  -o send_to_processor.py

# 3. 運行
WIKI_PROCESSOR_URL=http://localhost:8001 python3 send_to_processor.py
```

### 查看 CI 日誌

在 GitLab UI 中：
```
Project → CI/CD → Pipelines → 點擊 Pipeline ID → 點擊 update-wiki job
```

或用 CLI：
```bash
gitlab-runner verify
gitlab-runner --debug run
```

### 常見問題 & 解決方案

#### 問題 1：找不到 markdown 文件

```
⚠️  No markdown files found matching: markdowns/**/*.md
```

**解決方案：**
```bash
# 檢查文件是否存在
ls -la markdowns/

# 檢查 .gitlab-ci.yml 中的 MARKDOWN_PATTERN 是否正確
# 改成與你的目錄結構匹配
```

#### 問題 2：Connection refused

```
❌ Connection error: Cannot connect to host 'wiki-processor:8001'
```

**解決方案：**
1. Processor 是否啟動了？
   ```bash
   docker ps | grep wiki-processor
   ```

2. 檢查 `WIKI_PROCESSOR_URL` 是否正確
   - 同一 Docker network：`http://wiki-processor:8001`
   - 不同機器：`http://your-processor-ip:8001`
   - 有代理：設置正確的 URL

#### 問題 3：Timeout

```
❌ Timeout: Processor took too long to respond
```

**解決方案：**
- Minimax API 被限流
- LLM 處理耗時（正常，可能 15-30 秒）
- 增加 timeout：在 CI 中設置 `timeout: 5 minutes`

---

## 完整工作流程範例

### 情景：更新 API 文件

```bash
# 1. 編輯 markdown
vim markdowns/api-users.md
# 在文件中加入：
# ## PUT /users/{id}
# Update user details

# 2. Git 操作
git add markdowns/api-users.md
git commit -m "Add PUT /users endpoint"
git push origin main

# GitLab CI 自動觸發 👇
```

**CI 日誌輸出：**
```
🔍 Collecting markdown files from: markdowns/**/*.md
  ✅ markdowns/api-users.md (456 bytes)
  ✅ markdowns/api-orders.md (789 bytes)
  ✅ markdowns/api-products.md (234 bytes)

✅ Collected 3 markdown files

📤 Sending to processor: http://wiki-processor:8001/process
   Markdowns: 3 files
   Timestamp: 2026-05-08T12:00:00Z

📥 Response: HTTP 200
   Status: success
   Message: Wiki updated successfully

📊 Changes detected:
   Modified: api-users.md

✅ Wiki updated successfully!
   Output: minio://wiki-data/wiki.json
```

---

## 進階設置

### 1️⃣ 將腳本保存在 Repo 中

```bash
# 在你的 repo 中建立
mkdir -p scripts
curl -sSL https://raw.githubusercontent.com/tienyulin/llm-wiki-mcp/claude/general-session-ax0rl/examples/send_to_processor.py \
  -o scripts/send_to_processor.py

git add scripts/send_to_processor.py
git commit -m "Add wiki processor script"
git push
```

然後改 `.gitlab-ci.yml`：
```yaml
script:
  - pip install httpx
  - python3 scripts/send_to_processor.py
```

### 2️⃣ 多分支部署

```yaml
update-wiki:
  only:
    - main           # 只在 main 分支運行
    - production
    - tags
```

### 3️⃣ 排程自動更新（定期同步）

```yaml
# 每天晚上 8 點運行
scheduled-update:
  stage: deploy
  script:
    - pip install httpx
    - python3 send_to_processor.py
  only:
    - schedules
```

在 GitLab UI 設置：
```
Project → CI/CD → Schedules → New schedule
```

### 4️⃣ 使用 Webhook（其他 Repo 觸發）

```bash
# 如果 markdown 在別的 repo，可用 webhook
# Project → Integrations → Webhooks
# URL: https://gitlab.com/.../trigger/pipeline
```

---

## 下一步

1. ✅ 設置 `.gitlab-ci.yml`
2. ✅ Push markdown 文件
3. ✅ 查看 CI 運行 + 日誌
4. ✅ 驗證 wiki.json 在 Minio 中生成
5. 🎯 將 wiki.json 用於前端/文檔網站

### 查看生成的 wiki

```bash
# 方式 1：Minio 控制台
firefox http://minio:9001
# Login: minioadmin / minioadmin
# Browse: wiki-data bucket → wiki.json

# 方式 2：直接下載
curl http://minio:9000/wiki-data/wiki.json > wiki.json
jq . wiki.json

# 方式 3：用你的應用讀取
# GET http://minio:9000/wiki-data/wiki.json
```

---

## 常用命令速查

```bash
# 檢查 CI 是否啟用
git push origin main
# 在 GitLab 項目看 Pipeline

# 手動觸發 CI
# 在 GitLab UI → Pipeline → Run pipeline

# 查看環境變數
gitlab-runner verify
# 或在 .gitlab-ci.yml 中 script 添加
# echo "URL: $WIKI_PROCESSOR_URL"
```

---

需要幫助嗎？
- ❓ GitLab 問題：檢查 Project → CI/CD → Pipelines 的日誌
- ❓ Processor 問題：`docker logs wiki-processor`
- ❓ Minio 問題：訪問 http://minio:9001 (admin:minioadmin)
