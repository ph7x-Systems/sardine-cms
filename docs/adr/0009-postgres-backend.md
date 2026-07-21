# ADR-0009 — PostgreSQL backend on psycopg 3, shared migration history

- **Status:** accepted
- **Date:** 2026-07-17

> Identifiers in this record predate the Stillsite → Sardine CMS rename
> ([ADR-0016](0016-rename-sardine-cms.md)): read `stillsite*` names as their
> `sardine*` successors.


## Context

ADR-0004 left the server engines behind the storage factory as planned.
PostgreSQL is the production target and closes Milestone 1's remaining item.
The open sub-decision was whether server backends would share a layer such as
SQLAlchemy.

## Decision

- **Driver, not ORM**: the backend talks to PostgreSQL directly through
  **psycopg 3**, mirroring the SQLite backend's shape. Two engines did not
  justify an ORM's weight; revisit only if a third SQL backend shows real
  duplication pain (SQL Server is the test).
- **Optional dependency**: `pip install cms-core[postgres]` — the core stays
  dependency-minimal; the factory raises a helpful error if the extra is
  missing.
- **One migration history**: the ordered scripts moved to
  `storage/migrations.py` and are ANSI SQL shared by both engines. SQLite
  tracks the applied version in `user_version`; PostgreSQL in a
  `schema_migrations` table. New migrations are written once.
- **Conformance, not new tests**: `tests/test_storage.py` is parameterized
  over engines via the `backend` fixture — SQLite always, PostgreSQL when
  `STILLSITE_POSTGRES_URL` is set. CI runs it against a PostgreSQL 16 service
  container (required check); locally it runs against the project-prefixed
  Docker container `ph7x-cms-postgres`.

## Consequences

- Milestone 1 is closed: `create_storage("postgresql://…")` is a working
  production path, switchable from SQLite by configuration alone.
- The conformance suite proved the contract: the backend passed it unchanged.
- SQL Server and MySQL/MariaDB follow the same mold (shared migrations,
  engine-specific version tracking, conformance suite as the gate).
