# db/ — Postgres + pgvector serving index

Postgres is a **derived, rebuildable index** over MinIO's `wiki.json` (the
single source of truth). If PG state is ever wrong or lost: wipe it and call
`POST /admin/reindex` on wiki-processor.

## Layout

- `Dockerfile` — bitnami repmgr base image with the pgvector extension
  compiled in. Used by the `pg-0`/`pg-1`/`pg-2` services in
  `docker-compose.yml` (profile `pg`).
- `init/01-extension.sql` — `CREATE EXTENSION vector`, run as superuser on
  the primary's first boot.

## Where is the table DDL?

In code: `wiki-processor/storage/pg_store.py` → `PGVectorStore.ensure_schema()`.
It is idempotent and runs on startup/first use, so the schema works against
**any** PG with pgvector installed (the test suite uses a plain
`pgvector/pgvector:pg16` container). Keeping one executable copy avoids
SQL-file/code drift; this directory only handles what requires superuser or
image-level work.

## Topology

1 primary (`pg-0`) + 2 standbys (`pg-1`, `pg-2`) with repmgr automatic
failover. Clients use a multi-host DSN and let libpq find the writable node:

```
postgresql://wiki:wikipass@pg-0:5432,pg-1:5432,pg-2:5432/wiki?target_session_attrs=read-write
```

See `docs/architecture/vector-search.md` for the full design and failure
semantics.
