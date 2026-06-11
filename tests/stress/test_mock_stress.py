#!/usr/bin/env python3
"""
Mock-storage 壓力測試：100 個應用並發更新（schema v2 / CAS pipeline）。

取代舊的 test_poc_standalone.py / test_poc_100_apps.py /
test_100_apps_performance.py —— 那些腳本驗證的是 v1 file-map 資料模型，
已不存在。本腳本以 in-memory CAS storage + 從輸入推導的 mock LLM 驗證：

1. 100 應用並發初始提交：全部成功、每個應用的 entries 都在 wiki 中
2. 重新提交會取代（而非累加）該應用自己的 entries
3. 應用隔離：更新 10 個應用不影響其他 90 個
4. 審計完整性：每次提交一筆 audit 記錄

執行：python tests/stress/test_mock_stress.py
"""

import asyncio
import copy
import os
import sys
import time

os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../wiki-processor"))

from services.llm.config import LLMConfig  # noqa: E402
from services.llm.providers.minimax import MinimaxProvider  # noqa: E402
from services.processor import WikiProcessor, _WIKI_KEY  # noqa: E402
from tests.test_concurrency import InMemoryCASStorage  # noqa: E402

N_APPS = int(os.getenv("STRESS_N_APPS", "100"))


def markdown(app: str, version: str) -> dict:
    return {f"{app}_api.md": f"# {app} API {version}\n\nGET /{app}/items/{version}\n"}


async def main() -> int:
    storage = InMemoryCASStorage()
    llm = MinimaxProvider(LLMConfig(provider="minimax", api_key="test-key", model="m"))
    processor = WikiProcessor(storage=storage, llm=llm)
    apps = [f"app-{i:03d}" for i in range(N_APPS)]
    failures: list[str] = []

    print("=" * 70)
    print(f"Mock 壓力測試：{N_APPS} 應用並發（schema v2 / CAS）")
    print("=" * 70)

    # --- 1. 並發初始提交 ---
    start = time.time()
    results = await asyncio.gather(*[
        processor.process(markdown(a, "v1"), "t", source_app=a, source_version="v1")
        for a in apps
    ])
    t1 = time.time() - start
    ok = sum(r.status == "success" for r in results)
    print(f"\n1️⃣ 初始提交：{ok}/{N_APPS} 成功，{t1:.2f}s（{N_APPS / t1:.0f} apps/sec）")
    if ok != N_APPS:
        failures.append("initial submissions")

    wiki = storage.data[_WIKI_KEY]
    missing = [a for a in apps if f"GET /{a}/items/v1" not in wiki["apis"].get(a, {})]
    print(f"   wiki 完整性：{N_APPS - len(missing)}/{N_APPS} 應用的 entries 存在")
    if missing:
        failures.append(f"lost updates: {missing[:5]}")

    # --- 2. 重新提交取代自身 entries ---
    target = apps[0]
    await processor.process(markdown(target, "v2"), "t", source_app=target, source_version="v2")
    entries = storage.data[_WIKI_KEY]["apis"][target]
    replaced = f"GET /{target}/items/v2" in entries and f"GET /{target}/items/v1" not in entries
    print(f"\n2️⃣ 版本更新取代舊 entries：{'✅' if replaced else '❌'}")
    if not replaced:
        failures.append("resubmission did not replace entries")

    # --- 3. 應用隔離 ---
    others_before = {
        a: copy.deepcopy(storage.data[_WIKI_KEY]["apis"][a]) for a in apps[10:]
    }
    await asyncio.gather(*[
        processor.process(markdown(a, "v3"), "t", source_app=a, source_version="v3")
        for a in apps[1:10]
    ])
    isolated = all(storage.data[_WIKI_KEY]["apis"][a] == others_before[a] for a in apps[10:])
    print(f"3️⃣ 應用隔離（更新 9 個，其餘 {N_APPS - 10} 個不受影響）：{'✅' if isolated else '❌'}")
    if not isolated:
        failures.append("isolation violated")

    # --- 4. 審計完整性 ---
    audit_count = len(storage.audit_entries())
    expected = N_APPS + 1 + 9
    print(f"4️⃣ 審計記錄：{audit_count}/{expected} {'✅' if audit_count == expected else '❌'}")
    if audit_count != expected:
        failures.append(f"audit count {audit_count} != {expected}")

    print("\n" + "=" * 70)
    if failures:
        print(f"❌ 壓力測試失敗：{failures}")
        return 1
    print("✅ Mock 壓力測試全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
