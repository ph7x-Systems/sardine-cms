"""Microsoft SQL Server backend (ADR-0019).

Driver: pymssql — an optional dependency
(``pip install 'sardine-cms-core[mssql]'``). The shared migration history
applies with mechanical adaptations: key columns become ``NVARCHAR(255)``
(indexable), other ``TEXT`` columns become ``NVARCHAR(MAX)`` (the T-SQL
``TEXT`` type is deprecated), and the reserved ``key`` column is
bracket-quoted. Upserts are an update-then-insert inside the transaction —
readable, and race-free for the single-writer admin.
"""

from typing import Any
from urllib.parse import unquote, urlparse

from cms_core.storage.dbapi import DbApiBackend, rewrite_key_columns, split_statements

KEY_TYPE = "NVARCHAR(255)"


def _connect_kwargs(location: str) -> dict[str, Any]:
    parsed = urlparse(f"//{location.lstrip('/')}" if "://" not in location else location)
    if not parsed.hostname or not parsed.path.lstrip("/"):
        raise ValueError("mssql URL must look like mssql://user:password@host[:port]/database")
    return {
        "server": parsed.hostname,
        "port": parsed.port or 1433,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.lstrip("/"),
    }


class MssqlBackend(DbApiBackend):
    def __init__(self, location: str) -> None:
        self._kwargs = _connect_kwargs(location)
        super().__init__()

    def _connect(self) -> Any:
        try:
            import pymssql
        except ImportError as error:  # pragma: no cover - exercised without the extra
            raise ImportError(
                "the SQL Server backend needs the optional dependency:"
                " pip install 'sardine-cms-core[mssql]'"
            ) from error
        return pymssql.connect(**self._kwargs)

    def _ensure_migrations_table(self) -> None:
        self._execute(
            "IF OBJECT_ID('schema_migrations', 'U') IS NULL"
            " CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY)"
        )

    def _migration_statements(self, script: str) -> list[str]:
        statements = []
        for statement in split_statements(script):
            statement = rewrite_key_columns(statement, KEY_TYPE)
            statement = statement.replace(" TEXT", " NVARCHAR(MAX)")
            statement = statement.replace("ADD COLUMN ", "ADD ")
            statement = statement.replace(" key ", " [key] ")
            statement = statement.replace("(page_id, key)", "(page_id, [key])")
            statements.append(statement)
        return statements

    def _quoted_key_column(self) -> str:
        return "[key]"

    def _upsert(self, table: str, keys: dict[str, Any], values: dict[str, Any]) -> None:
        where = " AND ".join(f"{column} = %s" for column in keys)
        updates = ", ".join(f"{column} = %s" for column in values)
        cursor = self._execute(
            f"UPDATE {table} SET {updates} WHERE {where}",
            list(values.values()) + list(keys.values()),
        )
        if cursor.rowcount == 0:
            columns = list(keys) + list(values)
            placeholders = ", ".join(["%s"] * len(columns))
            self._execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                list(keys.values()) + list(values.values()),
            )
