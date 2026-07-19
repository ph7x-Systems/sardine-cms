"""MySQL / MariaDB backend (ADR-0018).

Driver: PyMySQL — an optional dependency
(``pip install 'sardine-cms-core[mysql]'``). MariaDB speaks the same
protocol and dialect subset used here. The shared migration history applies
with two mechanical adaptations: key columns become bounded ``VARCHAR``s
(MySQL cannot index unbounded ``TEXT``) and the reserved ``key`` column is
backtick-quoted. Upserts use ``ON DUPLICATE KEY UPDATE`` in the
``VALUES()`` form, which both MySQL and MariaDB accept.
"""

from typing import Any
from urllib.parse import unquote, urlparse

from cms_core.storage.dbapi import DbApiBackend, rewrite_key_columns, split_statements

KEY_TYPE = "VARCHAR(255)"


def _connect_kwargs(location: str) -> dict[str, Any]:
    parsed = urlparse(f"//{location.lstrip('/')}" if "://" not in location else location)
    if not parsed.hostname or not parsed.path.lstrip("/"):
        raise ValueError("mysql URL must look like mysql://user:password@host[:port]/database")
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.lstrip("/"),
        "charset": "utf8mb4",
        "autocommit": False,
    }


class MySQLBackend(DbApiBackend):
    def __init__(self, location: str) -> None:
        self._kwargs = _connect_kwargs(location)
        super().__init__()

    def _connect(self) -> Any:
        try:
            import pymysql
        except ImportError as error:  # pragma: no cover - exercised without the extra
            raise ImportError(
                "the MySQL backend needs the optional dependency:"
                " pip install 'sardine-cms-core[mysql]'"
            ) from error
        return pymysql.connect(**self._kwargs)

    def _migration_statements(self, script: str) -> list[str]:
        import re

        statements = []
        for statement in split_statements(script):
            statement = rewrite_key_columns(statement, KEY_TYPE)
            statement = statement.replace(" key ", " `key` ")
            statement = statement.replace("(page_id, key)", "(page_id, `key`)")
            # MySQL refuses DEFAULT on TEXT columns: add, backfill, constrain.
            defaulted = re.fullmatch(
                r"ALTER TABLE (\w+) ADD COLUMN (\w+) TEXT NOT NULL DEFAULT '([^']*)'",
                statement.strip(),
            )
            if defaulted:
                table, column, default = defaulted.groups()
                statements.append(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
                statements.append(f"UPDATE {table} SET {column} = '{default}'")
                statements.append(f"ALTER TABLE {table} MODIFY {column} TEXT NOT NULL")
            else:
                statements.append(statement)
        return statements

    def _quoted_key_column(self) -> str:
        return "`key`"

    def _upsert(self, table: str, keys: dict[str, Any], values: dict[str, Any]) -> None:
        columns = list(keys) + list(values)
        placeholders = ", ".join(["%s"] * len(columns))
        updates = ", ".join(f"{column} = VALUES({column})" for column in values)
        self._execute(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            f" ON DUPLICATE KEY UPDATE {updates}",
            list(keys.values()) + list(values.values()),
        )
