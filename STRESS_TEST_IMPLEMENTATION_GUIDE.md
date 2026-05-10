# 大規模壓力測試實作指南

**目標**：為下一個 AI 提供清晰的實作路線圖

**壓力測試總體目標**：
- 驗證 100+ 應用支持的實際性能
- 發現系統瓶頸（LLM、Minio、快取、網路）
- 測試大數據量和長期運行穩定性
- 評估多 AI agent 並發訪問能力

---

## 總體架構

```
stress_test/
├── __init__.py
├── gitlab_webhook_simulator.py      # GitLab webhook 模擬器
├── agent_concurrency_test.py        # AI agent 並發查詢測試
├── large_data_stress_test.py        # 大數據量壓力測試
├── sustained_load_test.py           # 持久性壓力測試（30 分鐘）
├── cache_performance_analyzer.py    # 緩存性能分析
├── generate_report.py               # 主驅動，執行所有測試並生成報告
├── utils/
│   ├── __init__.py
│   ├── metrics_collector.py         # 實時指標收集（CPU、記憶體、QPS）
│   ├── report_generator.py          # 報告生成（Markdown 格式）
│   ├── logger.py                    # 統一日誌
│   └── config.py                    # 配置管理
└── fixtures/
    ├── __init__.py
    └── sample_markdowns.py          # 生成測試用 markdown
```

---

## 任務分解

### 1️⃣ 基礎框架 (`stress_test/utils/`)

#### `metrics_collector.py`
**目標**：實時收集系統和應用指標

**需要實現**：
```python
class MetricsCollector:
    """實時監控系統資源和應用性能"""
    
    # 監控指標
    - cpu_percent: float            # CPU 利用率（%）
    - memory_mb: float              # 記憶體占用（MB）
    - memory_peak_mb: float         # 記憶體峰值
    - qps: float                    # 每秒查詢數
    - app_rps: float                # 每秒應用更新數
    - cache_hit_rate: float         # 快取命中率（%）
    - p50_latency_ms: float         # P50 延遲
    - p95_latency_ms: float         # P95 延遲
    - p99_latency_ms: float         # P99 延遲
    - error_count: int              # 錯誤計數
    - minio_operations: int         # Minio 操作計數
    
    def start_monitoring():
        """開始監控，後台線程每 1 秒採樣一次"""
    
    def stop_monitoring() -> dict:
        """停止監控，返回時間序列數據"""
        # 返回: {timestamp: [cpu, memory, qps, ...]}
    
    def get_summary() -> dict:
        """獲取統計摘要"""
        # 返回: {
        #   "peak_memory_mb": 500,
        #   "avg_cpu_percent": 45,
        #   "peak_qps": 10000,
        #   "avg_cache_hit_rate": 0.95,
        #   "p99_latency_ms": 150,
        #   "total_errors": 0
        # }
```

**實現方式**：
- 使用 `psutil` 監控 CPU 和記憶體
- 統計 HTTP 請求的響應時間分布
- 追蹤快取命中/未命中事件
- 記錄所有指標到 JSON，用於報告生成

**關鍵點**：
- ⚠️ 監控本身的開銷要最小（<1% CPU）
- 監控頻率：1 秒採樣一次
- 數據精度：保留到小數點 2 位

---

#### `config.py`
**目標**：集中配置管理

**需要實現**：
```python
class StressTestConfig:
    """所有測試配置的中央存儲"""
    
    # 系統連接
    PROCESSOR_URL: str = "http://localhost:8001"
    MCP_SERVER_URL: str = "http://localhost:8002"
    MINIO_ENDPOINT: str = "localhost:9000"
    
    # LLM 設置
    MOCK_LLM: bool = True            # 是否使用 MOCK 模式
    LLM_TIMEOUT_SECONDS: int = 60
    
    # 測試參數（可被命令行覆蓋）
    WEBHOOK_SIM_CONFIG = {
        "num_apps": 100,
        "markdown_per_app": 10,
        "markdown_size_kb": 5,
        "update_frequency": 1,      # 應用/秒
        "duration_seconds": 300
    }
    
    AGENT_TEST_CONFIG = {
        "num_agents": 100,
        "query_rate_per_agent": 10,  # 查詢/秒
        "test_duration": 300
    }
    
    # ... 其他配置
```

---

#### `logger.py`
**目標**：統一日誌管理

