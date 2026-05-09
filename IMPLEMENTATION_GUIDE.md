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

## Core Principle: Knowledge Accumulation, Not Search

This is NOT a search-based system like typical RAG. Instead, you ACCUMULATE knowledge:

1. **First question:** Read relevant complete files (api/users.md, overview.md, workflows/auth.md)
2. **Build mental model:** Keep this context in your understanding
3. **Subsequent questions:** Answer based on accumulated context (no need to re-read)
4. **Grow understanding:** Follow [[wikilinks]] to deepen knowledge as needed

This way, the longer a conversation goes, the better you understand the entire system.

## How to Use the Wiki

### Step 1: Browse the Structure
list_directory("/")
→ See: api/, architecture/, workflows/, concepts/, guides/

### Step 2: Understand Project First
read_file("overview.md")
→ Understand what the system is about

### Step 3: Navigate by Interest
For API questions:
  list_directory("/api")
  read_file("api/users.md")
  → Read COMPLETE file, not snippets

### Step 4: Follow Wikilinks to Deepen
Within files you'll see [[links]] like [[Orders Module]] or [[Authentication Flow]]
→ Follow them to build complete understanding

### Key Principles

- **Read complete files:** Not snippets or summaries. Full context matters.
- **Build understanding:** First question takes longer (read multiple files), but context accumulates.
- **Follow wikilinks:** They guide you to related concepts and modules naturally.
- **Natural exploration:** Like browsing Wikipedia - you learn more as you follow links.
- **Reuse context:** In the same conversation, use previously read information rather than re-reading.

## Real Example: How Context Accumulation Works

User Q1: "How do I create a user?"
→ You read:
   - read_file("overview.md")           # Understand project
   - read_file("api/users.md")          # See POST /users endpoint
   - See [[Authentication Flow]] link
   - read_file("workflows/auth.md")     # Understand authentication
   Time: ~500ms (initial file reading)
   Context: Now you understand users, API, and authentication

User Q2: "How does authentication work?"
→ You answer based on already-read workflows/auth.md
   No need to re-read!
   Time: Fast (reuse context)
   Context: Already in your understanding

User Q3: "What about the Orders API?"
→ You already understand the system from Q1 and Q2
   read_file("api/orders.md")           # Only read new module
   You can compare orders/users similarities immediately
   Time: ~200ms (only read one new file)
   Context: Continues to grow

User Q4: "How do these systems interact?"
→ You can answer complex design questions because you've read:
   overview.md, api/users.md, api/orders.md, workflows/auth.md
   You see the big picture!

## Why This Approach

Traditional RAG (search-based):
- Every query: "find relevant chunks"
- Agent starts fresh each time
- Limited context understanding
- Good for isolated questions, bad for complex reasoning

Karpathy Wiki (accumulation-based):
- First query: "read relevant complete files"
- Subsequent queries: "use what you've learned"
- Rich context understanding
- Perfect for complex system design questions

Your job: Read complete files, build understanding, answer complex questions.
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
        "description": "Browse the wiki file structure. Start with '/' to see sections. Use this to explore what documentation exists.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path like '/', 'api/', 'architecture/', 'workflows/'. Default is '/'."
                }
            }
        }
    },
    {
        "name": "read_file",
        "description": "Read a markdown file's complete content. Files contain [[wikilinks]] to other docs. Read complete files to build context, not snippets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path like 'api/users.md', 'overview.md', 'architecture/system.md'. Always read complete files."
                }
            },
            "required": ["path"]
        }
    }
]
```

### Context Window Strategy

When Claude has 200K token context window, use it strategically:

```
For a typical conversation:

1. INITIALIZE (first question)
   - read_file("overview.md")          [~2KB, builds foundation]
   - read_file("api/users.md")         [~5KB, user API details]
   - read_file("workflows/auth.md")    [~4KB, authentication logic]
   Total: ~11KB of rich context in your understanding

2. SUBSEQUENT QUESTIONS
   - Based on already-read context     [~0KB new reads, instant]
   - Or follow [[wikilinks]] for new info [selective file reads]

3. GROW UNDERSTANDING
   - After 10-20 questions on different topics
   - You've read: overview, 3-4 API modules, 2-3 workflows, several concepts
   - Total: ~50KB of curated knowledge
   - You understand the ENTIRE SYSTEM

This is exponentially better than searching for snippets 20 times.
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

## Why This Design: Philosophical Foundation

### Not Search, Not RAG - It's Knowledge Base

The key insight from Karpathy:

> "A large fraction of my recent token throughput is going less into manipulating code, and more into manipulating information"

### The Problem with Traditional Search (RAG)

```
User Question
  ↓
Search for relevant chunks
  ↓
Find 3-5 snippets
  ↓
LLM rediscovers knowledge from zero
  ↓
Answer based on isolated chunks
  ↓
(Next question) Repeat the search
  ↓
No knowledge accumulation!
```

### The Karpathy Approach

```
User Question 1
  ↓
Read relevant COMPLETE files
  ↓
Build mental model (save in context)
  ↓
Answer from complete understanding
  ↓
User Question 2
  ↓
Use previous understanding + selective new reads
  ↓
Answer from RICHER context
  ↓
Knowledge ACCUMULATES!
```

### Why File Browsing, Not Search?

**Search-based problems:**
- Index maintenance overhead
- Token spent on search logic, not understanding
- Snippet-based answers lack full context
- Complex queries produce poor results

**Browsing-based benefits:**
- No index to maintain - just clean files
- Token spent on reading and reasoning
- Complete files provide rich context
- Complex queries answered from full understanding
- Conversation naturally deepens knowledge

### Performance Reality

**First question:** Takes ~500ms to read 3-4 relevant files (slower than indexed search)

**But in a 20-question conversation:**
- Question 1: 500ms (read files)
- Questions 2-20: Each uses context, answering complex questions from accumulated knowledge
- Total: Much more effective than 20 separate searches

**Key metric:** Not "latency per query" but "understanding depth and reasoning quality"

### Why No search_endpoints()?

Because:
1. **LLM can browse naturally** - Give it list_directory() and it explores
2. **Files are self-documenting** - No need for metadata indices
3. **Simplicity** - Fewer components, fewer bugs
4. **Better context** - LLM reads COMPLETE endpoint with parameters, examples, errors—not just metadata
5. **Follows Karpathy's principle** - Structure enables understanding, not fragmented search

---

## Summary

Key implementations:
1. **wiki-processor**: Generate structured wiki files from markdown
2. **mcp-server**: Provide file browsing and reading interface
3. **Both**: Clear prompts that teach LLMs how to use the system

No complex search, no indexing - just clean structure and simple tools.
