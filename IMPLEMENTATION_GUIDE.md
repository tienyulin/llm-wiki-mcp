# LLM Wiki MCP - Implementation Guide

**Target Audience:** AI models implementing the wiki system
**Language:** English
**Status:** Ready for Implementation

---

## Overview

This document provides step-by-step implementation instructions for the Karpathy-style Wiki MCP system.

### Key Concept

Instead of building a search-based system, we're building a **file browsing system** that lets LLMs naturally explore a well-structured wiki. The core is simplicity:

- **Write side:** LLM generates well-structured Markdown files with clear frontmatter and wikilinks
- **Read side:** LLM browses files via `list_directory()` and `read_file()` tools
- **No search complexity:** Just clean file structure

---

## Part 1: Wiki Generation Prompt (wiki-processor)

### System Message for LLM

Use this prompt when calling LLM to generate wiki files:

```python
WIKI_GENERATION_SYSTEM_PROMPT = """You are generating a Karpathy-style wiki structure from markdown documentation.

## Output Structure

Generate markdown files organized in this directory structure:

```
overview.md              # Project overview (required)
llms.txt               # Index and usage guide (required)
api/
  ├── users.md         # Each module in separate file
  ├── orders.md
  └── inventory.md
architecture/
  ├── system.md
  └── data-flow.md
workflows/
  ├── generation.md
  └── incremental-update.md
concepts/
  ├── karpathy-wiki.md
  └── snapshot.md
guides/
  └── extending-api.md
```

## Every File: YAML Frontmatter

Every markdown file MUST start with YAML frontmatter. Example:

```yaml
---
title: "Users API Module"
type: "api_module"           # Must be one of: api_module, concept, workflow, guide, architecture, overview
module: "users"              # Required for api_module only
description: "User management and authentication APIs"

# For API modules only - list all endpoints
endpoints:
  - method: "GET"
    path: "/users"
    summary: "List all users"
    tags: ["list", "users", "public"]
  - method: "POST"
    path: "/users"
    summary: "Create a new user"
    tags: ["create", "users"]

# For all files - cross-references
related:
  - "api/orders.md"
  - "workflows/authentication.md"
  - "concepts/user-model.md"

tags: ["api", "users"]
last_updated: "2025-02-15T10:30:00Z"
---
```

## Content Format

After frontmatter, use standard Markdown. Key rules:

### 1. Wikilinks for Cross-References

Use `[[filename without .md]]` format:

```markdown
# Users Module

This module is used by [[Orders Module]] and [[Inventory Module]].

For authentication flow, see [[Authentication Workflow]].

Related concept: [[User Data Model]]
```

**Important:** Link to actual files that exist.

### 2. Self-Contained Sections

Each file should have clear sections with examples and details.

### 3. Consistent Tags

Use standard tags (lowercase, hyphenated):
- Operations: create, read, list, update, delete, search
- Domains: users, orders, inventory
- Properties: public, internal, deprecated

## Generation Rules

### Rule 1: Separate Files by Concern
- Wrong: All APIs in one file
- Right: api/users.md, api/orders.md, api/inventory.md

### Rule 2: Consistent Frontmatter
Every file must have: title, type, description, related, last_updated

### Rule 3: Valid Wikilinks
Use [[Name]] format and ensure referenced files exist

### Rule 4: Hierarchical Organization
Group by semantic type: api/, architecture/, workflows/, concepts/, guides/

### Rule 5: Output Format

Return files using this exact format:

```
=== FILE: overview.md ===
---
title: "Project Name"
type: "overview"
description: "Project description"
tags: ["overview"]
last_updated: "2025-02-15T10:30:00Z"
---

# Project Name

Content here...

=== END FILE ===

=== FILE: api/users.md ===
---
title: "Users API Module"
type: "api_module"
...
---

Content here...

=== END FILE ===
```

## Validation Checklist

- [ ] Every file has complete frontmatter
- [ ] All wikilinks use [[ ]] format
- [ ] No dead links
- [ ] api_module files have module and endpoints
- [ ] Consistent file organization
- [ ] Markdown is well-formatted
- [ ] Tags are lowercase and hyphenated
- [ ] last_updated is current date
"""
```

### Usage in Code

```python
# In wiki-processor/services/llm.py

async def generate_wiki(self, markdowns: dict) -> dict[str, str]:
    """Generate wiki file structure from markdown collection."""
    input_markdown = self._format_markdowns(markdowns)
    
    prompt = f"""{WIKI_GENERATION_SYSTEM_PROMPT}

## Input Documentation

{input_markdown}

## Your Task

1. Analyze the input markdown
2. Generate well-organized wiki files
3. Each file must have complete YAML frontmatter
4. Use wikilinks to connect related files
5. Follow all generation rules above

Generate Now - provide all files using === FILE === format.
"""

    response = await self._call_llm(prompt, temperature=0.3)
    files = self._parse_multifile_output(response)
    self._validate_wiki_structure(files)
    return files
```