**需要實現**：
```python
class StressTestLogger:
    """統一日誌系統"""
    
    def log_test_start(test_name: str, config: dict):
        """記錄測試開始"""
    
    def log_request(method: str, url: str, status: int, latency_ms: float):
        """記錄每個 HTTP 請求"""
    
    def log_metric(metric_name: str, value: float, unit: str):
        """記錄指標"""
    
    def log_error(error: Exception, context: str):
        """記錄錯誤"""
```

---

### 2️⃣ GitLab Webhook 模擬器 (`gitlab_webhook_simulator.py`)

**目標**：模擬 GitLab CI pipeline 觸發 wiki-processor

**核心邏輯**：
```python
class GitLabWebhookSimulator:
    """模擬 GitLab push event 和 CI pipeline"""
    
    def __init__(self, processor_url, num_apps, markdown_per_app, ...):
        self.processor_url = processor_url
        self.num_apps = num_apps
        self.metrics = MetricsCollector()
    
    def generate_markdown(app_name: str, file_index: int) -> dict:
        """為應用生成 markdown"""
        # 返回 {"filename.md": "content with frontmatter"}
        # frontmatter 必須包含：
        # - title
        # - type (api, architecture, config)
        # - source_app: app_name
        # - source_version: git_hash
        # - last_updated: ISO 時間戳
    
    async def trigger_webhook(app_name: str, markdowns: dict):
        """發送 HTTP POST 到 wiki-processor"""
        payload = {
            "markdowns": markdowns,
            "timestamp": datetime.now().isoformat(),
            "trigger_info": {
                "source": "gitlab-ci",
                "app": app_name,
                "version": git_hash,
                "branch": "main",
                "commit": commit_sha
            },
            "source_app": app_name,
            "source_version": git_hash
        }
        # POST /process，記錄耗時和狀態
    
    async def run_simulation(update_frequency=1, duration_seconds=300):
        """運行測試"""
        # 1. 計時開始，啟動 MetricsCollector
        # 2. 每秒發送 update_frequency 個應用的更新
        # 3. 持續 duration_seconds 秒
        # 4. 收集結果，計算 RPS、吞吐量、延遲分布
```

**輸出指標**：
- 每秒吞吐量（apps/sec）
- 平均響應時間
- P95、P99 響應時間
- 錯誤率（%）
- Wiki 檔案總數增長

---

### 3️⃣ AI Agent 並發測試 (`agent_concurrency_test.py`)

**目標**：模擬多個 AI agent 同時查詢 mcp-server

**核心邏輯**：
```python
class AgentConcurrencyTest:
    """模擬 N 個 AI agent 並發訪問 mcp-server"""
    
    def __init__(self, mcp_server_url, num_agents, query_rate_per_agent):
        self.mcp_server_url = mcp_server_url
        self.num_agents = num_agents
        self.query_rate = query_rate_per_agent
        self.metrics = MetricsCollector()
    
    async def agent_worker(agent_id: int):
        """單個 agent 的查詢循環"""
        # 1. 每秒發送 query_rate 個查詢
        # 2. 查詢類型：
        #    - list_apis (30%)
        #    - get_api_detail (40%)
        #    - search_apis (30%)
        # 3. 記錄每個查詢的：
        #    - 響應時間
        #    - 是否命中快取（通過檢查響應頭或耗時推斷）
        #    - 錯誤
    
    async def cache_invalidation_trigger():
        """模擬應用更新導致的快取失效"""
        # 每秒觸發 1 個應用的更新
        # POST /cache/invalidate?source_app=app-X
        # 監控失效前後的查詢速度變化
    
    async def run_simulation(duration_seconds=600):
        """運行並發測試"""
        # 1. 啟動 MetricsCollector
        # 2. 並行運行 num_agents 個 agent_worker
        # 3. 同時運行 cache_invalidation_trigger
        # 4. 持續 duration_seconds
        # 5. 收集快取命中率、延遲分布
```

**輸出指標**：
- 每秒查詢數（QPS）
- 快取命中率（%）
- 快取命中延遲（ms）
- 快取未命中延遲（ms，Minio 讀取）
- P50、P95、P99 延遲
- 應用級快取失效覆蓋率

---

### 4️⃣ 大數據量測試 (`large_data_stress_test.py`)

**目標**：測試大量 markdown 數據進來時的性能

**場景 1：大應用（多 markdown）**
```python
def scenario_1_large_app():
    """單個應用 1000 個 markdown（共 500MB）"""
    # 1. 生成 1000 個 markdown，總 500MB
    # 2. 一次性 POST 到 wiki-processor
    # 3. 監控：
    #    - 處理耗時
    #    - 記憶體峰值
    #    - Minio 存儲耗時
```

