# Architecture diagrams

Cross-service views of the platform. Per-service internals live in each repo's
`docs/architecture/`.

## System overview

```mermaid
flowchart LR
    apps["100+ apps<br/>(CI: ci-templates)"] -->|"POST /process"| WP[wiki-processor :8001]

    subgraph infra["shared infra (llm-wiki-net)"]
        MinIO[("MinIO<br/>wiki.json<br/>source of truth")]
        PG[("Postgres + pgvector<br/>derived index")]
    end

    WP -->|"CAS write"| MinIO
    WP -.->|"best-effort sync"| PG
    WP -.->|"POST /cache/invalidate"| MCP

    MCP[mcp-server :8002] -->|"PG-first"| PG
    MCP -->|"fallback / concepts / overviews"| MinIO
    MCP --> Claude["Claude / LLM"]
```

## Ingest pipeline (`/process`, two-step + CAS)

```mermaid
flowchart TD
    A["markdown in"] --> B{first run?}
    B -->|yes| C["generate_wiki"]
    B -->|no| D["update_wiki<br/>(this app only)"]

    subgraph llm["LLM two-step (real path)"]
        S1["step 1: analyze<br/>endpoints, modules,<br/>contradictions, source file"]
        S2["step 2: generate JSON<br/>+ sources[] per entry"]
        S1 --> S2
    end
    C --> S1
    D --> S1

    S2 --> ST["_stamp<br/>source_app / source_version"]
    ST --> OV["generate_overview(app)"]
    OV --> CAS{"CAS loop<br/>If-Match ETag"}
    CAS -->|conflict| RE["re-read + remerge"] --> CAS
    CAS -->|ok| W[("wiki.json<br/>apis + overviews")]
    W -.->|best-effort| PGsync[("PG index<br/>incl. sources in detail")]
```

Concepts are **not** built here — they're synthesized whole-wiki via
`POST /admin/rebuild-concepts`, not per-push (a per-push full-wiki LLM scan +
shared-blob write would mean cost + CAS contention on every app submission).

## Query + admin surfaces

```mermaid
flowchart LR
    subgraph wp["wiki-processor admin"]
        RC["POST /admin/recompile<br/>re-extract from snapshots"]
        RB["POST /admin/rebuild-concepts<br/>whole-wiki synthesis"]
        RI["POST /admin/reindex<br/>rebuild PG"]
    end

    subgraph mcp["mcp-server reads"]
        Q1["/list_apis · /search_apis<br/>/semantic_search · /get_api_detail"]
        Q2["/list_concepts · /get_concept"]
        Q3["/get_overview"]
        Q4["/skill → SKILL.md folder"]
        Q5["/graph → nodes + edges"]
    end

    W[("wiki.json")]
    PG[("PG index")]
    RB --> W
    RC --> W
    RI --> PG
    Q1 --> PG
    Q1 -.fallback.-> W
    Q2 --> W
    Q3 --> W
    Q4 --> W
    Q5 --> W
```

## wiki.json data model

```mermaid
erDiagram
    WIKI ||--o{ MODULE : apis
    WIKI ||--o{ CONCEPT : concepts
    WIKI ||--o{ OVERVIEW : overviews
    MODULE ||--o{ ENTRY : "api_key"
    CONCEPT }o--o{ ENTRY : "related (module::api_key)"

    WIKI {
        int schema_version
        object metadata
    }
    ENTRY {
        string method
        string path
        string description
        array sources "provenance: markdown files"
        string source_app "stamped by processor"
        string source_version
    }
    CONCEPT {
        string description
        array related "endpoints"
        array apps "cross-app"
    }
    OVERVIEW {
        string text
        string updated_at
    }
```

Graph edges (`GET /graph`): `shared_source` weight 4.0 (entries sharing a source
file), `concept` weight 3.0 (concept→entry). Adamic-Adar / Louvain communities
are a marked upgrade path.

## Run modes

```mermaid
flowchart TB
    subgraph A["Mode A — full stack (one compose)"]
        CA["docker compose up"] --> IA[("bundled minio + pg")]
        CA --> SA["all services"]
    end
    subgraph B["Mode B — independent services (shared infra)"]
        DB["scripts/dev-up.sh"] --> IB[("infra/ submodule:<br/>shared minio + pg<br/>on llm-wiki-net")]
        DB --> SB["each service own compose"]
        SB --> IB
    end
```
Run one mode at a time — both bind host ports 9000/9001/5432.
