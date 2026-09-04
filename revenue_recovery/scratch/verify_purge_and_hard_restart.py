from __future__ import annotations

import os
import sys
import psycopg

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import get_database_url
from app.db.container import create_persistence_container
from app.dashboard_api import _get_items, build_dashboard_summary

def main():
    print("==================================================")
    print("DIRECT HARD PURGE OF POSTGRESQL & MEMORY STORES")
    print("==================================================")

    url = get_database_url()
    print(f"DATABASE_URL: {url}")

    # 1. Direct PostgreSQL Truncate CASCADE
    try:
        conn = psycopg.connect(url, autocommit=True, connect_timeout=5)
        with conn.cursor() as cur:
            tables = [
                "recovery_outcomes", "promises", "provider_events", 
                "recovery_decisions", "audit_log", "idempotency_keys", 
                "attempts", "recovery_jobs", "recovery_batches", "recovery_items"
            ]
            print(f"Truncating PostgreSQL tables: {tables}...")
            cur.execute("TRUNCATE TABLE recovery_items, recovery_outcomes, promises, provider_events, recovery_decisions, audit_log, idempotency_keys, attempts, recovery_jobs, recovery_batches CASCADE;")
            print("PostgreSQL TRUNCATE CASCADE executed successfully.")

            cur.execute("SELECT count(*) FROM recovery_items;")
            row = cur.fetchone()
            print(f"PostgreSQL recovery_items count after truncate: {row[0]}")
        conn.close()
    except Exception as exc:
        print(f"PostgreSQL direct truncate result: {exc}")

    # 2. Memory Container Clean
    mem_container = create_persistence_container("memory")
    mem_container.reset_demo_data()
    mem_items = _get_items(mem_container)
    print(f"In-memory recovery_items count: {len(mem_items)}")

    # 3. Verify PostgreSQL via PersistenceContainer
    try:
        pg_container = create_persistence_container("postgres")
        pg_container.reset_demo_data()
        pg_items = _get_items(pg_container)
        summary = build_dashboard_summary(pg_container)

        print("\n--- POSTGRESQL CONTAINER VERIFICATION ---")
        print(f"Total Recovery Items : {len(pg_items)}")
        print(f"Revenue at Risk      : ₹{summary['revenue_at_risk'] / 100:,.2f}")
        print(f"Actually Recovered   : ₹{summary['actually_recovered'] / 100:,.2f}")
        print(f"Expected Recoverable : ₹{summary['expected_recovery'] / 100:,.2f}")
        print(f"Active Recoveries    : {summary['active_recoveries']}")
        print(f"Stopped Cases        : {summary['stopped_cases']}")
        print(f"Recovered Cases      : {summary['recovered_cases']}")
    except Exception as exc:
        print(f"PostgreSQL container verification note: {exc}")

    print("==================================================")

if __name__ == "__main__":
    main()
