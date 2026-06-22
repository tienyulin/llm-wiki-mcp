# db/ — Postgres + pgvector 服務索引

Postgres 是 MinIO `wiki.json`（唯一真相來源）之上的**衍生、可重建索引**。
若 PG 狀態錯了或遺失：清掉它，對 wiki-processor 呼叫 `POST /admin/reindex`。

> 名詞：**衍生索引** = 從真相來源算出來、壞了可重建的副本；**pgvector** = Postgres 向量擴充；
> **pg_trgm** = Postgres 的 trigram 擴充，讓 `ILIKE '%詞%'` 走索引（關鍵字搜尋）。

## 結構

- `init/01-extension.sql` —— `CREATE EXTENSION vector / pg_trgm`，在資料庫第一次啟動時
  以 superuser 身分執行（掛進 compose `pg` 服務的 `/docker-entrypoint-initdb.d`）。

## 表的 DDL 在哪？

在程式碼裡：`wiki-processor/repository/pg_store.py` → `PGVectorStore.ensure_schema()`。
它是 idempotent（可重複執行），啟動/首次使用時跑，所以對**任何**裝了 pgvector + pg_trgm
的 PG 都成立。只留一份可執行的 schema 避免 SQL 檔與程式碼漂移；本目錄只處理 bootstrap 時
需要 superuser 的部分。

## 拓撲

compose profile `pg` 後面一個 `pgvector/pgvector:pg16` 實例：

```
PG_DSN='postgresql://wiki:wikipass@pg:5432/wiki' docker compose --profile pg up -d
```

索引可選且可重建，所以單實例的耐久性可接受：PG 掛了，讀取自動退回 wiki.json 路徑，
事後 `POST /admin/reindex` 還原索引。

**之後要擴展：** client 程式（psycopg3）已支援多主機 failover DSN（`host=a,b,c` +
`target_session_attrs=read-write`，由 `test_pg_store.py::test_multihost_dsn_skips_dead_host`
覆蓋），所以改成 HA 叢集（repmgr、Patroni、CloudNativePG，或託管 PG）只動 docker-compose.yml
與 `PG_DSN`，不改應用程式。

完整設計與失敗語意見 `docs/architecture/vector-search.md`。
</content>
