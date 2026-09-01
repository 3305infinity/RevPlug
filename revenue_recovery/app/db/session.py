import os
from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg_pool import ConnectionPool


class DatabaseConnection(Protocol):
    """A minimal database connection interface."""

    def execute(self, query: str, params: tuple | dict | None = None) -> None:
        ...

    def fetchone(self, query: str, params: tuple | dict | None = None) -> dict | None:
        ...

    def fetchall(self, query: str, params: tuple | dict | None = None) -> list[dict]:
        ...


def get_database_url() -> str:
    """Build the DATABASE_URL from environment variables."""
    direct = os.environ.get("DATABASE_URL")
    if direct:
        return direct

    user = os.environ.get("PGUSER") or os.environ.get("POSTGRES_USER", "recovery")
    password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD", "recovery_dev_password")
    host = os.environ.get("PGHOST") or os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("PGPORT") or os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("PGDATABASE") or os.environ.get("POSTGRES_DB", "recovery_engine")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


# Global connection pool instance
_global_pool: ConnectionPool | None = None

def init_pool() -> None:
    """Initialize the global PostgreSQL connection pool with automatic health checks."""
    global _global_pool
    if _global_pool is None:
        url = get_database_url()
        _global_pool = ConnectionPool(
            url,
            min_size=2,
            max_size=10,
            kwargs={"autocommit": False},
            check=ConnectionPool.check_connection,
        )

def close_pool() -> None:
    """Close the global PostgreSQL connection pool."""
    global _global_pool
    if _global_pool is not None:
        _global_pool.close()
        _global_pool = None

def get_pool() -> ConnectionPool:
    """Get the global connection pool, initializing it if necessary."""
    global _global_pool
    if _global_pool is None:
        init_pool()
    return _global_pool


@dataclass
class PostgresConnection:
    """Uses the global psycopg_pool to execute queries.
    
    In a real system, you might pass a pool instance, but this preserves
    the current repository signatures that expect a `conn`.
    """

    def execute(self, query: str, params: tuple | dict | None = None) -> None:
        pool = get_pool()
        with pool.connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def fetchone(self, query: str, params: tuple | dict | None = None) -> dict | None:
        pool = get_pool()
        with pool.connection() as conn:
            try:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute(query, params)
                    row = cur.fetchone()
                conn.commit()
                return dict(row) if row else None
            except Exception:
                conn.rollback()
                raise

    def fetchall(self, query: str, params: tuple | dict | None = None) -> list[dict]:
        pool = get_pool()
        with pool.connection() as conn:
            try:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute(query, params)
                    rows = [dict(row) for row in cur.fetchall()]
                conn.commit()
                return rows
            except Exception:
                conn.rollback()
                raise


def create_connection() -> PostgresConnection:
    """Create a PostgresConnection wrapper (uses global pool internally)."""
    return PostgresConnection()
