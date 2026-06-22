# 壓力測試 Runbook —— 100+ Apps → wiki-processor（執行者：全部讀完）

你正在跑這個專案的壓力測試。**照順序**做每一步。把每個指令的**完整輸出**抄進報告。
**不要改任何程式碼。**

> 名詞：**CAS** = ETag 樂觀鎖；**lost write** = 並發下被蓋掉的寫入；**app 隔離** = 一個 app
> 的更新不影響別的 app；**429** = 供應商限流（請求太多）。

---

## 0. 你的任務與規則（先讀）

**測試目標。** 100+ 個應用各自同時把 README 推給 `wiki-processor`（`POST /process`）。要知道：
1. processor 能不能扛 100+ 並發推送（每個都成功嗎）？
2. 它有沒有**正確**更新 wiki —— 每個 app 的資料都存了、**app 隔離**、多 app 同推時**無 lost write**？
3. 有沒有造成問題（crash、timeout、資料遺失、retry、變慢）？
4. 之後 `mcp-server` 的查詢結果**正確**嗎？

**規則：**
- **只觀察與記錄。不要修或改任何程式碼。** 之後再分析。
- **記錄一切**：跑的每個指令與其**完整輸出**、每個問題（抄確切錯誤/traceback）、所有結果。
- **某步失敗，不要停。** 寫下確切發生什麼，繼續還能跑的步驟。
- 最後把完整報告寫到 `tests/stress/RESULTS_<YYYY-MM-DD>.md`（用今天日期），格式見第 10 節，然後 commit。

**輔助腳本。** 用 `tests/stress/push_apps.py`（已在本分支）。它是**純 Python stdlib —— 不需
`pip install`**。它用 HTTP 推 app 並驗證結果。所有指令從 **repo root** 跑。

> 注意：舊的 `tests/stress/test_real_service_stress.py` 有 bug（它 import 不存在的
> `storage.minio_client` —— 模組是 `repository.minio_client` —— 且需要 `aiohttp`）。
> **不要用它。** 用 `push_apps.py`。若試了舊的並報錯，記下錯誤即可。

---

## 1. 環境檢查（記錄）

Docker Desktop 必須**運行中**。然後記版本：
```bash
docker info >/dev/null 2>&1 && echo "docker daemon UP" || echo "docker daemon DOWN — start Docker Desktop and wait"
docker --version
docker compose version
python3 --version
uname -a            # OS / arch
sysctl -n hw.ncpu 2>/dev/null || nproc    # CPU count
```
全部寫進報告的「Environment」。

---

## 2. 起 stack（PG/pgvector 預設開）

```bash
docker compose down -v
docker compose up -d --build
```
等 ~30–60s，再檢查健康（重跑直到兩者都回 JSON）：
```bash
docker compose ps
curl -s localhost:8001/health ; echo
curl -s localhost:8002/health ; echo
```
**預期：** `wiki-minio` 與 `wiki-pg` 顯示 `(healthy)`；`wiki-processor` 與 `mcp-server` 為 `Up`。
`:8001/health` 含 `"vector_index_connected":true`。`:8002/health` 為 `{"status":"ok"}`。

若 `wiki-processor` **沒**起來，記錄：
```bash
docker compose ps -a
docker compose logs --tail=60 wiki-processor
```
…再 `docker compose up -d` 一次並重查。記下你看到什麼。

---

## 3. Baseline（空 wiki）

```bash
curl -s localhost:8002/wiki_info | python3 -m json.tool
curl -s localhost:8001/status   | python3 -m json.tool
```
**預期：** `modules: 0`、`total_endpoints: 0`、`wiki_size: 0`（全新）。記錄。

---

## 4. RUN A —— 150 apps（主測，PG 開）

推：
```bash
python3 tests/stress/push_apps.py push --n 150 | tee /tmp/runA_push.txt
```
**預期：** `succeeded: 150/150`，然後 `PUSH RESULT: PASS`。記整段輸出（成功數、apps/sec、
p50/p95/max 延遲、任何 FAILED 行）。

