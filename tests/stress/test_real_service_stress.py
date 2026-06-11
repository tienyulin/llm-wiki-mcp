#!/usr/bin/env python3
"""
真實服務壓力測試：100 個應用並發提交到運行中的 wiki-processor + MinIO。

與 mock storage 的壓力測試不同，這個腳本打真實的 HTTP 服務與真實的
MinIO（含真實的 ETag 條件寫入），驗證：
1. 100 個並發提交全部成功
2. 無 lost update：每個應用的 API entries 都出現在最終 wiki（mock LLM
   會從輸入 markdown 推導 entries，因此 per-app 完整性可以驗證）
3. 審計記錄完整（append-only audit/ 物件，每次提交一筆）

前置條件：
  - wiki-processor 運行於 WIKI_PROCESSOR_URL（預設 http://localhost:8001）
  - mcp-server 運行於 MCP_SERVER_URL（預設 http://localhost:8002）
  - MOCK_LLM=true（避免真實 LLM 呼叫）
  - 若 processor 啟用認證，設定 PROCESSOR_API_KEY

執行：
  python tests/stress/test_real_service_stress.py
"""

import asyncio
import os
import sys
import time

import aiohttp

WIKI_PROCESSOR_URL = os.getenv("WIKI_PROCESSOR_URL", "http://localhost:8001")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8002")
N_APPS = int(os.getenv("STRESS_N_APPS", "100"))


def app_markdown(app: str) -> dict:
    return {
        f"{app}_api.md": f"""---
title: "{app} API"
---

# {app} API

GET /{app}/items
""",
    }


def _headers() -> dict:
    key = os.getenv("PROCESSOR_API_KEY")
    return {"X-API-Key": key} if key else {}


async def submit(session: aiohttp.ClientSession, app: str) -> tuple[bool, int]:
    """回傳 (成功與否, server 端 processing_time_ms)。"""
    payload = {
        "markdowns": app_markdown(app),
        "timestamp": "2026-06-11T00:00:00",
        "trigger_info": {"source": "stress-test"},
        "source_app": app,
        "source_version": "v1.0.0",
    }
    async with session.post(
        f"{WIKI_PROCESSOR_URL}/process", json=payload, headers=_headers()
    ) as resp:
        if resp.status != 200:
            return False, 0
        body = await resp.json()
        return body.get("status") == "success", body.get("processing_time_ms", 0)


def _percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))
    return ordered[idx]


async def verify_vector_index(session: aiohttp.ClientSession, apps: list[str]) -> bool:
    """向量索引啟用時：驗證 PG 完整性與抽樣語意可尋性；未啟用時跳過。

    量化 PG 同步開銷時，比較有/無 PG_DSN 兩次執行印出的 p50/p95。
    """
    async with session.get(f"{MCP_SERVER_URL}/wiki_info") as resp:
        info = await resp.json()
    vector_index = info.get("vector_index", {})
    if not vector_index.get("available"):
        print("\n（向量索引未啟用，跳過 PG 完整性驗證）")
        return True

    entries = vector_index.get("entries", 0)
    embedded = vector_index.get("embedded", 0)
    print(f"\n向量索引：entries={entries}, embedded={embedded}")
    if entries < N_APPS:
        print(f"❌ PG 索引 entries ({entries}) < 提交應用數 ({N_APPS})")
        return False

    # 抽樣 5 個應用驗證語意可尋（mock embeddings 下 token 重疊即可命中）
    step = max(1, N_APPS // 5)
    sampled = [apps[i] for i in range(0, N_APPS, step)][:5]
    for app in sampled:
        query = f"{app} items"
        async with session.get(
            f"{MCP_SERVER_URL}/semantic_search", params={"query": query, "top_k": 3}
        ) as resp:
            body = await resp.json()
        results = body.get("results", [])
        top_keys = [r.get("api_key") for r in results]
        if body.get("mode") != "semantic" or f"GET /{app}/items" not in top_keys:
            print(f"❌ 語意搜尋找不到 {app}：mode={body.get('mode')}, top={top_keys}")
            return False
    print(f"語意抽樣驗證：{len(sampled)}/{len(sampled)} 個應用可由 /semantic_search 找到")
    return True


async def main() -> int:
    apps = [f"stress-app-{i:03d}" for i in range(N_APPS)]

    print("=" * 70)
    print(f"真實服務壓力測試：{N_APPS} 個應用並發提交（CAS pipeline）")
    print("=" * 70)

    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        start = time.time()
        results = await asyncio.gather(*[submit(session, app) for app in apps])
        elapsed = time.time() - start

        succeeded = sum(ok for ok, _ in results)
        latencies = [ms for ok, ms in results if ok]
        print(f"\n提交結果：{succeeded}/{N_APPS} 成功，{elapsed:.2f} 秒"
              f"（{N_APPS / elapsed:.1f} apps/sec）")
        print(f"processing_time_ms：p50={_percentile(latencies, 50)} "
              f"p95={_percentile(latencies, 95)} max={max(latencies, default=0)}"
              f"（有/無 PG_DSN 各跑一次即可量化索引同步的 per-app 開銷）")

        async with session.get(f"{MCP_SERVER_URL}/wiki_info") as resp:
            info = await resp.json()
        print(f"mcp-server wiki_info：{info}")

        vector_ok = await verify_vector_index(session, apps)

    # 直接從 MinIO 讀回驗證 per-app 完整性與審計
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../wiki-processor"))
    from storage.minio_client import MinioStorage  # noqa: E402

    storage = MinioStorage()
    wiki = storage.get_json("wiki.json") or {}
    apis = wiki.get("apis", {})
    missing = [app for app in apps if f"GET /{app}/items" not in apis.get(app, {})]

    audit_keys = [k for k in storage.list_files("audit/")]
    audit_success = 0
    for k in audit_keys:
        entry = storage.get_json(k) or {}
        if entry.get("source_app", "").startswith("stress-app-") and entry.get("status") == "success":
            audit_success += 1

    print(f"\n驗證：wiki schema_version = {wiki.get('schema_version')}")
    print(f"驗證：{N_APPS - len(missing)}/{N_APPS} 個應用的 entries 存在於 wiki（無 lost update）")
    print(f"驗證：audit 物件中有 {audit_success}/{N_APPS} 筆 stress-app 成功記錄")

    if succeeded == N_APPS and not missing and audit_success >= N_APPS and vector_ok:
        print("\n✅ 壓力測試通過：100% 成功、無 lost update、audit 完整、向量索引一致")
        return 0

    if missing:
        print(f"\n❌ Lost updates: {missing[:10]}{'...' if len(missing) > 10 else ''}")
    print("\n❌ 壓力測試失敗")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
