-- Runs as superuser on first boot of the PRIMARY node only (pg-0): bitnami
-- repmgr standbys clone the data dir via pg_basebackup and inherit this.
-- Table DDL is NOT here — wiki-processor's PGVectorStore.ensure_schema()
-- owns it (single source, works against any PG that has pgvector installed).
CREATE EXTENSION IF NOT EXISTS vector;
