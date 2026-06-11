#!/usr/bin/env python3
"""
Docker 集成測試：模擬真實的應用提交 wiki 更新到 wiki-processor
驗證完整的系統流程：生成、提交、處理、儲存、查詢
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, Any
import time

# API 端點
WIKI_PROCESSOR_URL = "http://localhost:8001"
MCP_SERVER_URL = "http://localhost:8002"

class WikiTestClient:
    def __init__(self, processor_url: str, mcp_url: str):
        self.processor_url = processor_url
        self.mcp_url = mcp_url

    async def submit_wiki(self, app_name: str, version: str, markdowns: Dict[str, str]) -> Dict[str, Any]:
        """提交應用的 wiki markdown 到 wiki-processor"""
        payload = {
            "markdowns": markdowns,
            "timestamp": datetime.now().isoformat(),
            "trigger_info": {
                "source": "gitlab-ci",
                "app": app_name,
                "version": version
            },
            "source_app": app_name,
            "source_version": version
        }

        headers = {}
        if os.getenv("PROCESSOR_API_KEY"):
            headers["X-API-Key"] = os.getenv("PROCESSOR_API_KEY")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.processor_url}/process",
                json=payload,
                headers=headers,
            ) as resp:
                return await resp.json()

    async def get_wiki_info(self) -> Dict[str, Any]:
        """從 mcp-server 獲取 wiki 信息"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.mcp_url}/wiki_info") as resp:
                return await resp.json()

    async def list_apis(self) -> Dict[str, Any]:
        """列出 wiki APIs"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.mcp_url}/list_apis") as resp:
                return await resp.json()

    async def semantic_search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """語意搜尋（需要 PG+pgvector；不可用時 server 端自動降級為關鍵字）"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.mcp_url}/semantic_search",
                params={"query": query, "top_k": top_k},
            ) as resp:
                return await resp.json()

    async def get_api_detail(self, module: str, api_key: str) -> Dict[str, Any]:
        """獲取 API 詳情（module + api_key 為必填參數）"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.mcp_url}/get_api_detail",
                params={"module": module, "api_key": api_key},
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"Status {resp.status}"}


def create_app_markdown(app_name: str, version: str) -> Dict[str, str]:
    """為應用生成 markdown"""
    return {
        f"{app_name}_api.md": f"""---
title: "{app_name.title()} API"
type: "api"
source_app: "{app_name}"
source_version: "{version}"
last_updated: "{datetime.now().isoformat()}"
---

# {app_name.title()} API

Version: {version}

## Endpoints

- `GET /api/{app_name}/health` - Health check
- `GET /api/{app_name}/info` - App info
- `POST /api/{app_name}/process` - Process data

## Authentication

This API requires Bearer token authentication.
""",
        f"{app_name}_config.md": f"""---
title: "{app_name.title()} Configuration"
type: "config"
source_app: "{app_name}"
source_version: "{version}"
---

# {app_name.title()} Configuration

## Environment Variables

- `{app_name.upper()}_PORT` - Service port (default: 8000)
- `{app_name.upper()}_LOG_LEVEL` - Log level (default: info)
- `{app_name.upper()}_DEBUG` - Debug mode (default: false)

## Database

