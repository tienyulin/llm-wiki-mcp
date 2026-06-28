#!/usr/bin/env python3
"""Processor contract shapes — request, change detection, wiki, response.

Pure stdlib structure checks (no services). These used to build a dict and
`return` it without asserting, so they passed without testing anything; they
now assert the shapes they describe.
"""

import json
from datetime import datetime, timezone


def test_request_structure():
    """A /process request payload has the required fields in the right shapes."""
    payload = {
        "markdowns": {
            "api-users.md": "## GET /users/{id}\nReturn user by ID",
            "api-orders.md": "## POST /orders\nCreate new order",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trigger_info": {
            "repo": "central-markdown-repo",
            "branch": "main",
            "commit_sha": "abc123",
            "pipeline_url": "https://gitlab.com/...",
        },
    }
    assert set(payload) >= {"markdowns", "timestamp", "trigger_info"}
    assert isinstance(payload["markdowns"], dict) and len(payload["markdowns"]) == 2
    assert all(isinstance(v, str) and v for v in payload["markdowns"].values())
    # timestamp must be ISO-8601 parseable
    datetime.fromisoformat(payload["timestamp"])
    assert payload["trigger_info"]["repo"] == "central-markdown-repo"
    # round-trips as JSON (it crosses an HTTP boundary)
    assert json.loads(json.dumps(payload)) == payload


def test_change_detection():
    """Added / modified / deleted are derived from snapshot vs new markdowns."""
    old_snapshot = {
        "api-users.md": "old content",
        "api-orders.md": "order content",
        "api-old.md": "deprecated",
    }
    new_markdowns = {
        "api-users.md": "updated content",  # modified
        "api-orders.md": "order content",  # unchanged
        "api-products.md": "new content",  # added
        # api-old.md deleted
    }
    old_files = set(old_snapshot)
    new_files = set(new_markdowns)
    added = new_files - old_files
    deleted = old_files - new_files
    modified = {f for f in old_files & new_files if old_snapshot[f] != new_markdowns[f]}
    changes = {
        "added": sorted(added),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
    }
    assert changes["added"] == ["api-products.md"]
    assert changes["modified"] == ["api-users.md"]
    assert changes["deleted"] == ["api-old.md"]


def test_wiki_structure():
    """A wiki object nests modules -> endpoint key -> detail under `apis`."""
    wiki = {
        "apis": {
            "users": {
                "GET /users/{id}": {
                    "description": "Get user by ID",
                    "method": "GET",
                    "path": "/users/{id}",
                    "parameters": {"id": {"type": "string", "required": True}},
                }
            },
            "orders": {
                "POST /orders": {
                    "description": "Create new order",
                    "method": "POST",
                    "path": "/orders",
                    "body": {"type": "object"},
                }
            },
        },
        "metadata": {"version": "1.0", "updated_at": "2026-05-08T10:05:00Z"},
    }
    assert set(wiki["apis"]) == {"users", "orders"}
    assert sum(len(m) for m in wiki["apis"].values()) == 2
    detail = wiki["apis"]["users"]["GET /users/{id}"]
    assert detail["method"] == "GET" and detail["path"] == "/users/{id}"
    assert detail["description"]
    assert wiki["metadata"]["version"] == "1.0"


def test_response_structure():
    """A /process response carries status + a three-bucket changes summary."""
    response = {
        "status": "success",
        "message": "Wiki generated successfully",
        "wiki_url": "minio://wiki-data/wiki.json",
        "changes_summary": {"added": ["api-users.md"], "modified": [], "deleted": []},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    assert response["status"] in ("success", "partial", "failed")
    assert set(response["changes_summary"]) == {"added", "modified", "deleted"}
    assert response["changes_summary"]["added"] == ["api-users.md"]
    datetime.fromisoformat(response["timestamp"])


if __name__ == "__main__":
    test_request_structure()
    test_change_detection()
    test_wiki_structure()
    test_response_structure()
    print("✅ All processor contract checks passed")
