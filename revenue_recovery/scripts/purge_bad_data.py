"""One-time migration and cleanup script for purging poisoned customer names and unapproved load-test data."""
from __future__ import annotations

import os
import sys

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.container import create_persistence_container
from app.dashboard_api import _get_items


def run_purge():
    # 1. Run against Postgres if configured, or memory
    mode = os.environ.get("PERSISTENCE_MODE", "postgres")
    print(f"Connecting to persistence container (mode={mode})...")
    container = create_persistence_container(mode)

    # 2. Execute purge of unapproved items and poisoned names
    stats = container.purge_unapproved_items()
    poisoned_cleared = stats["poisoned_names_cleared"]
    unapproved_purged = stats["unapproved_items_purged"]

    # 3. Check remaining live inbox count under allowlist filtering
    live_items = _get_items(container)
    live_inbox_count = len(live_items)

    print("=" * 60)
    print("PURGE & CLEANUP MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Poisoned Customer Names Cleared: {poisoned_cleared}")
    print(f"Unapproved/Stress Items Purged : {unapproved_purged}")
    print(f"Final Live Opportunity Inbox   : {live_inbox_count}")
    print("=" * 60)

    return {
        "poisoned_names_cleared": poisoned_cleared,
        "unapproved_items_purged": unapproved_purged,
        "live_inbox_count": live_inbox_count,
    }


if __name__ == "__main__":
    run_purge()
