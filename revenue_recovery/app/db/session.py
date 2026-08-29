from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import psycopg


class DatabaseConnection(Protocol):
    """A minimal database connection interface."""

    def execute(self, query: str, params: tuple | dict | None = None) -> None:
        ...

    def fetchone(self, query: str, params: tuple | dict | None = None) -> dict | None:
        ...

    def fetchall(self, query: str, params: tuple | dict | None = None) -> list[dict]:
        ...


@dataclass
class PostgresConnection:
    """Wraps a psycopg connection with a small typed interface."""

    _conn: psycopg.Connection

    def execute(self, query: str, params: tuple | dict | None = None) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute(query, params)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def fetchone(self, query: str, params: tuple | dict | None = None) -> dict | None:
        try:
            with self._conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception:
            self._conn.rollback()
            raise

    def fetchall(self, query: str, params: tuple | dict | None = None) -> list[dict]:
        try:
            with self._conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception:
            self._conn.rollback()
            raise


def get_database_url() -> str:
    """Build the DATABASE_URL from environment variables.

    Supports either a direct DATABASE_URL or individual PG* variables.
    """
    direct = os.environ.get("DATABASE_URL")
    if direct:
        return direct

    user = os.environ.get("PGUSER", "recovery")
    password = os.environ.get("PGPASSWORD", "recovery_dev_password")
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ.get("PGDATABASE", "recovery_engine")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def create_connection() -> PostgresConnection:
    """Create a new PostgreSQL connection."""
    url = get_database_url()
    conn = psycopg.connect(url, autocommit=False)
    return PostgresConnection(_conn=conn)
