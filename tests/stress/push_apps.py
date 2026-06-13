#!/usr/bin/env python3
"""Self-contained stress pusher + verifier for the 100+ app stress test.

NO third-party dependencies — stdlib only (urllib, concurrent.futures). Run it
with the project's services already up (`docker compose up -d`).

Subcommands:
  push        Concurrently POST N app READMEs to wiki-processor /process.
  verify      Check mcp-server query results are correct for N apps.
  update-one  Re-push ONE app with a different endpoint (isolation test).

Each synthetic app is named `stress-app-NNN` (NNN = zero-padded index) and its
README declares exactly one endpoint: `GET /stress-app-NNN/items`.

Examples:
  python3 tests/stress/push_apps.py push       --n 150
  python3 tests/stress/push_apps.py verify     --n 150 --pg on
  python3 tests/stress/push_apps.py update-one --app stress-app-005
  python3 tests/stress/push_apps.py verify     --n 150 --pg off

Exit code is non-zero if any check FAILS (so a wrapper/CI notices), but every
check always prints its result so you can copy the full output into the report.
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_PROCESSOR = "http://localhost:8001"
DEFAULT_MCP = "http://localhost:8002"


def app_name(i: int) -> str:
    return f"stress-app-{i:03d}"


def app_markdown(app: str, endpoint: str = None) -> dict:
    ep = endpoint or f"GET /{app}/items"
    return {f"{app}_api.md": f"---\ntitle: \"{app} API\"\n---\n\n# {app} API\n\n{ep}\n"}


def _post_json(url: str, payload: dict, timeout: float = 120.0):
    """POST JSON; return (status_code, parsed_body_or_text)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        return e.code, body
    except Exception as e:  # connection refused, timeout, etc.
        return 0, f"{type(e).__name__}: {e}"