---

## Part 2: Wiki Reading System (mcp-server)

### System Message for Claude

```python
WIKI_SYSTEM_PROMPT = """You have access to a Karpathy-style wiki knowledge base.

## How to Use the Wiki

This is NOT a search-based system. Instead, BROWSE and EXPLORE:

### Step 1: Browse the Structure
list_directory("/")
→ See: api/, architecture/, workflows/, concepts/, guides/

### Step 2: Navigate by Interest
For API questions:
  list_directory("/api")
  read_file("api/users.md")

### Step 3: Follow Wikilinks
Within files you'll see [[links]] - follow them for related content.

### Key Principles
- Browse first, understand structure
- Read complete files, not snippets
- Follow [[wikilinks]] to build context
- Natural exploration like browsing Wikipedia
"""
```

### Implementation

```python
# In mcp-server/services/wiki_service.py

class WikiService:
    def __init__(self, minio_client):
        self.minio = minio_client
    
    def list_directory(self, path: str = "/") -> list[dict]:
        """List files and folders in directory."""
        if path == "/":
            path = ""
        
        items = []
        listed = self.minio.list_files(path)
        
        for item in listed:
            if item.endswith("/"):
                name = item.rstrip("/").split("/")[-1]
                items.append({"type": "directory", "name": name, "path": item})
            else:
                name = item.split("/")[-1]
                items.append({"type": "file", "name": name, "path": item})
        
        return items
    
    def read_file(self, path: str) -> str:
        """Read complete file content from Minio."""
        content = self.minio.get_file(path)
        if content is None:
            raise FileNotFoundError(f"File not found: {path}")
        return content
    
    def parse_frontmatter(self, markdown: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown."""
        import yaml
        
        if not markdown.startswith("---"):
            return {}, markdown
        
        end_idx = markdown.find("---", 3)
        if end_idx == -1:
            return {}, markdown
        
        frontmatter_str = markdown[3:end_idx].strip()
        body = markdown[end_idx + 3:].strip()
        
        try:
            frontmatter = yaml.safe_load(frontmatter_str)
            return frontmatter or {}, body
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
```

### Tool Schema for Claude

```python
TOOLS_SCHEMA = [
    {
        "name": "list_directory",
        "description": "Browse the wiki file structure. Start with '/' to see sections.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path like '/', 'api/', 'architecture/'"
                }
            }
        }
    },
    {
        "name": "read_file",
        "description": "Read a markdown file. Files contain [[wikilinks]] to other docs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path like 'api/users.md', 'overview.md'"
                }
            },
            "required": ["path"]
        }
    }
]
```

---

## Part 3: Methods to Implement

### wiki-processor/services/llm.py

```python
async def generate_wiki(self, markdowns: dict) -> dict[str, str]:
    """Generate wiki files from markdown collection."""
    # Call LLM with WIKI_GENERATION_SYSTEM_PROMPT
    # Parse multifile output
    # Validate structure
    # Return {path: content}

def _parse_multifile_output(self, response: str) -> dict[str, str]:
    """Parse === FILE: xxx === format."""
    # Regex: === FILE: (.*?) ===(.*)=== END FILE ===
    # Return dict of {filename: content}

def _validate_wiki_structure(self, files: dict[str, str]) -> None:
    """Validate wiki structure."""
    # Check required files exist (overview.md, llms.txt)
    # Check all files have valid frontmatter
    # Check wikilinks are correct
    # Raise ValueError if invalid

async def update_wiki(self, current_files: dict[str, str], 
                      changed_markdowns: dict, changes: dict) -> dict[str, str]:
    """Incremental update - only modify changed files."""
    # Similar to generate_wiki but preserve unchanged files
```

### mcp-server/services/wiki_service.py

```python
def list_directory(self, path: str = "/") -> list[dict]:
    """List directory contents."""

def read_file(self, path: str) -> str:
    """Read file content."""

def parse_frontmatter(self, markdown: str) -> tuple[dict, str]:
    """Parse frontmatter and body."""
```

### mcp-server/http_api/main.py

```python
@app.get("/tools")
def get_tools():
    return TOOLS_SCHEMA

@app.post("/tools/{tool_name}")
def handle_tool_call(tool_name: str, params: dict):
    if tool_name == "list_directory":
        return wiki_service.list_directory(params.get("path", "/"))
    elif tool_name == "read_file":
        return wiki_service.read_file(params.get("path"))
```

---

## Summary

Key implementations:
1. **wiki-processor**: Generate structured wiki files from markdown
2. **mcp-server**: Provide file browsing and reading interface
3. **Both**: Clear prompts that teach LLMs how to use the system

No complex search, no indexing - just clean structure and simple tools.