用腳本驗證：
```bash
python3 tests/stress/push_apps.py verify --n 150 --pg on | tee /tmp/runA_verify.txt
```
**預期：** `VERIFY RESULT: PASS`（全部 PASS）。記整段輸出。

手動抽查（各記錄）：
```bash
# module count
curl -s localhost:8002/list_apis | python3 -c "import sys,json;m=json.load(sys.stdin)['modules'];print('modules:',len(m))"
# 3 detail samples
for a in stress-app-000 stress-app-075 stress-app-149; do
  curl -s "localhost:8002/get_api_detail?module=$a&api_key=GET%20/$a/items" | python3 -m json.tool
done
# search + semantic modes
curl -s 'localhost:8002/search_apis?query=stress-app-007'   | python3 -m json.tool
curl -s 'localhost:8002/semantic_search?query=stress-app-042%20items&top_k=3' | python3 -m json.tool
```
**預期：** modules `150`；每個 detail 有 `path: /stress-app-NNN/items`、`source_app:
stress-app-NNN`；search `mode: pg_keyword`；semantic `mode: semantic` 且結果含
`GET /stress-app-042/items`。

---

## 5. 隔離 / 增量更新測試（很重要）

用**不同的** endpoint 重推同一個 app，再證明只有那個 app 變了：
```bash
python3 tests/stress/push_apps.py update-one --app stress-app-005 | tee /tmp/runA_update.txt
```
驗證：
```bash
# app-005 現在應只有新 endpoint（舊 GET 不見）
curl -s localhost:8002/list_apis | python3 -c "import sys,json;print('app-005:',json.load(sys.stdin)['modules'].get('stress-app-005'))"
# 總數必須不變（取代，非新增）：仍 150 / 150
curl -s localhost:8002/wiki_info | python3 -c "import sys,json;d=json.load(sys.stdin);print('modules:',d['modules'],'endpoints:',d['total_endpoints'])"
# 鄰居 app 必須沒被動
curl -s "localhost:8002/get_api_detail?module=stress-app-004&api_key=GET%20/stress-app-004/items" | python3 -m json.tool
```
**預期：** `app-005: ['POST /stress-app-005/orders']`（舊 `GET` 不見）；`modules: 150`、
`total_endpoints: 150`（不變）；`stress-app-004` 仍有它的 `GET /stress-app-004/items`。
這證明 app 級隔離 + 無跨 app 覆蓋。三項都記。

---

## 6. RUN A 問題掃描（命中就記）

```bash
docker compose ps -a
docker compose logs wiki-processor mcp-server 2>&1 | grep -iE "error|traceback|exception|conflict|retry|exhaust" | tail -40
docker stats --no-stream
```
記：任何容器 `Restarting`/`Exited`、任何 traceback、任何 CAS retry/conflict 警告、以及
`wiki-processor`、`mcp-server`、`wiki-pg` 的 CPU/MEM。

---

## 7. RUN B —— 300 apps（拉伸 / 臨界點）

清空、重起、推 300：
```bash
docker compose down -v && docker compose up -d --build
# 等健康（重複第 2 節檢查）
python3 tests/stress/push_apps.py push   --n 300 | tee /tmp/runB_push.txt
python3 tests/stress/push_apps.py verify  --n 300 --pg on | tee /tmp/runB_verify.txt
```
然後重做第 6 節問題掃描。
**特別記：** 300 個都成功嗎？有 lost update 嗎（verify 在「每個 app 都在」這項 FAIL）？
延遲 vs 150（p95/max 跳很多嗎）？任何 HTTP 5xx、timeout、CAS retry 耗盡、容器 crash？
`vector_index.entries == 300` 嗎？

---

## 8. RUN C —— 150 apps、PG 關閉（對照 + fallback）

