#!/usr/bin/env python3
"""CI guard: committed openapi.json must match what the code generates — stdlib only.

Backstop for developers who didn't install the gen-openapi pre-commit hook: in CI,
regenerate the spec from code and compare to the committed openapi.json. Fail if
they differ (stale) so the wiki never ingests an out-of-date API surface.

Usage:
  python check_openapi_fresh.py --app app.main:app [--file openapi.json]
"""
import argparse
import importlib
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True, help="module:attr (uvicorn style)")
    ap.add_argument("--file", default="openapi.json")
    args = ap.parse_args()

    mod_name, attr = args.app.split(":", 1)
    try:
        app = getattr(importlib.import_module(mod_name), attr)
        fresh = app.openapi()
    except Exception as e:
        print(f"[fresh-check] 無法產生 spec（{e}）→ 跳過（非 OpenAPI app）"); return 0
    try:
        committed = json.load(open(args.file, encoding="utf-8"))
    except FileNotFoundError:
        print(f"[fresh-check] 缺 {args.file}，但 code 能產 spec → 請跑 gen_openapi.py 並 commit")
        return 1

    # Compare canonically (order-insensitive).
    if json.dumps(fresh, sort_keys=True) == json.dumps(committed, sort_keys=True):
        print("[fresh-check] OK — openapi.json 與程式碼一致")
        return 0
    print(f"[fresh-check] {args.file} 已過期：與程式碼產生的 spec 不一致。")
    print("請跑：python scripts/gen_openapi.py --app " + args.app + " 並 commit。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