def _get_json(url: str, timeout: float = 60.0):
    """GET JSON; return (status_code, parsed_body_or_text)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _pct(values, p):
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))
    return ordered[idx]


# --------------------------------------------------------------------------
# push
# --------------------------------------------------------------------------
def cmd_push(args) -> int:
    base = args.base.rstrip("/")
    url = f"{base}/process"
    apps = [app_name(i) for i in range(args.n)]

    def submit(app):
        payload = {
            "markdowns": app_markdown(app),
            "timestamp": "2026-06-13T00:00:00",
            "trigger_info": {"source": "stress-test"},
            "source_app": app,
            "source_version": "v1.0.0",
        }
        t0 = time.time()
        status, body = _post_json(url, payload)
        wall_ms = int((time.time() - t0) * 1000)
        ok = status == 200 and isinstance(body, dict) and body.get("status") == "success"
        server_ms = body.get("processing_time_ms", 0) if isinstance(body, dict) else 0
        return app, ok, status, server_ms, wall_ms, body

    print(f"==> push: {args.n} apps -> {url} (workers={args.workers})")
    start = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(submit, a) for a in apps]
        for f in as_completed(futures):
            results.append(f.result())
    elapsed = time.time() - start

    ok_results = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    server_ms = [r[3] for r in ok_results]
    wall_ms = [r[4] for r in ok_results]

    print(f"\nsucceeded: {len(ok_results)}/{args.n}")
    print(f"elapsed:   {elapsed:.2f}s  ({args.n / elapsed:.1f} apps/sec)")
    print(
        "server processing_time_ms: "
        f"p50={_pct(server_ms,50)} p95={_pct(server_ms,95)} max={max(server_ms, default=0)}"
    )
    print(
        "client wall_ms:            "
        f"p50={_pct(wall_ms,50)} p95={_pct(wall_ms,95)} max={max(wall_ms, default=0)}"
    )
    if failed:
        print(f"\n!! {len(failed)} FAILED submissions (showing up to 10):")
        for app, _ok, status, _s, _w, body in failed[:10]:
            snippet = body if isinstance(body, str) else json.dumps(body)
            print(f"   {app}: HTTP {status} -> {str(snippet)[:200]}")
    print("\nPUSH RESULT:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


# --------------------------------------------------------------------------
# update-one (isolation test helper)
# --------------------------------------------------------------------------
def cmd_update_one(args) -> int:
    base = args.base.rstrip("/")
    app = args.app
    new_ep = args.endpoint
    payload = {
        "markdowns": app_markdown(app, endpoint=new_ep),
        "timestamp": "2026-06-13T01:00:00",
        "trigger_info": {"source": "stress-test-isolation"},
        "source_app": app,
        "source_version": "v2.0.0",
    }
    print(f"==> update-one: {app} -> {new_ep}")
    status, body = _post_json(f"{base}/process", payload)
    print(f"HTTP {status}")
    print(json.dumps(body, indent=2) if isinstance(body, dict) else body)
    ok = status == 200 and isinstance(body, dict) and body.get("status") == "success"
    print("\nUPDATE RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------
def cmd_verify(args) -> int:
    mcp = args.mcp.rstrip("/")
    proc = args.base.rstrip("/")
    n = args.n
    pg_on = args.pg == "on"
    checks = []  # (name, passed, detail)

    def record(name, passed, detail=""):
        checks.append((name, passed, detail))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    # 1. list_apis: module count + per-app exact endpoint (lost-update + isolation)
    status, info = _get_json(f"{mcp}/list_apis")
    if status != 200 or not isinstance(info, dict):
        record("list_apis reachable", False, f"HTTP {status}: {str(info)[:200]}")
        modules = {}
    else:
        modules = info.get("modules", {})
        record("list_apis module count == N", len(modules) == n, f"got {len(modules)}, want {n}")
        bad = []
        for i in range(n):
            a = app_name(i)
            want = [f"GET /{a}/items"]
            if modules.get(a) != want:
                bad.append((a, modules.get(a)))
        record(
            "every app present with exactly its endpoint (no lost update / isolation)",
            len(bad) == 0,
            "all good" if not bad else f"{len(bad)} wrong, e.g. {bad[:5]}",
        )

    # 2. wiki_info: totals + vector index
    status, wi = _get_json(f"{mcp}/wiki_info")
    if status == 200 and isinstance(wi, dict):
        record("wiki_info.modules == N", wi.get("modules") == n, f"got {wi.get('modules')}")
        record(
            "wiki_info.total_endpoints == N",
            wi.get("total_endpoints") == n,
            f"got {wi.get('total_endpoints')}",
        )
        vidx = wi.get("vector_index", {})
        if pg_on:
            record("vector_index.available == true", vidx.get("available") is True, str(vidx)[:160])
            record("vector_index.entries == N", vidx.get("entries") == n, f"got {vidx.get('entries')}")
            record("vector_index.embedded == N", vidx.get("embedded") == n, f"got {vidx.get('embedded')}")
        else:
            record("vector_index.available == false (PG off)", vidx.get("available") is False, str(vidx)[:160])
    else:
        record("wiki_info reachable", False, f"HTTP {status}: {str(wi)[:200]}")

    # 3. /status wiki_size == N
    status, st = _get_json(f"{proc}/status")
    if status == 200 and isinstance(st, dict):
        record("status.wiki_size == N", st.get("wiki_size") == n, f"got {st.get('wiki_size')}")
    else:
        record("status reachable", False, f"HTTP {status}: {str(st)[:200]}")

    # 4. get_api_detail on 3 samples
    samples = [app_name(0), app_name(n // 2), app_name(n - 1)]
    for a in samples:
        q = urllib.parse.urlencode({"module": a, "api_key": f"GET /{a}/items"})
        status, d = _get_json(f"{mcp}/get_api_detail?{q}")
        ok = (
            status == 200
            and isinstance(d, dict)
            and isinstance(d.get("detail"), dict)
            and d["detail"].get("path") == f"/{a}/items"
            and d["detail"].get("source_app") == a
        )
        record(f"get_api_detail {a}", ok, str(d)[:160])

    # 5. search_apis mode
    status, s = _get_json(f"{mcp}/search_apis?{urllib.parse.urlencode({'query': samples[1]})}")
    if status == 200 and isinstance(s, dict):
        want_mode = "pg_keyword" if pg_on else "wiki_scan"
        record(f"search_apis mode == {want_mode}", s.get("mode") == want_mode, f"got {s.get('mode')}, count={s.get('count')}")
    else:
        record("search_apis reachable", False, f"HTTP {status}: {str(s)[:200]}")

    # 6. semantic_search mode + finds the sampled app
    a = samples[1]
    q = urllib.parse.urlencode({"query": f"{a} items", "top_k": 3})
    status, sem = _get_json(f"{mcp}/semantic_search?{q}")
    if status == 200 and isinstance(sem, dict):
        want_mode = "semantic" if pg_on else "keyword_fallback"
        keys = [r.get("api_key") for r in sem.get("results", [])]
        record(f"semantic_search mode == {want_mode}", sem.get("mode") == want_mode, f"got {sem.get('mode')}")
        if pg_on:
            record(f"semantic_search finds {a}", f"GET /{a}/items" in keys, f"top={keys}")
    else:
        record("semantic_search reachable", False, f"HTTP {status}: {str(sem)[:200]}")

    passed = sum(1 for _n, p, _d in checks if p)
    print(f"\nVERIFY SUMMARY: {passed}/{len(checks)} checks passed")
    print("VERIFY RESULT:", "PASS" if passed == len(checks) else "FAIL")
    return 0 if passed == len(checks) else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("push", help="concurrently push N app READMEs")
    pp.add_argument("--n", type=int, default=150)
    pp.add_argument("--base", default=DEFAULT_PROCESSOR, help="wiki-processor base URL")
    pp.add_argument("--workers", type=int, default=50)
    pp.set_defaults(func=cmd_push)

    pv = sub.add_parser("verify", help="verify mcp-server results for N apps")
    pv.add_argument("--n", type=int, default=150)
    pv.add_argument("--mcp", default=DEFAULT_MCP, help="mcp-server base URL")
    pv.add_argument("--base", default=DEFAULT_PROCESSOR, help="wiki-processor base URL")
    pv.add_argument("--pg", choices=["on", "off"], default="on", help="is the PG index enabled?")
    pv.set_defaults(func=cmd_verify)

    pu = sub.add_parser("update-one", help="re-push one app with a new endpoint (isolation test)")
    pu.add_argument("--app", default="stress-app-005")
    pu.add_argument("--base", default=DEFAULT_PROCESSOR)
    pu.add_argument("--endpoint", default=None, help="defaults to POST /<app>/orders")
    pu.set_defaults(
        func=lambda a: cmd_update_one(
            argparse.Namespace(
                base=a.base, app=a.app, endpoint=a.endpoint or f"POST /{a.app}/orders"
            )
        )
    )

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
