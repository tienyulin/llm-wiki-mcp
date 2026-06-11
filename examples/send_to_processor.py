#!/usr/bin/env python3
"""
Collect markdown files and send to wiki-processor.
This script runs in GitLab CI to push documentation updates.

Usage:
    python3 send_to_processor.py

Environment variables:
    WIKI_PROCESSOR_URL - processor endpoint (default: http://wiki-processor:8001)
"""

import json
import glob
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Install with: pip install httpx")
    sys.exit(1)


def collect_markdowns(pattern: str = "markdowns/**/*.md") -> dict[str, str]:
    """Collect all markdown files matching pattern"""
    markdowns = {}

    files = sorted(glob.glob(pattern, recursive=True))

    if not files:
        print(f"⚠️  No markdown files found matching: {pattern}")
        return markdowns

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                markdowns[filepath] = f.read()
                print(f"  ✅ {filepath} ({len(markdowns[filepath])} bytes)")
        except Exception as e:
            print(f"  ❌ Failed to read {filepath}: {e}")
            return {}

    return markdowns


def create_payload(markdowns: dict) -> dict:
    """Create request payload for processor"""

    # Get GitLab CI variables if available
    repo = os.getenv("CI_PROJECT_PATH", "central-markdown-repo")
    branch = os.getenv("CI_COMMIT_BRANCH", "main")
    commit_sha = os.getenv("CI_COMMIT_SHA", "unknown")
    pipeline_url = os.getenv("CI_PIPELINE_URL", "")

    payload = {
        "markdowns": markdowns,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trigger_info": {
            "repo": repo,
            "branch": branch,
            "commit_sha": commit_sha,
            "pipeline_url": pipeline_url,
        }
    }

    return payload


async def send_to_processor(payload: dict, processor_url: str) -> bool:
    """Send payload to wiki-processor"""

    print(f"\n📤 Sending to processor: {processor_url}/process")
    print(f"   Markdowns: {len(payload['markdowns'])} files")
    print(f"   Timestamp: {payload['timestamp']}")

    headers = {}
    api_key = os.getenv("PROCESSOR_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{processor_url}/process",
                json=payload,
                headers=headers,
            )

            print(f"\n📥 Response: HTTP {response.status_code}")

            if response.status_code >= 200 and response.status_code < 300:
                result = response.json()
                print(f"   Status: {result.get('status')}")
                print(f"   Message: {result.get('message')}")

                if result.get('changes_summary'):
                    summary = result['changes_summary']
                    print(f"\n📊 Changes detected:")
                    if summary.get('added'):
                        print(f"   Added: {', '.join(summary['added'])}")
                    if summary.get('modified'):
                        print(f"   Modified: {', '.join(summary['modified'])}")
                    if summary.get('deleted'):
                        print(f"   Deleted: {', '.join(summary['deleted'])}")

                print(f"\n✅ Wiki updated successfully!")
                print(f"   Output: {result.get('wiki_url')}")
                return True
            else:
                print(f"   Error: {response.text}")
                return False

        except httpx.ConnectError as e:
            print(f"❌ Connection error: {e}")
            print(f"   Check if processor is running at: {processor_url}")
            return False
        except httpx.TimeoutError:
            print(f"❌ Timeout: Processor took too long to respond")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def main():
    """Main entry point"""

    print("=" * 70)
    print("Wiki Processor - Markdown Sender (GitLab CI)")
    print("=" * 70)

    # Get processor URL from environment or use default
    processor_url = os.getenv("WIKI_PROCESSOR_URL", "http://wiki-processor:8001")

    # Get markdown pattern from environment or use default
    pattern = os.getenv("MARKDOWN_PATTERN", "markdowns/**/*.md")

    # Step 1: Collect markdowns
    print(f"\n🔍 Collecting markdown files from: {pattern}")
    markdowns = collect_markdowns(pattern)

    if not markdowns:
        print("❌ No markdown files collected, aborting")
        sys.exit(1)

    print(f"\n✅ Collected {len(markdowns)} markdown files")

    # Step 2: Create payload
    print("\n📦 Creating payload...")
    payload = create_payload(markdowns)

    # Step 3: Send to processor
    print("\n🚀 Sending to processor...")
    success = await send_to_processor(payload, processor_url)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
