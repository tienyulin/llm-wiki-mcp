#!/usr/bin/env python3
"""Contract test: flashback-api's README, when pushed to wiki-processor,
parses into the expected API entries — no services needed.

This guards the SOP→spec→API→README→wiki pipeline (the "GitLab CI push"
step simulated by examples/simulate-app-push.sh). It reproduces the
processor's mock-mode extraction regexes; SOURCE OF TRUTH is
wiki-processor/services/llm/base.py (_ENDPOINT_RE / _H1_RE / module
derivation) — keep these in sync if that file changes.
"""
import re
from pathlib import Path

# Mirror of wiki-processor/services/llm/base.py:12-13
_ENDPOINT_RE = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/[\w/{}.-]*)")
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

_README = Path(__file__).resolve().parents[2] / "flashback-api" / "README.md"

# Every endpoint flashback-api documents (spec Part B §2 / README endpoint table).
_EXPECTED_PATHS = {
    ("GET", "/health"),
    ("GET", "/flashback/status"),
    ("GET", "/restore_points"),
    ("POST", "/restore_points"),
    ("DELETE", "/restore_points/{name}"),
    ("GET", "/recyclebin"),
    ("POST", "/flashback/table"),
    ("POST", "/flashback/drop"),
    ("POST", "/flashback/database"),
    ("POST", "/flashback/database/finalize"),
    ("GET", "/audit/log"),
}


def _module_from_filename(filename: str) -> str:
    """Mirror of base.py module derivation."""
    module = filename.rsplit(".", 1)[0]
    for suffix in ("_api", "_arch", "-api"):
        module = module.removesuffix(suffix)
    return module


def test_readme_has_h1():
    content = _README.read_text(encoding="utf-8")
    assert _H1_RE.search(content), "README needs an H1 (becomes the wiki description)"


def test_readme_endpoints_extract_for_processor():
    content = _README.read_text(encoding="utf-8")
    found = set(_ENDPOINT_RE.findall(content))
    missing = _EXPECTED_PATHS - found
    assert not missing, f"processor would miss these endpoints from the README: {missing}"


def test_pushed_as_flashback_api_md_yields_module_flashback():
    # examples/simulate-app-push.sh sends README under key "flashback-api.md"
    assert _module_from_filename("flashback-api.md") == "flashback"
