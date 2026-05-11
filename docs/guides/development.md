# 開發和自定義指南

如何修改代碼、自定義 LLM 提示、添加新 API 端點和運行測試。

## 項目結構

```
llm-wiki-mcp/
├── wiki-processor/              # Markdown 處理服務
│   ├── main.py                  # 入口點
│   ├── requirements.txt          # Python 依賴
│   ├── Dockerfile               # Docker 配置
│   ├── api/
│   │   └── routes.py            # FastAPI 路由
│   ├── services/
│   │   ├── processor.py         # 核心處理邏輯
│   │   ├── llm.py               # Minimax LLM 客戶端
│   │   └── minio_client.py      # Minio 存儲邏輯
│   ├── models/
│   │   └── schemas.py           # Pydantic 數據模型
│   ├── storage/
│   │   └── minio_client.py      # 存儲實現
│   └── tests/                   # 單元測試
│
├── mcp-server/                  # HTTP API 服務
│   ├── main.py                  # 舊 MCP 實現（已廢棄）
│   ├── requirements.txt          # Python 依賴
│   ├── Dockerfile               # Docker 配置
│   ├── http_api/
│   │   └── main.py              # FastAPI HTTP API
│   ├── services/
│   │   └── wiki_service.py      # Wiki 查詢服務
│   ├── storage/
│   │   └── minio_client.py      # Minio 讀取
│   └── tests/                   # 單元測試
│
├── docker-compose.yml           # Docker Compose 編排
├── .env-example                 # 環境變數模板
├── README.md                    # 項目概述
├── LOCAL_SETUP.md               # 本地設置指南
├── API_SCHEMA.md                # Wiki 數據結構
├── TROUBLESHOOTING.md           # 故障排除
└── DEVELOPMENT.md               # 本文件
```

---

## 修改 LLM 提示

### 位置

文件：`wiki-processor/services/llm.py`

### 當前的提示

#### 首次運行提示（生成完整 Wiki）

```python
def generate_wiki(self, markdowns: dict) -> dict:
    combined = "\n\n".join(...)
    prompt = (
        "Analyze the following API documentation markdown files "
        "and generate a structured wiki.\n\n"
        f"{combined}\n\n"
        "Task:\n"
        "1. Extract all API endpoints (method, path, description, parameters)\n"
        "2. Group by module/service\n"
        '3. Generate JSON structure: {"apis": {...}, "metadata": {}}\n\n'
        "Output ONLY valid JSON, no markdown."
    )
    ...
```

#### 增量更新提示（更新現有 Wiki）

```python
def update_wiki(self, current_wiki: dict, changed_markdowns: dict, 
                changes: dict) -> dict:
    prompt = (
        f"Current Wiki (summarized):\n{wiki_summary}\n\n"
        f"Changes: {json.dumps(changes)}\n\n"
        f"New/Modified Markdowns:\n{changed_content}\n\n"
        "Task:\n"
        "1. For new files: Extract APIs and add to wiki\n"
        "2. For modified files: Update related APIs\n"
        "3. For deleted files: Remove from wiki\n"
        "4. Maintain module structure and semantic relationships\n\n"
        "Output ONLY the updated wiki JSON."
    )
    ...
```

### 自定義提示的步驟

#### 1. 編輯 llm.py

```bash
nano wiki-processor/services/llm.py
# 或使用你的編輯器打開
```

#### 2. 修改 generate_wiki() 中的 prompt

例如，添加額外的字段提取：

```python
prompt = (
    "Analyze the following API documentation markdown files "
    "and generate a structured wiki.\n\n"
    f"{combined}\n\n"
    "Task:\n"
    "1. Extract all API endpoints\n"
    "2. Extract authentication method for each API\n"  # 新增
    "3. Extract rate limiting information\n"           # 新增
    "4. Group by module/service\n"
    '5. Generate JSON: {"apis": {...}, "metadata": {}}\n\n'
    "Output ONLY valid JSON."
)
```

#### 3. 對應修改 API_SCHEMA.md 的 API Entry 結構

在 [API_SCHEMA.md](API_SCHEMA.md) 中添加新字段說明

#### 4. 重啟服務並測試

```bash
# 本地開發
uvicorn main:app --reload

# Docker
docker-compose up -d wiki-processor
docker-compose logs wiki-processor
```

#### 5. 發送測試 Markdown

```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{
    "markdowns": {
      "test.md": "# API\n## GET /test\n**Auth:** Bearer Token\n**Rate Limit:** 1000 req/hour"
    },
    "timestamp": "2026-05-09T10:00:00Z",
    "trigger_info": {"source": "test"}
  }'
```