**場景 2：多應用大數據**
```python
def scenario_2_many_apps_large():
    """100 應用，每個 100 個 markdown（共 1GB）"""
    # 1. 生成 100 個應用，總 1GB
    # 2. 並行 POST（10 個並發）
    # 3. 監控：
    #    - wiki.json 大小增長
    #    - 記憶體占用（快取）
    #    - CPU 利用率
```

**場景 3：漸進式增長**
```python
def scenario_3_progressive_growth():
    """從 10 應用增加到 500 應用"""
    # 1. 初始 10 個應用
    # 2. 每 30 秒增加 10 個應用
    # 3. 監控效能衰減：
    #    - 處理耗時隨應用數增加而增加嗎？
    #    - 記憶體線性增長嗎？
    #    - P99 延遲是否穩定？
```

---

### 5️⃣ 持久性壓力測試 (`sustained_load_test.py`)

**目標**：30 分鐘長期運行，驗證穩定性和無泄漏

**三階段流程**：
```python
class SustainedLoadTest:
    """30 分鐘持續壓力測試"""
    
    PHASES = {
        "ramp_up": {
            "duration": 600,     # 10 分鐘
            "apps_per_minute": "linear(0->50)"  # 從 0 逐漸增加到 50
        },
        "peak": {
            "duration": 900,     # 15 分鐘
            "apps_per_minute": 50  # 持續 50 apps/min
        },
        "wave": {
            "duration": 300,     # 5 分鐘
            "apps_per_minute": "wave(10,100)"  # 波動：10-100
        }
    }
    
    async def run():
        """執行三階段測試"""
        # 監控點（每 30 秒記錄一次）：
        # 1. 記憶體使用量（檢測泄漏）
        # 2. CPU 利用率
        # 3. 應用更新成功率
        # 4. P99 延遲（檢測衰退）
        # 5. 快取大小
```

**成功標準**：
- ✅ 記憶體線性增長（不指數增長）
- ✅ 錯誤率 <0.1%
- ✅ P99 延遲穩定（±10%）
- ✅ 無資源洩漏

---

### 6️⃣ 緩存效率分析 (`cache_performance_analyzer.py`)

**目標**：深度分析快取策略

**測試場景**：
```python
class CachePerformanceAnalyzer:
    """分析快取效率和策略有效性"""
    
    def test_1_ttl_efficiency():
        """TTL 失效效率"""
        # 設置短 TTL（10 秒）
        # 觀察過期前後的查詢延遲變化
        # 計算 TTL 失效導致的 Minio 讀取次數
    
    def test_2_app_level_invalidation():
        """應用級失效效率"""
        # 100 應用，每秒 1 個應用更新
        # 監控：每次失效清除了多少快取項？
        # 預期：每次應該只清除 1 個應用的快取（<2% 無關快取）
    
    def test_3_cache_hotness():
        """快取熱度分佈"""
        # 記錄每個 API 被查詢的次數
        # 繪製 Zipfian 分布圖
        # 發現 20% API 占多少 % 的流量
    
    def test_4_multiprocess_simulation():
        """多進程部署的快取同步問題"""
        # 模擬 4 個 mcp-server 進程
        # 其中一個進程收到快取失效通知
        # 其他進程是否仍然提供舊數據？
        # 評估 Redis 共享快取的必要性
```

**輸出指標**：
- 全局快取命中率
- 應用級快取命中率
- 快取有效期內重複率（可避免 Minio 讀取的百分比）
- 應用級失效覆蓋率（應該 >98%）

---

### 7️⃣ 報告生成 (`generate_report.py`)

**目標**：彙整所有測試結果，生成專業報告