```bash
docker compose down -v
PG_DSN= docker compose up -d --build minio wiki-processor mcp-server
# 等健康；這次 :8001/health 應顯示 "vector_index_connected":false
curl -s localhost:8001/health ; echo
python3 tests/stress/push_apps.py push   --n 150 | tee /tmp/runC_push.txt
python3 tests/stress/push_apps.py verify  --n 150 --pg off | tee /tmp/runC_verify.txt
```
**預期：** push 仍 150/150；verify PASS 且 `search mode: wiki_scan`、`semantic mode:
keyword_fallback`；`vector_index.available: false`。把 push 延遲（p50/p95）跟 RUN A 比，
顯示 PG-sync 的開銷。記錄。

---

## 8b. RUN R —— REAL 測試（真 MiniMax LLM + 真 embedding）⚠️ 會花錢

Run A–C 用 `MOCK_LLM=true` / `MOCK_EMBEDDINGS=true`（無真 API 呼叫）。這次讓抽取**真實**：
真 MiniMax LLM + 真 OpenAI embedding，對同樣的真 MinIO/PG/HTTP 服務。規模較小（**N=50、
concurrency 5**），因為每個 `/process` 是真的 ~20–30s MiniMax 呼叫，**會花錢**且高並發會
**限流（HTTP 429）**。

### R.1 機密 —— 建 gitignored 的 `.env`（永不 commit；用完輪換 key）
先確認 `.env` 被忽略，再建：
```bash
git check-ignore .env && echo ".env is gitignored ✓"   # 必須印這行
cat > .env <<'EOF'
MOCK_LLM=false
LLM_PROVIDER=minimax
LLM_API_KEY=__PUT_MINIMAX_KEY_HERE__
LLM_MODEL=MiniMax-M3
MOCK_EMBEDDINGS=false
EMBEDDING_BASE_URL=https://api.openai.com
EMBEDDING_API_KEY=__PUT_OPENAI_KEY_HERE__
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
EOF
# 編輯 .env 貼上真 key
```
**安全：** key 只住在 `.env`。絕不把 key 貼進報告、commit 或 log。若 `git check-ignore .env`
什麼都沒印，停 —— 別把 key 寫進被追蹤的檔。

### R.2 用真設定起 stack
```bash
docker compose down -v && docker compose up -d --build
# 等，然後：
curl -s localhost:8001/health ; echo
```
**預期：** health 顯示 `"llm_provider":"minimax"`、`"minimax_accessible":true`、
`"vector_index_connected":true`。若 `"minimax_accessible":false` → key 錯/空：記下並停止
real run（先修 key）。

### R.3 跑 R —— 推 50 個真 app，節流、含 retry
```bash
python3 tests/stress/push_apps.py push   --n 50 --workers 5 --retries 3 | tee /tmp/runR_push.txt
python3 tests/stress/push_apps.py verify  --n 50 --mode real --pg on    | tee /tmp/runR_verify.txt
```
- 預期約 **5–15 分鐘**。比 mock 高延遲是正常的。
- `--mode real` **寬鬆**：真 LLM 自由命名 module/endpoint，所以它檢查每個 app **能用
  `source_app` 找到**，而非精確比對 endpoint。記完整輸出。
- 若有些 submit 因限流 FAILED，那是邊界上的預期 —— 記多少個、以及 `--retries` 有沒有救回。

### R.4 權威正確性（psql —— 即使 LLM 有變異也確定）
```bash
# 無遺失 app：distinct source_app 必須 == 50
docker compose exec -T pg psql -U wiki -d wiki -tA -c \
  "SELECT count(DISTINCT source_app) FROM api_entries WHERE source_app LIKE 'stress-app-%';"
docker compose exec -T pg psql -U wiki -d wiki -tA -c \
  "SELECT count(*) FROM app_sync WHERE source_app LIKE 'stress-app-%';"
# 每 app endpoint 數（真 LLM 可能抽 1+；記分布）
docker compose exec -T pg psql -U wiki -d wiki -c \
  "SELECT source_app, count(*) AS endpoints FROM api_entries WHERE source_app LIKE 'stress-app-%' GROUP BY source_app ORDER BY 1 LIMIT 12;"
```
**預期：** 兩個 count 都 == **50**（無 lost update）。記錄。

