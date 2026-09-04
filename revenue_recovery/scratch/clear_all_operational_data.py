from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.container import create_persistence_container
from app.dashboard_api import _get_items, build_dashboard_summary

def run_cleanup():
    print("=== STARTING COMPLETE OPERATIONAL DATA CLEANUP ===")
    
    # 1. Clear PostgreSQL persistence if available
    try:
        pg_container = create_persistence_container("postgres")
        pg_deleted = pg_container.reset_demo_data()
        print(f"PostgreSQL Operational Store Cleaned: {pg_deleted} items deleted.")
    except Exception as exc:
        print(f"PostgreSQL Cleanup Note: {exc}")

    # 2. Clear Memory persistence
    mem_container = create_persistence_container("memory")
    mem_deleted = mem_container.reset_demo_data()
    print(f"In-Memory Operational Store Cleaned: {mem_deleted} items deleted.")

    # 3. Verify PostgreSQL container status after reset
    try:
        pg_container = create_persistence_container("postgres")
        pg_items = _get_items(pg_container)
        pg_summary = build_dashboard_summary(pg_container)
        print("\n--- PostgreSQL Store Verification ---")
        print(f"Total Operational Items: {len(pg_items)}")
        print(f"Revenue at Risk        : ₹{pg_summary['revenue_at_risk'] / 100:,.2f}")
        print(f"Actually Recovered     : ₹{pg_summary['actually_recovered'] / 100:,.2f}")
    except Exception as exc:
        print(f"PostgreSQL Verification Note: {exc}")

    # 4. Verify Memory container status after reset
    mem_items = _get_items(mem_container)
    mem_summary = build_dashboard_summary(mem_container)
    print("\n--- In-Memory Store Verification ---")
    print(f"Total Operational Items: {len(mem_items)}")
    print(f"Revenue at Risk        : ₹{mem_summary['revenue_at_risk'] / 100:,.2f}")
    print(f"Actually Recovered     : ₹{mem_summary['actually_recovered'] / 100:,.2f}")

    print("\n=== OPERATIONAL DATA CLEANUP COMPLETE ===")

if __name__ == "__main__":
    run_cleanup()