#### 6. 驗證 wiki.json 包含新字段

```bash
curl http://localhost:8002/get_api_detail?module=test&api_key=GET%20/test
```

---

## 修改 Wiki 結構

### 添加新字段到 API 條目

在 `wiki-processor/services/llm.py` 中修改 LLM 提示，讓 LLM 在生成的 JSON 中包含新字段。

**示例：添加 `deprecated` 字段**

```python
# 在 generate_wiki 中修改提示
prompt = (
    "...\n"
    "For each API, include:\n"
    "- method: HTTP method\n"
    "- path: endpoint path\n"
    "- deprecated: true/false if API is deprecated\n"
    "...\n"
)
```

### 修改模組分組邏輯

LLM 自動決定模組名稱。要自定義：

```python
# 在提示中添加指引
prompt = (
    "...\n"
    "Module naming guidelines:\n"
    "- Use singular names (e.g., 'user' not 'users')\n"
    "- Group related endpoints (auth, billing, etc.)\n"
    "- Max 2-3 words per module name\n"
    "...\n"
)
```

---

## 添加新 API 端點到 mcp-server

### 當前的 API 端點

文件：`mcp-server/http_api/main.py`

現有端點：
- `GET /health` - 健康檢查
- `GET /list_apis` - 列出所有 API
- `GET /search_apis` - 搜尋 API
- `GET /get_api_detail` - 獲取詳細信息
- `GET /wiki_info` - Wiki 統計

### 添加新端點的步驟

#### 1. 編輯 http_api/main.py

```python
# 在現有路由下添加新路由
@app.get("/new_endpoint")
async def new_endpoint(param: str = ""):
    """新端點的說明"""
    service = WikiService(wiki_reader)
    result = service.new_method(param)  # 調用服務層
    
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    
    return {"data": result}
```

#### 2. 在 services/wiki_service.py 中添加新方法

```python
class WikiService:
    def __init__(self, wiki_reader):
        self.wiki_reader = wiki_reader
    
    def new_method(self, param: str):
        """實現查詢邏輯"""
        wiki = self.wiki_reader.get_json("wiki.json")
        
        if not wiki:
            return None
        
        # 實現自定義邏輯
        result = []
        for module, apis in wiki.get("apis", {}).items():
            # 處理...
            pass
        
        return result
```

#### 3. 添加數據模型（如果需要）

```python
# 在 models/ 中添加
from pydantic import BaseModel

class NewResponseModel(BaseModel):
    data: list
    count: int
    metadata: dict = {}
```

#### 4. 添加測試

文件：`mcp-server/tests/test_http_api.py`

```python
def test_new_endpoint(client):
    response = client.get("/new_endpoint?param=value")
    assert response.status_code == 200
    assert "data" in response.json()
```

#### 5. 測試新端點

```bash
# 本地運行
uvicorn http_api/main:app --reload

# 測試
curl http://localhost:8002/new_endpoint?param=test
```

---

## 運行測試

### 測試結構

```
wiki-processor/tests/
├── test_llm.py              # LLM 抽取邏輯
├── test_processor.py        # 處理邏輯
└── test_routes.py           # API 路由

mcp-server/tests/
├── test_wiki_service.py     # Wiki 查詢服務
└── test_http_api.py         # HTTP API 端點
```

### 運行所有測試

```bash
# 在項目根目錄
pytest -v

# 或分別運行
pytest wiki-processor/tests/ -v
pytest mcp-server/tests/ -v
```

### 運行特定測試

```bash
# 運行單個測試文件
pytest wiki-processor/tests/test_llm.py -v

# 運行單個測試函數
pytest wiki-processor/tests/test_llm.py::test_clean_json_string -v

# 運行包含特定關鍵字的測試
pytest -k "json" -v
```

### 添加新測試

```python
# 在 tests/ 中創建新文件或添加到現有文件
import pytest
from your_module import YourFunction

def test_your_function():
    """測試說明"""
    result = YourFunction(input_data)
    assert result == expected_output

@pytest.fixture
def sample_data():
    """設置測試數據"""
    return {"key": "value"}

def test_with_fixture(sample_data):
    result = YourFunction(sample_data)
    assert result is not None
```

### 測試覆蓋率

```bash
# 生成覆蓋率報告
pip install pytest-cov
pytest --cov=wiki-processor --cov=mcp-server

# 生成 HTML 報告
pytest --cov=. --cov-report=html
# 打開 htmlcov/index.html
```

