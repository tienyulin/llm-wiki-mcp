# 壓力測試任務清單

下面列出所有需要實現的文件和任務。

## 已完成
- ✅ `STRESS_TEST_IMPLEMENTATION_GUIDE.md` - 完整實作指南
- ✅ 目錄結構（`stress_test/`, `stress_test/utils/`, `stress_test/fixtures/`）
- ✅ 計劃文件更新（`/root/.claude/plans/document-sorted-castle.md`）

## 待實現

### 優先級 P1（基礎框架）
- [ ] `stress_test/utils/config.py` - 配置管理類
- [ ] `stress_test/utils/logger.py` - 日誌系統
- [ ] `stress_test/utils/metrics_collector.py` - 指標收集（CPU、記憶體、QPS、延遲分布）
- [ ] `stress_test/utils/__init__.py` - 導出公共接口
- [ ] `stress_test/fixtures/sample_markdowns.py` - 測試數據生成器

### 優先級 P2（核心測試場景）
- [ ] `stress_test/gitlab_webhook_simulator.py` - GitLab Webhook 模擬器
  - [ ] 生成 N 個應用的 markdown
  - [ ] 非阻塞並行 POST 請求
  - [ ] 延遲、吞吐量、錯誤率統計
  
- [ ] `stress_test/agent_concurrency_test.py` - AI agent 並發測試
  - [ ] 模擬 N 個 agent 的查詢
  - [ ] 三種查詢類型的混合
  - [ ] 快取命中率計算
  - [ ] 應用級快取失效模擬
  
- [ ] `stress_test/large_data_stress_test.py` - 大數據量測試
  - [ ] 場景 1：單應用大數據（1000 markdown）
  - [ ] 場景 2：多應用大數據（1GB）
  - [ ] 場景 3：漸進式增長（10->500 應用）

### 優先級 P3（專項測試）
- [ ] `stress_test/sustained_load_test.py` - 持久性壓力測試（30 分鐘）
  - [ ] 三階段流程：ramp up、peak、wave
  - [ ] 內存泄漏檢測
  - [ ] 性能穩定性驗證

- [ ] `stress_test/cache_performance_analyzer.py` - 快取效率分析
  - [ ] TTL 失效效率
  - [ ] 應用級失效効果
  - [ ] 快取熱度分佈（Zipfian 圖）
  - [ ] 多進程場景模擬

### 優先級 P4（報告和整合）
- [ ] `stress_test/generate_report.py` - 主驅動程序
  - [ ] 命令行解析（phase、num-apps、duration 等）
  - [ ] 執行所有測試
  - [ ] 收集結果
  - [ ] 生成 Markdown 報告
  
- [ ] `stress_test/utils/report_generator.py` - 報告生成工具
  - [ ] Markdown 格式化
  - [ ] 性能指標表格
  - [ ] 圖表生成（matplotlib）
  - [ ] 建議生成

### 優先級 P5（依賴和文檔）
- [ ] `stress_test/requirements-stress.txt` - 依賴列表
  - aiohttp, asyncio, psutil, matplotlib, pandas 等
  
- [ ] `stress_test/README.md` - 快速開始指南
  - 安裝依賴
  - 執行測試的各種方式
  - 結果解讀

- [ ] `stress_test/__init__.py` - 導出主要類

---

## 實現指南

### 文件依賴圖
```
generate_report.py (主驅動)
├── metrics_collector.py (所有測試都用)
├── config.py (所有測試都用)
├── logger.py (所有測試都用)
├── gitlab_webhook_simulator.py
├── agent_concurrency_test.py
├── large_data_stress_test.py
├── sustained_load_test.py
├── cache_performance_analyzer.py
├── report_generator.py
└── sample_markdowns.py (fixture)
```

### 實現順序
1. **第 1 步**：實現 `config.py`（最簡單，無依賴）
2. **第 2 步**：實現 `logger.py`（依賴 config）
3. **第 3 步**：實現 `metrics_collector.py`（依賴 logger、psutil）
4. **第 4 步**：實現 `sample_markdowns.py`（生成測試數據）
5. **第 5-8 步**：實現四個測試場景（都依賴前面的工具）
6. **第 9 步**：實現 `report_generator.py`
7. **第 10 步**：實現 `generate_report.py`（整合器）

---

## 測試驗證步驟

### 對於每個測試文件
```bash
# 1. 驗證 import（無 runtime 錯誤）
python -c "from stress_test.xxx import YYY"

# 2. 運行簡單的功能測試（如果提供了）
python stress_test/xxx.py --help

# 3. 在 Docker 環境中運行
docker compose up -d
MOCK_LLM=true python stress_test/xxx.py --test-mode
```

---

## 關鍵要求

### 代碼質量
- ✅ 使用 async/await（非阻塞 IO）
- ✅ 類型提示（Type hints）
- ✅ 錯誤處理（try/except，重試邏輯）
- ✅ 詳細的 docstring
- ✅ 日誌記錄（所有關鍵步驟）

### 性能
- ✅ 指標收集開銷 <1% CPU
- ✅ 不持久化大數據到磁盤（內存優先）
- ✅ 使用連接池重用 HTTP 連接

### 驗證
- ✅ 單元測試（至少測試核心邏輯）
- ✅ 集成測試（模擬完整流程）
- ✅ 邊界測試（0 應用、1 應用、10000 應用）

---

## 預期完成時間

- P1（基礎框架）：2-3 小時
- P2（核心測試）：4-5 小時  
- P3（專項測試）：2-3 小時
- P4（報告）：1-2 小時
- **總計**：9-13 小時

---

## 交付物

最終應該提交的文件：
- `stress_test/` 目錄（包含所有 .py 文件）
- `STRESS_TEST_RESULTS_*.md`（執行結果）
- 任何發現的瓶頸和優化建議

---

## 聯繫方式

如果下一個 AI 在實現過程中有問題，參考：
1. `STRESS_TEST_IMPLEMENTATION_GUIDE.md` - 詳細技術規格
2. 現有的 `test_*.py` 文件 - 參考代碼風格
3. `README.md` 和 `GITLAB_SETUP.md` - 系統架構背景
