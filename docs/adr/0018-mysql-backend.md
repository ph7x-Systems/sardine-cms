# ADR-0018 — MySQL / MariaDB storage backend

- **Status:** accepted
- **Date:** 2026-07-19

## Context

The release plan reserves the remaining engines in the ADR-0009 mold: an
ADR each, an optional dependency extra, the shared ANSI migration history
with engine-specific version tracking, and the storage conformance suite
green in CI against a real server.

## Decision

- **Driver: PyMySQL** (`pip install 'sardine-cms-core[mysql]'`) — pure
  Python, MIT, no client libraries to install; MariaDB is protocol- and
  dialect-compatible for the subset used, so `mariadb://` aliases to
  `mysql://`.
- URL form: `mysql://user:password@host[:port]/database`.
- The shared migrations apply with two mechanical dialect adaptations,
  performed at migrate time and covered by the conformance suite: key
  columns declared `TEXT` become `VARCHAR(255)` (MySQL cannot index
  unbounded text) and the reserved `key` column is backtick-quoted.
- Upserts use `INSERT … ON DUPLICATE KEY UPDATE` in the `VALUES()` form —
  accepted by both MySQL 8 and MariaDB (the newer alias form is not).
- Version tracking in a `schema_migrations` table, like PostgreSQL.
- The CRUD itself is the shared DB-API implementation
  (`cms_core.storage.dbapi`) also used by the SQL Server backend — one
  body of logic, three dialects, zero duplication.

## Consequences

- CI runs the conformance suite against a `mysql:8.4` service container
  (`SARDINE_MYSQL_URL`); locally any MySQL/MariaDB works the same way.
- `utf8mb4` is forced at connection time; content is stored as UTF-8.
