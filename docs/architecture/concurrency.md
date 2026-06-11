# 並發控制設計（Concurrency）

**狀態：** 已實作（2026-06-11）
**範圍：** wiki-processor 的 wiki 更新 pipeline 與 mcp-server 快取

---

## 問題

所有應用共用同一個 `wiki.json` 物件。`WikiProcessor.process()` 的流程是：

```
讀 snapshot/wiki  →  await LLM 呼叫  →  寫 wiki/snapshot  →  寫 audit log
```

讀與寫之間隔著一次 awaited LLM 呼叫（讓出 event loop 控制權）。沒有同步
機制時，並發請求會讀到相同的 wiki 狀態，後寫者覆蓋先寫者的結果。
實測 20 個並發 app 更新只有 1 個存活（lost update rate 95%）。

這與「支援 100+ 應用並行更新」的設計目標直接矛盾。

## 解法：process-local asyncio.Lock

`WikiProcessor` 持有一把 `asyncio.Lock`，`process()` 的完整 pipeline
（含失敗路徑的 audit log）都在鎖內執行。

**為什麼不用 per-app lock：** 所有 app 都 read-modify-write 同一個
`wiki.json`，per-app 鎖無法防止跨 app 的 lost update。

**取捨：**

| 面向 | 影響 |
|------|------|
| 正確性 | ✅ 單副本部署下完全消除 lost update（單元 + 真實服務壓測驗證） |
| 吞吐量 | LLM 呼叫被序列化。真實 LLM 每次呼叫秒級，吞吐 = 1/LLM延遲；mock 模式實測 ~20 apps/sec |
| 部署限制 | ⚠️ 鎖是 process-local 的，**只在單副本（目前 docker-compose 配置）下有效** |

## 已知限制與未來方向

1. **多副本部署**：需要存儲層的原子性 —— MinIO 條件寫入（ETag
   compare-and-swap）或外部鎖（Redis/etcd）。列為 Phase 9 前置工作。
2. **兩階段更新（吞吐優化）**：LLM 呼叫移出鎖外，鎖內只做
   re-read + merge + write。可將序列化窗口從秒級縮到毫秒級，
   但 merge 語意需要先把 wiki 資料模型統一（見下）。
3. **同步 MinIO client**：minio-py 是同步的，會阻塞 event loop。
   副作用是單一存儲操作對 coroutine 天然原子；遷移到
   `asyncio.to_thread` 時必須確保鎖仍覆蓋完整 read-modify-write。
4. **資料模型不一致**：wiki.json 同時存在兩種形態 ——
   結構化（`{"apis": {...}, "metadata": {...}}`，LLM 全量生成路徑）與
   檔案映射（`{"path.md": "content", ...}`，app-level 更新路徑）。
   merge 邏輯已用 `isinstance` 防護，但長期應統一 schema。

## mcp-server 快取一致性

mcp-server 讀取路徑帶 TTL 快取（預設 1 小時，key 為 `wiki`）。
一致性由 wiki-processor 在每次成功更新後呼叫
`POST /cache/invalidate`（best-effort，失敗只記 log）維持，
透過 `MCP_SERVER_URL` 環境變數設定目標。

快取失效採 key segment 精確比對（`:` 分隔），`app-1` 不會誤刪
`app-10`；共用的 `wiki` 條目聚合所有 app 的資料，任何 app 級失效
都會一併刪除它。

## 驗證

- `wiki-processor/tests/test_concurrency.py` — 20 個並發 `process()`
  以會讓出控制權的 fake LLM 驗證無 lost update、audit 完整。
  （移除鎖後此測試失敗：1/20 存活）
- `tests/stress/test_real_service_stress.py` — 100 個並發 app 打真實
  HTTP 服務 + 真實 MinIO：100% 成功、audit log 100/100 無遺失。