---

## 代碼結構和設計模式

### Services 層（業務邏輯）

**wiki-processor/services/processor.py**

責任：
- 檢測 Markdown 變更
- 調用 LLM
- 協調存儲操作

```python
class WikiProcessor:
    def detect_changes(self, old: dict, new: dict) -> dict:
        """檢測變更（Pure function）"""
        pass
    
    async def process(self, markdowns: dict, timestamp: str):
        """主處理流程"""
        # 1. 檢測變更
        # 2. 調用 LLM
        # 3. 保存到 Minio
        # 4. 返回結果
```

**mcp-server/services/wiki_service.py**

責任：
- 從 Wiki 查詢數據
- 提供高級查詢方法

```python
class WikiService:
    def list_apis(self, module: str = ""):
        """列出 API"""
        pass
    
    def search_apis(self, query: str):
        """搜尋 API"""
        pass
```

### Storage 層（數據持久化）

**storage/minio_client.py**

責任：
- 抽象 Minio 操作
- 處理序列化/反序列化

```python
class MinioStorage:
    def get_json(self, key: str) -> dict | None:
        """讀取 JSON"""
        pass
    
    def put_json(self, key: str, data: dict):
        """寫入 JSON"""
        pass
```

### API 層（HTTP 接口）

**api/routes.py** 和 **http_api/main.py**

責任：
- 接收 HTTP 請求
- 調用 Services
- 返回響應

```python
@app.post("/process")
async def process(request: ProcessRequest):
    service = WikiService(...)
    result = await service.process(...)
    return result
```

---

## 本地開發最佳實踐

### 使用 Mock LLM 進行開發

避免不必要的 API 調用和成本：

```bash
export MOCK_LLM=true
uvicorn main:app --reload
```

### 使用虛擬環境

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 使用 IDE 的調試器

**VS Code launch.json**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "wiki-processor",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload"],
      "cwd": "${workspaceFolder}/wiki-processor"
    }
  ]
}
```

### 代碼風格和格式

```bash
# 安裝 linter 和 formatter
pip install black flake8

# 格式化代碼
black wiki-processor/ mcp-server/

# 檢查代碼風格
flake8 wiki-processor/ mcp-server/
```

---

## 常見開發任務

### 任務：修改 API 響應格式

1. **編輯 http_api/main.py 中的路由**
2. **修改 services/wiki_service.py 中的查詢邏輯**
3. **更新 models/schemas.py 中的數據模型**
4. **添加測試到 tests/test_http_api.py**
5. **運行 `pytest tests/ -v` 驗證**

### 任務：添加新的搜尋功能

1. **在 wiki_service.py 中添加新方法**
2. **在 http_api/main.py 中添加路由**
3. **編寫測試**
4. **文檔化新端點**

### 任務：改進 LLM 提示

1. **編輯 services/llm.py 中的提示**
2. **更新 API_SCHEMA.md 以反映新字段**
3. **測試新提示：`export MOCK_LLM=true`，然後發送 test markdown**
4. **驗證生成的 wiki.json**

---

## 調試技巧

### 啟用詳細日誌

```python
# 在代碼中
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Debug message: {variable}")
```

### 使用 pdb 交互式調試

```python
# 在代碼中添加
import pdb; pdb.set_trace()

# 或使用 Python 3.7+
breakpoint()
```

### 檢查中間值

```python
# 在 Service 方法中添加日誌
logger.info(f"Markdown files: {markdowns.keys()}")
logger.info(f"Changes detected: {changes}")
logger.info(f"Generated wiki: {wiki}")
```

---

## FastAPI 高級特性

### 添加 CORS 支持

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定具體域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 添加認證

```python
from fastapi import Depends, HTTPException, Header

async def verify_api_key(x_token: str = Header(...)):
    if x_token != "expected_key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_token

@app.get("/protected")
async def protected_route(token: str = Depends(verify_api_key)):
    return {"message": "Success"}
```

### 非同步操作

```python
async def expensive_operation():
    # 耗時操作
    await asyncio.sleep(1)
    return result

@app.get("/async")
async def async_endpoint():
    result = await expensive_operation()
    return {"result": result}
```

---

## 相關文檔

- [LOCAL_SETUP.md](LOCAL_SETUP.md) - 本地環境設置
- [API_SCHEMA.md](API_SCHEMA.md) - 數據結構參考
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排除
- [README.md](README.md) - 項目概述
