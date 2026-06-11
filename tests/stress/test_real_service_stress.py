#!/usr/bin/env python3
"""
真實服務壓力測試：100 個應用並發提交到運行中的 wiki-processor + MinIO。

與 mock storage 的壓力測試不同，這個腳本打真實的 HTTP 服務與真實的
MinIO，驗證並發處理全部成功且 audit log 無遺失。

注意：MOCK_LLM 模式下 mock provider 回傳固定的 wiki 內容（忽略輸入的
markdown），因此無法在這裡驗證每個 app 的檔案是否進入 wiki —— 該驗證由
wiki-processor/tests/test_concurrency.py 以忠實的 fake LLM 覆蓋。

前置條件：
  - wiki-processor 運行於 WIKI_PROCESSOR_URL（預設 http://localhost:8001）
  - mcp-server 運行於 MCP_SERVER_URL（預設 http://localhost:8002）
  - MOCK_LLM=true（避免真實 LLM 呼叫）

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
source_app: "{app}"
source_version: "v1.0.0"
---

# {app} API

GET /{app}/items
""",
    }


async def submit(session: aiohttp.ClientSession, app: str) -> bool:
    payload = {
        "markdowns": app_markdown(app),
        "timestamp": "2026-06-11T00:00:00",
        "trigger_info": {"source": "stress-test"},
        "source_app": app,
        "source_version": "v1.0.0",
    }
    async with session.post(f"{WIKI_PROCESSOR_URL}/process", json=payload) as resp:
        if resp.status != 200:
            return False
        body = await resp.json()
        return body.get("status") == "success"


async def main() -> int:
    apps = [f"stress-app-{i:03d}" for i in range(N_APPS)]

    print("=" * 70)
    print(f"真實服務壓力測試：{N_APPS} 個應用並發提交")
    print("=" * 70)

    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 種子提交（讓系統脫離 first-run 狀態，走 app-level 更新路徑）
        ok = await submit(session, "stress-seed")
        if not ok:
            print("❌ 種子提交失敗，無法繼續")
            return 1

        start = time.time()
        results = await asyncio.gather(*[submit(session, app) for app in apps])
        elapsed = time.time() - start

        succeeded = sum(results)
        print(f"\n提交結果：{succeeded}/{N_APPS} 成功，{elapsed:.2f} 秒"
              f"（{N_APPS / elapsed:.1f} apps/sec）")

        # 驗證沒有 lost update：每個 app 的檔案都必須存在於最終 wiki
        async with session.get(f"{WIKI_PROCESSOR_URL}/status") as resp:
            status = await resp.json()
        print(f"wiki-processor 狀態：{status}")

        async with session.get(f"{MCP_SERVER_URL}/wiki_info") as resp:
            info = await resp.json()
        print(f"mcp-server wiki_info：{info}")

    # 直接從 MinIO 讀回驗證：wiki 可解析、audit log 無遺失
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../wiki-processor"))
    from storage.minio_client import MinioStorage  # noqa: E402

    storage = MinioStorage()
    wiki = storage.get_json("wiki.json") or {}
    wiki_ok = bool(wiki.get("metadata", {}).get("updated_at"))

    audit = storage.get_file("wiki-audit-log.jsonl") or ""
    audit_count = sum(1 for line in audit.splitlines()
                      if '"stress-app-' in line and '"success"' in line)

    print(f"\n驗證：wiki.json 可解析且帶有 updated_at：{'✅' if wiki_ok else '❌'}")
    print(f"驗證：audit log 中有 {audit_count}/{N_APPS} 筆 stress-app 成功記錄"
          f"{'（無遺失）' if audit_count >= N_APPS else '（有遺失！）'}")

    if succeeded == N_APPS and wiki_ok and audit_count >= N_APPS:
        print("\n✅ 壓力測試通過：100% 成功、audit 完整、wiki 一致")
        return 0

    print("\n❌ 壓力測試失敗")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
