from __future__ import annotations

import os
import sys
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import get_database_url
import psycopg

def inspect():
    url = get_database_url()
    print(f"DATABASE_URL: {url}")

    try:
        conn = psycopg.connect(url, autocommit=True, connect_timeout=5)
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row["table_name"] for row in cur.fetchall()]
            print(f"PostgreSQL Tables Found: {tables}")

            if "recovery_items" in tables:
                cur.execute("SELECT id, customer_id, amount, status, metadata FROM recovery_items")
                rows = cur.fetchall()
                print(f"\n--- recovery_items Table ({len(rows)} rows) ---")
                for r in rows:
                    meta = r.get("metadata")
                    if isinstance(meta, str):
                        try:
                            meta = json.loads(meta)
                        except Exception:
                            pass
                    c_name = meta.get("customer_name") if isinstance(meta, dict) else None
                    print(f"  ID: {r['id']} | Customer: {r['customer_id']} ({c_name}) | Amount: {r['amount']} | Status: {r['status']}")

            if "recovery_outcomes" in tables:
                cur.execute("SELECT * FROM recovery_outcomes")
                outcomes = cur.fetchall()
                print(f"\n--- recovery_outcomes Table ({len(outcomes)} rows) ---")
                for o in outcomes:
                    print(f"  {o}")

        conn.close()
    except Exception as exc:
        print(f"PostgreSQL connection failed: {exc}")

if __name__ == "__main__":
    inspect()
