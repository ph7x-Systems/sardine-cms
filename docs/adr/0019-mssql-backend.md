# ADR-0019 — Microsoft SQL Server storage backend

- **Status:** accepted
- **Date:** 2026-07-19

## Context

Same mold as ADR-0009 and ADR-0018: the last planned engine, as an optional
extra with the shared migration history and the conformance suite against a
real server in CI.

## Decision

- **Driver: pymssql** (`pip install 'sardine-cms-core[mssql]'`) — wheels
  with FreeTDS bundled, no ODBC driver installation required, which keeps
  local setup and CI to a plain `pip install`.
- URL form: `mssql://user:password@host[:port]/database` (alias
  `sqlserver://`).
- The shared migrations apply with mechanical dialect adaptations at
  migrate time: key columns become `NVARCHAR(255)` (indexable), remaining
  `TEXT` columns become `NVARCHAR(MAX)` (T-SQL's `TEXT` type is
  deprecated), and the reserved `key` column is bracket-quoted.
- Upserts are an update-then-insert inside the write transaction — simple,
  readable, and race-free for the single-writer admin process.
- Version tracking in a `schema_migrations` table; CRUD comes from the
  shared DB-API implementation (`cms_core.storage.dbapi`).

## Consequences

- CI runs the conformance suite against the
  `mcr.microsoft.com/mssql/server:2022-latest` container
  (`SARDINE_MSSQL_URL`); the suite creates the database if missing.
- With this, every engine promised in ADR-0004's factory is implemented:
  SQLite, PostgreSQL, MySQL/MariaDB and SQL Server, one contract, one
  conformance suite.