### R.5 抽取品質目視（跑真的的重點）
```bash
for a in stress-app-000 stress-app-025 stress-app-049; do
  echo "== $a =="
  docker compose exec -T pg psql -U wiki -d wiki -c \
    "SELECT module, api_key, left(description,80) FROM api_entries WHERE source_app='$a';"
done
# 真語意搜尋（現在是真 OpenAI 向量）：
curl -s 'localhost:8002/semantic_search?query=list%20items%20for%20stress-app-025&top_k=3' | python3 -m json.tool
```
記真 LLM 怎麼命名 module + endpoint（vs 輸入 README `# stress-app-NNN API` /
`GET /stress-app-NNN/items`），以及語意搜尋是否回 `"mode":"semantic"` 且命中合理。

### R.6 問題掃描（同第 6 節）+ 記錄
```bash
docker compose ps -a
docker compose logs wiki-processor 2>&1 | grep -iE "error|traceback|rate limit|429|conflict|retry" | tail -40
```

**RUN R 通過標準：** 50 個 submit 全成功（或每個失敗都有解釋，如記錄到的 429 + retry 後恢復）；
`count(DISTINCT source_app) == 50`（無遺失 app）；每個 app ≥1 抽出的 endpoint；
`semantic_search` 回 `"mode":"semantic"` 且命中合理；無容器 crash。

---

## 9. 收尾

```bash
docker compose down -v
# 完成後移除真 key 檔
rm -f .env
```

---

## 10. 必填報告 —— 寫到 `tests/stress/RESULTS_<YYYY-MM-DD>.md` 並 commit

填**每一**節。貼真實指令輸出，不要摘要。

```markdown
# Stress Test Results — <DATE>

## Environment
- docker / compose / python3 versions, OS, CPU, RAM  (from Section 1)

## Process log (what I actually did)
- For each Section (2–8b): the commands I ran and their FULL output.
  (Paste /tmp/runA_push.txt, runA_verify.txt, runB_*, runC_*, runR_*, etc.)

## Problems found
- For each problem: which step, the EXACT error text / traceback, and what I
  observed. "None" if truly none. Include the known old-script bug if you hit it.
  For Run R: note any rate-limit (429) failures and whether retries recovered them.

## Results table
| Run | N | LLM | PG | submits ok | apps/sec | p50 ms | p95 ms | max ms | lost updates | modules | endpoints | PG entries | verdict |
|-----|---|-----|----|-----------|----------|--------|--------|--------|--------------|---------|-----------|------------|---------|
| A   |150| mock| on |           |          |        |        |        |              |         |           |            |         |
| B   |300| mock| on |           |          |        |        |        |              |         |           |            |         |
| C   |150| mock| off|           |          |        |        |        |              |         | N/A (off) |            |         |
| R   | 50| REAL| on |           |          |        |        |        | (distinct source_app) |  |           |            |         |

## Isolation test result
- app-005 after v2 update; totals before/after; neighbor app state. PASS/FAIL.

## Real run (R) — extraction quality
- `count(DISTINCT source_app)` (must be 50) and per-app endpoint spread.
- For 3 sampled apps: how the real LLM named the module + endpoint vs the input
  README. Did it stay consistent across apps, or vary? Any apps it extracted
  0 endpoints for? Real-vector semantic_search sample.
- Rate-limit / cost notes: how many 429s, retries, total wall time.

## Log excerpts
- Relevant lines from `docker compose logs` (errors/retries) and `docker stats`.

## Analysis & conclusions
- Did the processor handle 100+ apps? Correct + isolated + no lost writes?
- Where (if anywhere) did it start to struggle (300?)? PG overhead vs no-PG?
- Open questions / anything that needs a closer look.
```

## 通過標準（每個 run）
- 100% submit 成功（`PUSH RESULT: PASS`）
- `verify` 全 PASS：modules == N、total_endpoints == N、**無遺失 app**（無 lost update）、
  每個 app 隔離在自己的 endpoint
- 隔離測試：只有被更新的 app 變了；總數不變；鄰居完好
- PG-on run：`vector_index.entries == embedded == N`；語意找得到樣本
- 無容器 crash/restart；無未處理的 HTTP 5xx
```
</content>