**輸出格式**：
```
STRESS_TEST_REPORT_2026-05-10.md

## 執行摘要
- 測試時間：2026-05-10 10:00:00 - 12:30:00
- 總耗時：2.5 小時
- 測試模式：MOCK LLM（快速驗證）/ 真實 API（實際性能）
- 系統配置：Docker Compose (3 容器)
- 是否發現問題：是/否

## 性能指標總結
| 指標 | 值 | 狀態 |
|------|---|------|
| 峰值吞吐量 | 1000 apps/sec | ✅ 正常 |
| 峰值 QPS | 10000 | ✅ 正常 |
| P99 延遲 | 50ms | ✅ 正常 |
| 快取命中率 | 95% | ✅ 正常 |
| 無泄漏 | 是 | ✅ 正常 |

## 詳細結果
### 1. GitLab Webhook 模擬 (100 apps)
- 吞吐量曲線圖
- 延遲分布
- 錯誤日誌

### 2. AI Agent 並發 (100 agents)
- QPS 曲線
- 快取命中率分析
- 應用級失效效果評估

### 3. 大數據量測試
- 記憶體占用
- Minio 性能
- 數據增長曲線

### 4. 持久性壓力 (30 分鐘)
- 記憶體泄漏檢測
- 性能穩定性
- 資源占用趨勢

### 5. 緩存分析
- 命中率分佈
- Zipfian 熱度圖
- 應用級失效有效性

## 瓶頸識別
| 瓶頸 | 嚴重性 | 原因 | 建議 |
|-----|--------|------|------|
| LLM API | 高 | API 超時 60 秒 | 實現請求隊列 + 批處理 |
| ... | ... | ... | ... |

## 容量規劃
- 單機上限：1000 應用（假設 100 MB/應用）
- 記憶體需求：8GB（快取 + wiki 數據）
- 水平擴展：推薦 Kubernetes + Redis 共享快取
- 成本優化建議

## 建議
1. ...
2. ...
```

---

## 實施檢查清單

### 核心實現
- [ ] `metrics_collector.py` - 指標收集
- [ ] `config.py` - 配置管理
- [ ] `logger.py` - 日誌系統
- [ ] `gitlab_webhook_simulator.py` - Webhook 模擬
- [ ] `agent_concurrency_test.py` - Agent 並發
- [ ] `large_data_stress_test.py` - 大數據量
- [ ] `sustained_load_test.py` - 持久性測試
- [ ] `cache_performance_analyzer.py` - 快取分析
- [ ] `generate_report.py` - 報告生成

### 輔助
- [ ] `fixtures/sample_markdowns.py` - 測試數據生成
- [ ] `requirements-stress.txt` - 依賴（aiohttp, psutil 等）

### 測試驗證
- [ ] 在本地運行基礎測試（100 應用）
- [ ] 驗證指標收集功能
- [ ] 驗證報告生成
- [ ] 文檔完整

---

## 關鍵實現細節

### 非阻塞 IO
所有網路請求必須使用 `aiohttp` 和 `asyncio`：
```python
async with aiohttp.ClientSession() as session:
    async with session.post(url, json=payload) as resp:
        latency_ms = resp.elapsed.total_seconds() * 1000
```

### 指標精度
- 延遲：毫秒級（ms）
- CPU/Memory：取整到 1 位小數
- 速率：apps/sec、QPS（每秒取樣）

### 快取命中率檢測
若 mcp-server 不提供命中/未命中標識，可通過：
```python
# 方法 1：檢查響應時間
if latency_ms < 5:  # 快取命中（內存讀取）
    cache_hit()
else:  # 快取未命中（Minio 讀取）
    cache_miss()
```

### 並發控制
使用信號量控制最大並發數：
```python
semaphore = asyncio.Semaphore(50)  # 最多 50 個並發請求

async def task():
    async with semaphore:
        # 執行請求
```

---

## 測試執行命令

```bash
# 第一輪：快速驗證（MOCK LLM）
docker compose up -d
export MOCK_LLM=true

python stress_test/generate_report.py \
  --phase all \
  --num-apps 100 \
  --duration 60 \
  --output-dir ./results

# 第二輪：真實 API（可選）
export MOCK_LLM=false
export MINIMAX_API_KEY=your_key

python stress_test/generate_report.py \
  --phase webhook \
  --num-apps 20 \
  --duration 300
```

---

## 預期輸出

測試完成後，應該在 `./results/` 目錄下生成：
```
results/
├── STRESS_TEST_REPORT_2026-05-10_MOCK.md         # 詳細報告
├── metrics_MOCK.json                             # 原始指標數據
├── cache_hit_distribution.png                    # 快取命中分佈圖
├── latency_distribution.png                      # 延遲分佈圖
├── memory_over_time.png                          # 記憶體趨勢圖
└── performance_summary.txt                       # 簡短摘要
```

---

## 下一步

這份指南提供了完整的路線圖。下一個 AI 應該：

1. 按照任務分解實現各個模塊
2. 優先實現基礎設施（metrics、config、logger）
3. 逐個實現測試場景
4. 最後集成所有結果到報告生成器

**重點**：實現過程中保持代碼的清潔性、可讀性和可重用性，便於後續優化和拓展。
