"""Check that the database connection works and print table names."""
from __future__ import annotations

import sys

from app.db.session import create_connection, get_database_url


def main() -> int:
    url = get_database_url()
    # Mask the password for safe printing.
    safe_url = url
    if "@" in url:
        prefix, rest = url.split("://", 1)
        if "@" in rest:
            creds, host = rest.split("@", 1)
            if ":" in creds:
                user, _ = creds.split(":", 1)
                safe_url = f"{prefix}://{user}:***@{host}"

    print(f"Connecting to: {safe_url}")
    try:
        conn = create_connection()
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    try:
        tables = conn.fetchall(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        table_names = [row["table_name"] for row in tables]
        print("OK — connected successfully.")
        print(f"Tables: {', '.join(table_names) if table_names else '(none)'}")
        return 0
    except Exception as exc:
        print(f"FAILED to list tables: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
