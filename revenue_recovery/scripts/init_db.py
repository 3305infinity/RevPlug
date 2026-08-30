"""Initialize the database schema by running all migrations in order."""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from app.db.session import get_database_url


def main() -> int:
    url = get_database_url()
    safe_url = url
    if "@" in url:
        prefix, rest = url.split("://", 1)
        if "@" in rest:
            creds, host = rest.split("@", 1)
            if ":" in creds:
                user, _ = creds.split(":", 1)
                safe_url = f"{prefix}://{user}:***@{host}"

    print(f"Initializing database: {safe_url}")

    migrations_dir = Path(__file__).parent.parent / "db" / "migrations"
    if not migrations_dir.exists():
        print(f"Migrations directory not found: {migrations_dir}")
        return 1

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        print("No migration files found.")
        return 1

    try:
        conn = psycopg.connect(url, autocommit=True, connect_timeout=5, options="-c lock_timeout=5000")
        conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state = 'idle in transaction'")
    except Exception as exc:
        print(f"FAILED to connect: {exc}")
        return 1

    try:
        for migration_file in migration_files:
            sql = migration_file.read_text()
            try:
                conn.execute(sql)
                print(f"  OK — applied {migration_file.name}")
            except Exception as exc:
                print(f"  FAILED — {migration_file.name}: {exc}")
                return 1
    finally:
        conn.close()

    print("OK — all migrations applied successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
