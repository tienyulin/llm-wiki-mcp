# Stress Test Runbook — 100+ Apps → wiki-processor (EXECUTOR: READ ALL OF THIS)

You are running a stress test of this project. Follow every step **in order**.
Copy every command's **full output** into a report. Do **not** change any code.

---

## 0. Your job and the rules (read first)

**Goal of the test.** More than 100 applications each push a README to
`wiki-processor` (`POST /process`) at the same time. We want to know:
1. Can the processor handle 100+ concurrent pushes (does every push succeed)?
2. Does it update the wiki **correctly** — each app's data stored, **app-isolated**,
   with **no lost writes** when many apps push at once?
3. Does it cause any problem (crash, timeout, data loss, retries, slowdown)?
4. Are the `mcp-server` query results **correct** afterward?

**Your rules:**
- **Observe and record only. Do NOT fix or change any code.** We analyze later.
- **Record EVERYTHING**: every command you run and its **complete output**, every
  problem (copy the exact error text / traceback), and all results.
- **If a step fails, DO NOT STOP.** Write down exactly what happened and continue
  with the remaining steps that can still run.
- At the end, write a full report to `tests/stress/RESULTS_<YYYY-MM-DD>.md`
  (use today's date) using the template in Section 10, then commit it.

**Helper script.** Use `tests/stress/push_apps.py` (already in this branch). It
is **pure Python stdlib — no `pip install` needed**. It pushes apps and verifies
results over HTTP. Run all commands from the **repo root**.

> Note: the older `tests/stress/test_real_service_stress.py` has bugs (it imports
> `storage.minio_client` which does not exist — the module is
> `repository.minio_client` — and it needs `aiohttp`). **Do not use it.** Use
> `push_apps.py`. If you try the old one and it errors, just record the error.

---

## 1. Environment check (record this)

Docker Desktop must be **running**. Then record versions:
```bash
docker info >/dev/null 2>&1 && echo "docker daemon UP" || echo "docker daemon DOWN — start Docker Desktop and wait"
docker --version
docker compose version
python3 --version
uname -a            # OS / arch
sysctl -n hw.ncpu 2>/dev/null || nproc    # CPU count
```
Write all of this into the report under "Environment".

---

## 2. Bring up the stack (PG/pgvector is ON by default)

```bash
docker compose down -v
docker compose up -d --build
```
Wait ~30–60s, then check health (re-run until both return JSON):
```bash
docker compose ps
curl -s localhost:8001/health ; echo
curl -s localhost:8002/health ; echo
```
**Expected:** `wiki-minio` and `wiki-pg` show `(healthy)`; `wiki-processor` and
`mcp-server` are `Up`. `:8001/health` contains `"vector_index_connected":true`.
`:8002/health` is `{"status":"ok"}`.

If `wiki-processor` is **not** Up, record:
```bash
docker compose ps -a
docker compose logs --tail=60 wiki-processor
```
…then re-run `docker compose up -d` once and re-check. Record what you saw.

---

## 3. Baseline (empty wiki)

```bash
curl -s localhost:8002/wiki_info | python3 -m json.tool
curl -s localhost:8001/status   | python3 -m json.tool
```
**Expected:** `modules: 0`, `total_endpoints: 0`, `wiki_size: 0` (fresh). Record.

---

## 4. RUN A — 150 apps (primary, PG on)

Push:
```bash
python3 tests/stress/push_apps.py push --n 150 | tee /tmp/runA_push.txt
```
**Expected:** `succeeded: 150/150`, then `PUSH RESULT: PASS`. Record the whole
output (succeeded count, apps/sec, p50/p95/max latency, any FAILED lines).

Verify with the script:
```bash
python3 tests/stress/push_apps.py verify --n 150 --pg on | tee /tmp/runA_verify.txt
```
**Expected:** `VERIFY RESULT: PASS` (all checks PASS). Record the whole output.

Manual spot-checks (record each):
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
**Expected:** modules `150`; each detail has `path: /stress-app-NNN/items`,
`source_app: stress-app-NNN`; search `mode: pg_keyword`; semantic `mode: semantic`
and `GET /stress-app-042/items` appears in results.

---

## 5. Isolation / incremental-update test (very important)

Re-push ONE app with a **different** endpoint, then prove only that app changed:
```bash
python3 tests/stress/push_apps.py update-one --app stress-app-005 | tee /tmp/runA_update.txt
```
Verify:
```bash
# app-005 should now have ONLY the new endpoint (old GET gone)
curl -s localhost:8002/list_apis | python3 -c "import sys,json;print('app-005:',json.load(sys.stdin)['modules'].get('stress-app-005'))"
# totals must be UNCHANGED (replaced, not added): still 150 / 150
curl -s localhost:8002/wiki_info | python3 -c "import sys,json;d=json.load(sys.stdin);print('modules:',d['modules'],'endpoints:',d['total_endpoints'])"
# a neighbor app must be untouched
curl -s "localhost:8002/get_api_detail?module=stress-app-004&api_key=GET%20/stress-app-004/items" | python3 -m json.tool
```
**Expected:** `app-005: ['POST /stress-app-005/orders']` (old `GET` gone);
`modules: 150`, `total_endpoints: 150` (unchanged); `stress-app-004` still has its
`GET /stress-app-004/items`. This proves app-level isolation + no cross-app clobber.
Record all three.

---

## 6. Problem scan for RUN A (record any hits)

```bash
docker compose ps -a
docker compose logs wiki-processor mcp-server 2>&1 | grep -iE "error|traceback|exception|conflict|retry|exhaust" | tail -40
docker stats --no-stream
```
Record: any container `Restarting`/`Exited`, any traceback, any CAS
retry/conflict warnings, and the CPU/MEM of `wiki-processor`, `mcp-server`, `wiki-pg`.

---

## 7. RUN B — 300 apps (stretch / breaking point)

Clean slate, bring up again, push 300:
```bash
docker compose down -v && docker compose up -d --build
# wait for health (repeat Section 2 checks)
python3 tests/stress/push_apps.py push   --n 300 | tee /tmp/runB_push.txt
python3 tests/stress/push_apps.py verify  --n 300 --pg on | tee /tmp/runB_verify.txt
```
Then repeat the Section 6 problem scan.
**Record especially:** did all 300 succeed? any lost updates (verify FAIL on the
"every app present" check)? latency vs 150 (did p95/max jump)? any HTTP 5xx,
timeouts, CAS retry exhaustion, or container crash? Is `vector_index.entries == 300`?

---

## 8. RUN C — 150 apps with PG DISABLED (compare + fallback)

```bash
docker compose down -v
PG_DSN= docker compose up -d --build minio wiki-processor mcp-server
# wait for health; this time :8001/health should show "vector_index_connected":false
curl -s localhost:8001/health ; echo
python3 tests/stress/push_apps.py push   --n 150 | tee /tmp/runC_push.txt
python3 tests/stress/push_apps.py verify  --n 150 --pg off | tee /tmp/runC_verify.txt
```
**Expected:** push still 150/150; verify PASS with `search mode: wiki_scan` and
`semantic mode: keyword_fallback`; `vector_index.available: false`. Compare the
push latency (p50/p95) against RUN A to show the PG-sync overhead. Record.

---

## 9. Teardown

```bash
docker compose down -v
```

---

## 10. REQUIRED REPORT — write to `tests/stress/RESULTS_<YYYY-MM-DD>.md` and commit

Fill in **every** section. Paste real command output, not summaries.

```markdown
# Stress Test Results — <DATE>

## Environment
- docker / compose / python3 versions, OS, CPU, RAM  (from Section 1)

## Process log (what I actually did)
- For each Section (2–8): the commands I ran and their FULL output.
  (Paste /tmp/runA_push.txt, runA_verify.txt, runB_*, runC_*, etc.)

## Problems found
- For each problem: which step, the EXACT error text / traceback, and what I
  observed. "None" if truly none. Include the known old-script bug if you hit it.

## Results table
| Run | N | PG | submits ok | apps/sec | p50 ms | p95 ms | max ms | lost updates | modules | endpoints | PG entries | verdict |
|-----|---|----|-----------|----------|--------|--------|--------|--------------|---------|-----------|------------|---------|
| A   |150| on |           |          |        |        |        |              |         |           |            |         |
| B   |300| on |           |          |        |        |        |              |         |           |            |         |
| C   |150| off|           |          |        |        |        |              |         | N/A (off) |            |         |

## Isolation test result
- app-005 after v2 update; totals before/after; neighbor app state. PASS/FAIL.

## Log excerpts
- Relevant lines from `docker compose logs` (errors/retries) and `docker stats`.

## Analysis & conclusions
- Did the processor handle 100+ apps? Correct + isolated + no lost writes?
- Where (if anywhere) did it start to struggle (300?)? PG overhead vs no-PG?
- Open questions / anything that needs a closer look.
```

## Pass criteria (per run)
- 100% submits succeed (`PUSH RESULT: PASS`)
- `verify` all checks PASS: modules == N, total_endpoints == N, **no missing apps**
  (no lost updates), each app isolated to its own endpoint
- isolation test: only the updated app changed; totals unchanged; neighbor intact
- PG-on runs: `vector_index.entries == embedded == N`; semantic finds samples
- no container crash/restart; no unhandled HTTP 5xx
