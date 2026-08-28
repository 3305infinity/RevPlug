"""Initialize the database schema by running all migrations in order."""
from __future__ import annotations

import sys
from pathlib import Path

from app.db.session import create_connection, get_database_url


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
        conn = create_connection()
    except Exception as exc:
        print(f"FAILED to connect: {exc}")
        return 1

    for migration_file in migration_files:
        sql = migration_file.read_text()
        try:
            conn._conn.execute(sql)
            conn._conn.commit()
            print(f"  OK — applied {migration_file.name}")
        except Exception as exc:
            conn._conn.rollback()
            print(f"  FAILED — {migration_file.name}: {exc}")
            return 1

    print("OK — all migrations applied successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
