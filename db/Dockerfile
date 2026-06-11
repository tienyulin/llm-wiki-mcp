# Postgres + repmgr + pgvector, used by pg-0/pg-1/pg-2 in docker-compose.yml.
#
# Base: Broadcom froze Bitnami's free Docker Hub catalog into bitnamilegacy/
# (no further updates, Aug 2025). The app layer only requires "any PG with
# pgvector + a multi-host read-write DSN", so swapping the HA base later
# (Patroni, CloudNativePG, managed PG) touches only this file and compose.
ARG BASE_IMAGE=bitnamilegacy/postgresql-repmgr:16
ARG PGVECTOR_VERSION=v0.8.0

FROM ${BASE_IMAGE} AS builder
ARG PGVECTOR_VERSION
USER root
# Compile pgvector against the Bitnami postgres (its pg_config drives all
# install paths under /opt/bitnami/postgresql).
RUN install_packages build-essential git ca-certificates && \
    git clone --depth 1 --branch ${PGVECTOR_VERSION} \
        https://github.com/pgvector/pgvector.git /tmp/pgvector && \
    cd /tmp/pgvector && \
    make PG_CONFIG=/opt/bitnami/postgresql/bin/pg_config && \
    make install PG_CONFIG=/opt/bitnami/postgresql/bin/pg_config

FROM ${BASE_IMAGE}
COPY --from=builder /opt/bitnami/postgresql/lib/vector.so /opt/bitnami/postgresql/lib/
COPY --from=builder /opt/bitnami/postgresql/share/extension/vector* /opt/bitnami/postgresql/share/extension/