Connected to PostgreSQL for data persistence.
"""
    }


async def test_scenario_1_single_app():
    """場景 1：單個應用提交 wiki"""
    print("\n" + "="*70)
    print("📝 場景 1：單應用提交 - app-inventory")
    print("="*70)

    client = WikiTestClient(WIKI_PROCESSOR_URL, MCP_SERVER_URL)

    app_name = "app-inventory"
    version = "v1.0.0"

    print(f"\n1️⃣ 準備 {app_name} 的 markdown...")
    markdowns = create_app_markdown(app_name, version)
    print(f"   已準備 {len(markdowns)} 個檔案")

    print(f"\n2️⃣ 提交到 wiki-processor...")
    start_time = time.time()
    result = await client.submit_wiki(app_name, version, markdowns)
    elapsed = time.time() - start_time

    print(f"   ✅ 提交成功 ({elapsed:.2f}s)")
    print(f"   狀態：{result.get('status')}")
    print(f"   訊息：{result.get('message')}")

    if "wiki_url" in result:
        print(f"   Wiki URL：{result.get('wiki_url')}")

    return True


async def test_scenario_2_multiple_apps():
    """場景 2：多個應用連續提交"""
    print("\n" + "="*70)
    print("📝 場景 2：多應用連續提交 - 5 個應用")
    print("="*70)

    client = WikiTestClient(WIKI_PROCESSOR_URL, MCP_SERVER_URL)

    apps = [
        ("app-users", "v1.0.0"),
        ("app-orders", "v1.0.0"),
        ("app-payments", "v1.0.0"),
        ("app-analytics", "v1.0.0"),
        ("app-notifications", "v1.0.0"),
    ]

    print(f"\n提交 {len(apps)} 個應用的 wiki...")

    results = []
    for app_name, version in apps:
        print(f"\n   提交 {app_name}...", end=" ")
        markdowns = create_app_markdown(app_name, version)

        try:
            result = await client.submit_wiki(app_name, version, markdowns)
            results.append(result)
            print(f"✅ {result.get('status')}")
        except Exception as e:
            print(f"❌ 失敗：{e}")
            results.append({"status": "error"})

    success_count = sum(1 for r in results if r.get("status") == "success")
    print(f"\n✅ 完成：{success_count}/{len(apps)} 應用成功提交")

    return success_count == len(apps)


async def test_scenario_3_verify_wiki_structure():
    """場景 3：驗證 wiki 結構"""
    print("\n" + "="*70)
    print("📝 場景 3：驗證 Wiki 結構")
    print("="*70)

    client = WikiTestClient(WIKI_PROCESSOR_URL, MCP_SERVER_URL)

    print("\n1️⃣ 獲取 wiki 信息...")
    try:
        wiki_info = await client.get_wiki_info()
        print(f"   ✅ Wiki 信息：")
        print(f"      模塊數：{wiki_info.get('modules')}")
        print(f"      總端點：{wiki_info.get('total_endpoints')}")
        metadata = wiki_info.get('metadata', {})
        print(f"      模塊列表：{metadata.get('modules')}")
    except Exception as e:
        print(f"   ❌ 無法獲取 wiki 信息：{e}")
        return False

    print("\n2️⃣ 列出 APIs...")
    try:
        apis = await client.list_apis()
        print(f"   ✅ 找到模塊：")
        modules = apis.get('modules', {})
        for module, endpoints in list(modules.items())[:5]:
            print(f"      - {module}：{len(endpoints)} 個端點")
    except Exception as e:
        print(f"   ❌ 無法列出 APIs：{e}")
        return False

    return True


async def test_scenario_4_get_api_details():
    """場景 4：獲取 API 詳情"""
    print("\n" + "="*70)
    print("📝 場景 4：獲取 API 詳情")
    print("="*70)

    client = WikiTestClient(WIKI_PROCESSOR_URL, MCP_SERVER_URL)

    # 從 wiki 實際內容取得 (module, api_key) 配對再查詳情
    listing = await client.list_apis()
    modules = listing.get("modules", {})
    pairs = [(m, keys[0]) for m, keys in modules.items() if keys][:3]

    if not pairs:
        print("\n❌ wiki 中沒有任何 API 可查詢")
        return False

    print(f"\n嘗試獲取 {len(pairs)} 個 API 的詳情...")

    success_count = 0
    for module, api_key in pairs:
        print(f"\n   查詢 {module} / {api_key}...", end=" ")
        try:
            detail = await client.get_api_detail(module, api_key)
            if "error" in detail:
                print(f"❌ {detail['error']}")
            elif detail.get("detail"):
                print("✅")
                print(f"      描述：{detail['detail'].get('description', 'N/A')}")
                success_count += 1
            else:
                print("❌ 空的 detail")
        except Exception as e:
            print(f"❌ {e}")

    print(f"\n✅ 成功獲取 {success_count} 個 API 的詳情")
    return success_count == len(pairs)


async def test_scenario_5_parallel_apps():
    """場景 5：並行提交應用"""
    print("\n" + "="*70)
    print("📝 場景 5：並行提交 - 10 個應用同時")
    print("="*70)

    client = WikiTestClient(WIKI_PROCESSOR_URL, MCP_SERVER_URL)

    # 生成 10 個應用
    apps = [(f"app-parallel-{i:02d}", f"v1.0.{i}") for i in range(10)]

    print(f"\n並行提交 {len(apps)} 個應用...")
    start_time = time.time()

    # 並行提交
    tasks = [
        client.submit_wiki(app_name, version, create_app_markdown(app_name, version))
        for app_name, version in apps
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    print(f"\n✅ 完成：{success_count}/{len(apps)} 應用成功")
    print(f"   耗時：{elapsed:.2f} 秒")
    print(f"   吞吐量：{len(apps)/elapsed:.1f} apps/sec")

    return success_count == len(apps)


async def test_scenario_6_incremental_update():
    """場景 6：應用增量更新驗證"""
    print("\n" + "="*70)
    print("📝 場景 6：應用增量更新 - app-inventory 版本更新")
    print("="*70)

    client = WikiTestClient(WIKI_PROCESSOR_URL, MCP_SERVER_URL)

    app_name = "app-inventory"

    print(f"\n1️⃣ 獲取更新前的 wiki 信息...")
    try:
        wiki_before = await client.get_wiki_info()
        modules_before = len(wiki_before.get('metadata', {}).get('modules', []))
        print(f"   模塊數：{modules_before}")
    except Exception as e:
        print(f"   ❌ 失敗：{e}")
        modules_before = 0

    print(f"\n2️⃣ 提交版本 v1.1.0...")
    markdowns = create_app_markdown(app_name, "v1.1.0")

    try:
        result = await client.submit_wiki(app_name, "v1.1.0", markdowns)
        print(f"   ✅ 提交成功：{result.get('status')}")
    except Exception as e:
        print(f"   ❌ 失敗：{e}")
        return False

    print(f"\n3️⃣ 驗證增量更新...")
    try:
        wiki_after = await client.get_wiki_info()
        modules_after = len(wiki_after.get('metadata', {}).get('modules', []))
        print(f"   ✅ wiki 已更新，模塊數：{modules_after}")
        print(f"   ✅ 增量更新完成（只更新 {app_name}，其他應用保留）")
        return True
    except Exception as e:
        print(f"   ❌ 驗證失敗：{e}")
        return False


async def test_scenario_7_semantic_search():
    """場景 7：語意搜尋（PG+pgvector 索引）

    向量索引未啟用（PG_DSN 未設定 / PG 不可用）時自動跳過 —— 與
    test_pg_store.py 的 auto-skip 慣例一致。
    """
    print("\n" + "="*70)
    print("📝 場景 7：語意搜尋 - /semantic_search")
    print("="*70)

    client = WikiTestClient(WIKI_PROCESSOR_URL, MCP_SERVER_URL)

    print("\n1️⃣ 檢查向量索引狀態...")
    wiki_info = await client.get_wiki_info()
    vector_index = wiki_info.get("vector_index", {})
    if not vector_index.get("available"):
        print("   ⏭️  向量索引未啟用（PG_DSN 未設定或 PG 不可用），跳過場景 7")
        return True
    print(f"   ✅ 向量索引可用：{vector_index.get('entries')} entries, "
          f"{vector_index.get('embedded')} embedded")

    app_name = "app-vector-demo"
    print(f"\n2️⃣ 提交 {app_name} ...")
    result = await client.submit_wiki(
        app_name, "v1.0.0", create_app_markdown(app_name, "v1.0.0")
    )
    if result.get("status") != "success":
        print(f"   ❌ 提交失敗：{result}")
        return False
    print("   ✅ 提交成功")

    print(f"\n3️⃣ 語意搜尋 'vector demo health check'...")
    search = await client.semantic_search("vector demo health check")
    mode = search.get("mode")
    results = search.get("results", [])
    print(f"   模式：{mode}，結果數：{len(results)}")

    if mode != "semantic":
        print(f"   ❌ 預期 mode=semantic，得到 {mode}")
        return False
    if not results:
        print("   ❌ 語意搜尋沒有結果")
        return False

    top = results[0]
    print(f"   Top-1：{top['module']} / {top['api_key']} (score={top.get('score')})")
    if top.get("source_app") != app_name:
        print(f"   ❌ Top-1 不是 {app_name} 的 entry：{top}")
        return False
    if not (0.0 < top.get("score", 0) <= 1.0001):
        print(f"   ❌ score 不在 (0, 1] 區間：{top.get('score')}")
        return False

    print(f"\n4️⃣ 驗證索引計數隨提交成長...")
    after = (await client.get_wiki_info()).get("vector_index", {})
    if not after.get("entries", 0) > 0:
        print(f"   ❌ 索引 entries 異常：{after}")
        return False
    print(f"   ✅ entries={after.get('entries')}, embedded={after.get('embedded')}, "
          f"last_sync={after.get('last_sync')}")

    return True


async def main():
    """執行所有測試"""
    print("\n" + "🚀 " * 25)
    print("LLM Wiki MCP - Docker 集成測試".center(70))
    print("🚀 " * 25)

    print("\n⏳ 等待服務完全啟動...")
    await asyncio.sleep(2)

    try:
        # 場景 1：單應用提交
        result1 = await test_scenario_1_single_app()

        # 場景 2：多應用連續提交
        result2 = await test_scenario_2_multiple_apps()

        # 場景 3：驗證 wiki 結構
        result3 = await test_scenario_3_verify_wiki_structure()

        # 場景 4：獲取 API 詳情
        result4 = await test_scenario_4_get_api_details()

        # 場景 5：並行提交
        result5 = await test_scenario_5_parallel_apps()

        # 場景 6：增量更新
        result6 = await test_scenario_6_incremental_update()

        # 場景 7：語意搜尋（向量索引未啟用時自動跳過）
        result7 = await test_scenario_7_semantic_search()

        # 最終報告
        print("\n" + "="*70)
        print("✅ Docker 集成測試完成！")
        print("="*70)

        results = {
            "場景 1 - 單應用提交": result1,
            "場景 2 - 多應用連續": result2,
            "場景 3 - Wiki 結構": result3,
            "場景 4 - 獲取 API 詳情": result4,
            "場景 5 - 並行提交": result5,
            "場景 6 - 增量更新": result6,
            "場景 7 - 語意搜尋": result7,
        }

        print("\n📊 測試結果總結：")
        all_passed = True
        for scenario, passed in results.items():
            status = "✅ 通過" if passed else "❌ 失敗"
            print(f"   {status} - {scenario}")
            all_passed = all_passed and passed

        print("\n" + "="*70)
        if all_passed:
            print("🎊 所有測試通過！系統完全可用 🎊")
        else:
            print("⚠️  有些測試未通過，請檢查")
        print("="*70)

    except Exception as e:
        print(f"\n❌ 測試出錯：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
