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


async def submit(session: aiohttp.ClientSession, app: str) -> bool:
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
            return False
        body = await resp.json()
        return body.get("status") == "success"


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

        succeeded = sum(results)
        print(f"\n提交結果：{succeeded}/{N_APPS} 成功，{elapsed:.2f} 秒"
              f"（{N_APPS / elapsed:.1f} apps/sec）")

        async with session.get(f"{MCP_SERVER_URL}/wiki_info") as resp:
            info = await resp.json()
        print(f"mcp-server wiki_info：{info}")

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

    if succeeded == N_APPS and not missing and audit_success >= N_APPS:
        print("\n✅ 壓力測試通過：100% 成功、無 lost update、audit 完整")
        return 0

    if missing:
        print(f"\n❌ Lost updates: {missing[:10]}{'...' if len(missing) > 10 else ''}")
    print("\n❌ 壓力測試失敗")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
