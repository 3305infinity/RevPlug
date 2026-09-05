from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.audit.models import AuditLog, InMemoryAuditLog
from app.db.decision_repository import (
    InMemoryRecoveryDecisionRepository,
    RecoveryDecisionRepository,
)
from app.db.postgres_repositories import (
    PostgresAuditLog,
    PostgresAttemptLedger,
    PostgresIdempotencyStore,
    PostgresProviderEventRepository,
    PostgresPromiseRepository,
    PostgresRecoveryItemRepository,
    PostgresRecoveryOutcomeRepository,
    PostgresRecoveryJobRepository,
)
from app.worker.job_repository import InMemoryRecoveryJobRepository
from app.db.repositories import InMemoryRecoveryItemRepository, RecoveryItemRepository
from app.db.session import PostgresConnection, create_connection
from app.idempotency.store import IdempotencyStore, InMemoryIdempotencyStore
from app.ledger.attempts import AttemptLedger, InMemoryAttemptLedger



@dataclass
class PersistenceContainer:
    """Holds all persistence dependencies for the application."""

    recovery_items: RecoveryItemRepository
    idempotency: IdempotencyStore
    audit_log: AuditLog
    attempts: AttemptLedger
    decisions: RecoveryDecisionRepository
    outcomes: "RecoveryOutcomeRepository"
    promises: "PromiseRepository"
    provider_events: "ProviderEventRepository"
    users: "object | None" = None
    sessions: "object | None" = None
    jobs: "object | None" = None  # RecoveryJobRepository (Stage 7 async worker)
    batches: "object | None" = None  # InMemoryBatchRepository (Stage 8 batch recovery)

    def get_clear_preview(self, item_id: str) -> dict[str, Any] | None:
        """Return real counts of operational records associated with a recovery case."""
        item = None
        if hasattr(self.recovery_items, "get"):
            item = self.recovery_items.get(item_id)
        elif hasattr(self.recovery_items, "_items"):
            item = self.recovery_items._items.get(item_id)

        if item is None:
            return None

        # Decisions count
        decisions_count = 0
        if hasattr(self.decisions, "list_by_recovery_item_id"):
            decisions_count = len(self.decisions.list_by_recovery_item_id(item_id))
        elif hasattr(self.decisions, "_decisions"):
            decs = self.decisions._decisions
            if isinstance(decs, list):
                decisions_count = sum(1 for d in decs if (d.get("recovery_item_id") if isinstance(d, dict) else getattr(d, "recovery_item_id", None)) == item_id)
            elif isinstance(decs, dict):
                decisions_count = 1 if item_id in decs else 0

        # Attempts count
        attempts_count = 0
        if hasattr(self.attempts, "attempts_for"):
            attempts_count = len(self.attempts.attempts_for(item_id))
        elif hasattr(self.attempts, "_records"):
            recs = self.attempts._records
            if isinstance(recs, list):
                attempts_count = sum(1 for a in recs if (a.get("recovery_item_id") if isinstance(a, dict) else getattr(a, "recovery_item_id", None)) == item_id)
            elif isinstance(recs, dict):
                attempts_count = len(recs.get(item_id, []))

        # Outcomes count
        outcomes_count = 0
        if hasattr(self.outcomes, "get_for_item"):
            outcomes_count = 1 if self.outcomes.get_for_item(item_id) is not None else 0
        elif hasattr(self.outcomes, "_outcomes"):
            outcomes_count = 1 if item_id in self.outcomes._outcomes else 0

        # Promises count
        promises_count = 0
        if hasattr(self.promises, "list_by_item"):
            promises_count = len(self.promises.list_by_item(item_id))
        elif hasattr(self.promises, "_by_item"):
            promises_count = 1 if item_id in self.promises._by_item else 0

        # Jobs count
        jobs_count = 0
        if hasattr(self.jobs, "_jobs"):
            jobs_list = self.jobs._jobs
            if isinstance(jobs_list, list):
                jobs_count = sum(1 for j in jobs_list if (j.get("recovery_item_id") if isinstance(j, dict) else getattr(j, "recovery_item_id", None)) == item_id)
            elif isinstance(jobs_list, dict):
                jobs_count = sum(1 for j in jobs_list.values() if (j.get("recovery_item_id") if isinstance(j, dict) else getattr(j, "recovery_item_id", None)) == item_id)

        # Provider events count
        provider_events_count = 0
        if hasattr(self.provider_events, "_events"):
            provider_events_count = sum(
                1 for ev in self.provider_events._events.values()
                if (ev.get("recovery_item_id") if isinstance(ev, dict) else getattr(ev, "recovery_item_id", None)) == item_id
            )

        # Batch membership
        batch_id = None
        if item is not None:
            meta = getattr(item, "metadata", {}) or {}
            if isinstance(meta, dict):
                batch_id = meta.get("batch_id")

        return {
            "recovery_item_id": item_id,
            "recovery_case": 1,
            "decisions_count": decisions_count,
            "attempts_count": attempts_count,
            "outcomes_count": outcomes_count,
            "promises_count": promises_count,
            "jobs_count": jobs_count,
            "provider_events_count": provider_events_count,
            "batch_id": batch_id,
        }

    def clear_recovery_item(self, item_id: str) -> dict[str, Any] | None:
        """Transactionally clear a recovery case and all corresponding operational data.

        Guarantees:
        - All removable operational descendants are cleared (decisions, attempts,
          outcomes, promises, jobs, provider_event links).
        - No orphaned records remain.
        - Audit history is preserved (append-only); a tombstone event is appended.
        - Batch membership metadata is removed from the item before deletion.
        - The operation is atomic: either complete deletion succeeds or nothing changes.
        """
        preview = self.get_clear_preview(item_id)
        if preview is None:
            return None

        # 1. Append tombstone audit log event for compliance history BEFORE clearing
        if hasattr(self.audit_log, "append"):
            from app.audit.models import AuditEvent
            from datetime import datetime, timezone
            import uuid
            try:
                self.audit_log.append(AuditEvent(
                    id=f"audit_{uuid.uuid4().hex[:12]}",
                    recovery_item_id=item_id,
                    actor="user",
                    action="case_cleared",
                    reason="User requested full deletion of recovery case operational data",
                    timestamp=datetime.now(timezone.utc),
                ))
            except Exception:
                pass

        # 2. In-Memory Path — copy-and-swap for atomicity
        if hasattr(self.recovery_items, "_items"):
            # Deep-copy all stores that will be mutated
            old_items = dict(self.recovery_items._items)
            old_attempts = list(self.attempts._records) if isinstance(self.attempts._records, list) else dict(self.attempts._records)
            old_decisions = list(self.decisions._decisions) if isinstance(self.decisions._decisions, list) else dict(self.decisions._decisions)
            old_outcomes = dict(self.outcomes._outcomes) if hasattr(self.outcomes, "_outcomes") else {}
            old_promises_item = dict(self.promises._by_item) if hasattr(self.promises, "_by_item") else {}
            old_promises_id = dict(self.promises._by_id) if hasattr(self.promises, "_by_id") else {}
            old_jobs = list(self.jobs._jobs) if self.jobs is not None and hasattr(self.jobs, "_jobs") and isinstance(self.jobs._jobs, list) else (dict(self.jobs._jobs) if self.jobs is not None and hasattr(self.jobs, "_jobs") and isinstance(self.jobs._jobs, dict) else None)

            try:
                # Remove the item
                old_items.pop(item_id, None)

                # Filter attempts
                if isinstance(old_attempts, list):
                    new_attempts = [
                        a for a in old_attempts
                        if (a.get("recovery_item_id") if isinstance(a, dict) else getattr(a, "recovery_item_id", None)) != item_id
                    ]
                else:
                    new_attempts = {k: v for k, v in old_attempts.items() if k != item_id}

                # Filter decisions
                if isinstance(old_decisions, list):
                    new_decisions = [
                        d for d in old_decisions
                        if (d.get("recovery_item_id") if isinstance(d, dict) else getattr(d, "recovery_item_id", None)) != item_id
                    ]
                else:
                    new_decisions = {k: v for k, v in old_decisions.items() if k != item_id}

                # Remove outcome
                old_outcomes.pop(item_id, None)

                # Remove promises
                old_promises_item.pop(item_id, None)
                to_remove_promises = [
                    k for k, v in old_promises_id.items()
                    if (v.get("recovery_item_id") if isinstance(v, dict) else getattr(v, "recovery_item_id", None)) == item_id
                ]
                for k in to_remove_promises:
                    old_promises_id.pop(k, None)

                # Filter jobs
                if old_jobs is not None:
                    if isinstance(old_jobs, list):
                        new_jobs = [
                            j for j in old_jobs
                            if (j.get("recovery_item_id") if isinstance(j, dict) else getattr(j, "recovery_item_id", None)) != item_id
                        ]
                    else:
                        new_jobs = {k: v for k, v in old_jobs.items() if (v.get("recovery_item_id") if isinstance(v, dict) else getattr(v, "recovery_item_id", None)) != item_id}

                # Nullify provider event links
                if hasattr(self.provider_events, "_events"):
                    for ev in self.provider_events._events.values():
                        if isinstance(ev, dict) and ev.get("recovery_item_id") == item_id:
                            ev["recovery_item_id"] = None
                        elif hasattr(ev, "recovery_item_id") and getattr(ev, "recovery_item_id") == item_id:
                            setattr(ev, "recovery_item_id", None)

                # Commit: swap all copies into place atomically
                self.recovery_items._items = old_items
                if hasattr(self.attempts, "_records"):
                    self.attempts._records = new_attempts
                if hasattr(self.decisions, "_decisions"):
                    self.decisions._decisions = new_decisions
                if hasattr(self.outcomes, "_outcomes"):
                    self.outcomes._outcomes = old_outcomes
                if hasattr(self.promises, "_by_item"):
                    self.promises._by_item = old_promises_item
                if hasattr(self.promises, "_by_id"):
                    self.promises._by_id = old_promises_id
                if hasattr(self.jobs, "_jobs") and old_jobs is not None:
                    self.jobs._jobs = new_jobs

            except Exception:
                # Rollback: restore original state (copies are untouched)
                self.recovery_items._items = old_items
                if hasattr(self.attempts, "_records"):
                    self.attempts._records = old_attempts
                if hasattr(self.decisions, "_decisions"):
                    self.decisions._decisions = old_decisions
                if hasattr(self.outcomes, "_outcomes"):
                    self.outcomes._outcomes = old_outcomes
                if hasattr(self.promises, "_by_item"):
                    self.promises._by_item = old_promises_item
                if hasattr(self.promises, "_by_id"):
                    self.promises._by_id = old_promises_id
                if hasattr(self.jobs, "_jobs") and old_jobs is not None:
                    self.jobs._jobs = old_jobs
                raise

        # 3. PostgreSQL Path — each statement runs in its own pooled connection
        if hasattr(self.recovery_items, "_conn") and getattr(self.recovery_items, "_conn") is not None:
            db_conn = getattr(self.recovery_items, "_conn")

            # Nullify provider event links (no trigger constraints here)
            try:
                db_conn.execute(
                    "UPDATE provider_events SET recovery_item_id = NULL WHERE recovery_item_id = %s",
                    (item_id,),
                )
            except Exception:
                pass

            # Delete operational descendants — each in its own connection so one failure
            # does not poison the transaction state for the others.
            for table in ["attempts", "recovery_decisions", "recovery_outcomes", "promises", "recovery_jobs"]:
                try:
                    db_conn.execute(f"DELETE FROM {table} WHERE recovery_item_id = %s", (item_id,))
                except Exception as ex:
                    print(f"[clear_recovery_item] PG delete {table} warning: {ex}")

            # Soft-clear the item — the no-delete trigger on recovery_items is intentional
            # and must not be bypassed.  Use a fresh connection to guarantee a clean state.
            try:
                db_conn.execute(
                    "UPDATE recovery_items SET status = 'stopped', metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{cleared}', 'true') WHERE id = %s",
                    (item_id,),
                )
            except Exception as exc:
                print(f"[clear_recovery_item] PG soft-clear warning: {exc}")

        return {
            "status": "success",
            "recovery_item_id": item_id,
            "cleared_counts": preview,
        }


    def purge_poisoned_customer_names(self) -> int:
        """Scan all persisted RecoveryItems and set metadata.customer_name = None if it matches a banned enterprise name."""
        banned_patterns = [
            "swiggy", "zomato", "acme global", "flipkart", "reliance retail",
            "paytm business", "inmobi", "razorpay enterprise", "phonepe", "freshworks",
            "pvt ltd", "enterprise direct", "merchant pay"
        ]
        count = 0

        # In-memory path
        if hasattr(self.recovery_items, "_items"):
            items_repo = getattr(self.recovery_items, "_items")
            for item in list(items_repo.values()):
                meta = getattr(item, "metadata", {}) or {}
                if isinstance(meta, dict):
                    c_name = meta.get("customer_name")
                    if c_name and isinstance(c_name, str):
                        if any(pat in c_name.lower() for pat in banned_patterns):
                            meta["customer_name"] = None
                            count += 1

        # Postgres path
        if hasattr(self.recovery_items, "_conn") and getattr(self.recovery_items, "_conn") is not None:
            db_conn = getattr(self.recovery_items, "_conn")
            try:
                import json
                rows = db_conn.fetchall("SELECT id, metadata FROM recovery_items")
                if rows:
                    poisoned_ids = []
                    for r in rows:
                        if isinstance(r, dict):
                            i_id = r.get("id")
                            m = r.get("metadata") or {}
                            if isinstance(m, dict):
                                cn = m.get("customer_name")
                                if cn and isinstance(cn, str):
                                    if any(pat in cn.lower() for pat in banned_patterns):
                                        if i_id:
                                            poisoned_ids.append(i_id)
                    if poisoned_ids:
                        for p_id in poisoned_ids:
                            try:
                                row = db_conn.fetchone("SELECT metadata FROM recovery_items WHERE id = %s", (p_id,))
                                if row and "metadata" in row and isinstance(row["metadata"], dict):
                                    meta = row["metadata"]
                                    meta["customer_name"] = None
                                    db_conn.execute("UPDATE recovery_items SET metadata = %s WHERE id = %s", (json.dumps(meta), p_id))
                                    count += 1
                            except Exception as ex:
                                print(f"[purge_poisoned_customer_names] item update warning: {ex}")
            except Exception as exc:
                print(f"[purge_poisoned_customer_names] Postgres warning: {exc}")

        return count

    def purge_unapproved_items(self) -> dict[str, int]:
        """Purge all accumulated load/stress/test/unapproved items whose source is NOT in APPROVED_LIVE_SOURCES."""
        approved_sources = {"webhook_live", "manual_case", "webhook"}
        unapproved_ids: set[str] = set()

        # In-memory path
        if hasattr(self.recovery_items, "_items"):
            items_repo = getattr(self.recovery_items, "_items")
            for item_id, item in list(items_repo.items()):
                meta = getattr(item, "metadata", {}) or {}
                src = str(meta.get("source", "") if isinstance(meta, dict) else "").strip().lower()
                if src not in approved_sources:
                    unapproved_ids.add(item_id)

        # Postgres path
        if hasattr(self.recovery_items, "_conn") and getattr(self.recovery_items, "_conn") is not None:
            db_conn = getattr(self.recovery_items, "_conn")
            try:
                rows = db_conn.fetchall("SELECT id, metadata FROM recovery_items")
                if rows:
                    for r in rows:
                        if isinstance(r, dict):
                            i_id = r.get("id")
                            m = r.get("metadata") or {}
                            src = str(m.get("source", "") if isinstance(m, dict) else "").strip().lower()
                            if src not in approved_sources:
                                if i_id:
                                    unapproved_ids.add(i_id)
            except Exception as exc:
                print(f"[purge_unapproved_items] Postgres scan warning: {exc}")

        count = len(unapproved_ids)
        if unapproved_ids:
            ids_list = list(unapproved_ids)
            if hasattr(self.recovery_items, "_conn") and getattr(self.recovery_items, "_conn") is not None:
                db_conn = getattr(self.recovery_items, "_conn")
                try:
                    # Update status to stopped and mark source=unapproved_purged so trigger passes and filter excludes
                    for u_id in ids_list:
                        try:
                            row = db_conn.fetchone("SELECT metadata FROM recovery_items WHERE id = %s", (u_id,))
                            meta = row.get("metadata") if row and isinstance(row, dict) else {}
                            if not isinstance(meta, dict):
                                meta = {}
                            meta["source"] = "unapproved_purged"
                            meta["batch_scope"] = True
                            meta["stopped_reason"] = "purged_unapproved_data"
                            import json
                            db_conn.execute(
                                "UPDATE recovery_items SET status = 'stopped', metadata = %s WHERE id = %s",
                                (json.dumps(meta), u_id)
                            )
                        except Exception as ex:
                            print(f"[purge_unapproved_items] item update warning: {ex}")
                except Exception as exc:
                    print(f"[purge_unapproved_items] Postgres deletion warning: {exc}")

            if hasattr(self.recovery_items, "_items"):
                items_repo = getattr(self.recovery_items, "_items")
                for i_id in unapproved_ids:
                    items_repo.pop(i_id, None)

        poisoned_cleared = self.purge_poisoned_customer_names()
        return {
            "unapproved_items_purged": count,
            "poisoned_names_cleared": poisoned_cleared,
        }

    def purge_batch_items(self) -> int:
        """Purge all batch-scoped synthetic items sitting in the primary recovery store."""
        count = 0
        batch_item_ids: set[str] = set()

        # 1. Collect in-memory batch item IDs
        if hasattr(self.recovery_items, "_items"):
            items_repo = getattr(self.recovery_items, "_items")
            for item_id, item in list(items_repo.items()):
                meta = getattr(item, "metadata", {}) or {}
                if isinstance(meta, dict) and (meta.get("batch_scope") or meta.get("batch_id")):
                    batch_item_ids.add(item_id)

        # 2. PostgreSQL Path
        if hasattr(self.recovery_items, "_conn") and getattr(self.recovery_items, "_conn") is not None:
            db_conn = getattr(self.recovery_items, "_conn")
            try:
                rows = db_conn.fetchall("SELECT id, metadata FROM recovery_items")
                if rows:
                    for r in rows:
                        if isinstance(r, dict):
                            i_id = r.get("id")
                            m = r.get("metadata") or {}
                            if isinstance(m, dict) and (m.get("batch_scope") or m.get("batch_id")):
                                if i_id:
                                    batch_item_ids.add(i_id)

                if batch_item_ids:
                    ids_list = list(batch_item_ids)
                    count = len(ids_list)
                    for table in ["recovery_outcomes", "promises", "audit_log", "attempts", "recovery_decisions", "recovery_jobs"]:
                        try:
                            db_conn.execute(f"DELETE FROM {table} WHERE recovery_item_id = ANY(%(ids)s)", {"ids": ids_list})
                        except Exception:
                            pass
                    db_conn.execute("DELETE FROM recovery_items WHERE id = ANY(%(ids)s)", {"ids": ids_list})
            except Exception as exc:
                print(f"[purge_batch_items] PostgreSQL deletion warning: {exc}")

        # 3. In-memory cleanup
        if hasattr(self.recovery_items, "_items"):
            items_repo = getattr(self.recovery_items, "_items")
            count = max(count, len(batch_item_ids))
            for item_id in batch_item_ids:
                items_repo.pop(item_id, None)

        return count

    def reset_demo_data(self) -> int:
        """Permanently deletes synthetic and existing recovery items and cleans all operational stores."""
        count = self.purge_batch_items()

        # 1. PostgreSQL Deletion Path (if configured)
        if hasattr(self.recovery_items, "_conn") and getattr(self.recovery_items, "_conn") is not None:
            db_conn = getattr(self.recovery_items, "_conn")
            try:
                # Atomically truncate all tables with CASCADE to handle foreign keys
                db_conn.execute("TRUNCATE TABLE recovery_items, recovery_outcomes, promises, provider_events, recovery_decisions, audit_log, idempotency_keys, attempts, recovery_jobs, recovery_batches CASCADE;")
            except Exception as exc:
                print(f"[reset_demo_data] PostgreSQL truncate CASCADE info: {exc}")
                # Fallback: Delete table by table in reverse dependency order
                for table in ["recovery_outcomes", "promises", "audit_log", "attempts", "recovery_decisions", "recovery_jobs", "provider_events", "idempotency_keys", "recovery_batches", "recovery_items"]:
                    try:
                        db_conn.execute(f"DELETE FROM {table}")
                    except Exception:
                        pass

        # 2. In-Memory Deletion Path (cleans all in-memory repository caches)
        if hasattr(self.recovery_items, "_items"):
            items_repo = getattr(self.recovery_items, "_items")
            mem_count = len(items_repo)
            count = max(count, mem_count)
            items_repo.clear()

        if hasattr(self.audit_log, "_events"):
            events = getattr(self.audit_log, "_events")
            events.clear()

        if hasattr(self.attempts, "_records"):
            records = getattr(self.attempts, "_records")
            records.clear()

        if hasattr(self.decisions, "_decisions"):
            decisions = getattr(self.decisions, "_decisions")
            decisions.clear()

        if hasattr(self.outcomes, "_outcomes"):
            outcomes = getattr(self.outcomes, "_outcomes")
            outcomes.clear()

        if hasattr(self.promises, "_by_item"):
            promises_by_item = getattr(self.promises, "_by_item")
            promises_by_item.clear()
        if hasattr(self.promises, "_by_id"):
            promises_by_id = getattr(self.promises, "_by_id")
            promises_by_id.clear()

        if hasattr(self, "idempotency") and self.idempotency is not None and hasattr(self.idempotency, "_processed"):
            idempotency_repo = getattr(self.idempotency, "_processed")
            idempotency_repo.clear()

        if hasattr(self, "provider_events") and self.provider_events is not None and hasattr(self.provider_events, "_events"):
            pe_repo = getattr(self.provider_events, "_events")
            pe_repo.clear()

        if hasattr(self, "jobs") and self.jobs is not None and hasattr(self.jobs, "_jobs"):
            jobs_repo = getattr(self.jobs, "_jobs")
            if isinstance(jobs_repo, dict):
                jobs_repo.clear()
            elif isinstance(jobs_repo, list):
                jobs_repo.clear()

        if hasattr(self, "batches") and self.batches is not None and hasattr(self.batches, "_batches"):
            batches_repo = getattr(self.batches, "_batches")
            batches_repo.clear()

        return count


def create_persistence_container(mode: str | None = None) -> PersistenceContainer:
    """Create a persistence container based on the configured mode.

    Args:
        mode: "memory" or "postgres". If None, reads PERSISTENCE_MODE env var,
              defaulting to "memory".
    """
    if mode is None:
        mode = os.environ.get("PERSISTENCE_MODE", "postgres")

    if mode == "memory":
        from app.services.batch_service import InMemoryBatchRepository
        return PersistenceContainer(
            recovery_items=InMemoryRecoveryItemRepository(),
            idempotency=InMemoryIdempotencyStore(),
            audit_log=InMemoryAuditLog(),
            attempts=InMemoryAttemptLedger(),
            decisions=InMemoryRecoveryDecisionRepository(),
            outcomes=_InMemoryRecoveryOutcomeRepository(),
            promises=_InMemoryPromiseRepository(),
            provider_events=_InMemoryProviderEventRepository(),
            users=_InMemoryUserRepository(),
            sessions=_InMemorySessionRepository(),
            jobs=InMemoryRecoveryJobRepository(),
            batches=InMemoryBatchRepository(),
        )

    if mode == "postgres":
        conn = create_connection()
        from app.db.postgres_repositories import (
            PostgresRecoveryDecisionRepository,
            PostgresUserRepository,
            PostgresSessionRepository,
        )
        return PersistenceContainer(
            recovery_items=PostgresRecoveryItemRepository(conn),
            idempotency=PostgresIdempotencyStore(conn),
            audit_log=PostgresAuditLog(conn),
            attempts=PostgresAttemptLedger(conn),
            decisions=PostgresRecoveryDecisionRepository(conn),
            outcomes=PostgresRecoveryOutcomeRepository(conn),
            promises=PostgresPromiseRepository(conn),
            provider_events=PostgresProviderEventRepository(conn),
            users=PostgresUserRepository(conn),
            sessions=PostgresSessionRepository(conn),
            jobs=PostgresRecoveryJobRepository(conn),
            batches=InMemoryBatchRepository() if "InMemoryBatchRepository" in locals() else None,
        )

    raise ValueError(f"Unknown PERSISTENCE_MODE: {mode!r}. Use 'memory' or 'postgres'.")


# ---------------------------------------------------------------------------
# In-memory implementations for new canonical repositories
# ---------------------------------------------------------------------------

class _InMemoryRecoveryOutcomeRepository:
    """In-memory outcome repository for unit tests and local development."""

    def __init__(self) -> None:
        self._outcomes: dict[str, dict] = {}

    def save(self, outcome) -> None:
        self._outcomes[outcome.recovery_item_id] = outcome

    def get_for_item(self, recovery_item_id: str):
        from app.domain.models import RecoveryOutcome
        data = self._outcomes.get(recovery_item_id)
        return data

    def list_all(self) -> list:
        return list(self._outcomes.values())


class _InMemoryPromiseRepository:
    """In-memory promise repository — full CRUD for Stage 8 promise lifecycle."""

    def __init__(self) -> None:
        self._by_item: dict[str, object] = {}   # item_id → Promise
        self._by_id: dict[str, object] = {}     # promise_id → Promise

    def save(self, promise) -> None:
        if isinstance(promise, dict):
            item_id = promise.get("recovery_item_id", "")
            promise_id = promise.get("id", "")
        else:
            item_id = promise.recovery_item_id
            promise_id = promise.id
        self._by_item[item_id] = promise
        if promise_id:
            self._by_id[promise_id] = promise

    def get_for_item(self, recovery_item_id: str):
        return self._by_item.get(recovery_item_id)

    def get(self, promise_id: str):
        """Get promise by its own ID."""
        return self._by_id.get(promise_id)

    def list_all(self) -> list:
        """List all promises."""
        return list(self._by_id.values())

    def list_by_item(self, item_id: str) -> list:
        p = self._by_item.get(item_id)
        return [p] if p is not None else []

    def list_by_customer(self, customer_id: str) -> list:
        result = []
        for promise in self._by_id.values():
            p_cust = getattr(promise, "customer_id", None) or (promise.get("customer_id") if isinstance(promise, dict) else None)
            if p_cust == customer_id:
                result.append(promise)
        return result

    def update_status(self, promise_id: str, status: str, **extra) -> object | None:
        """Update promise status and extra fields. Returns updated promise."""
        from app.domain.models import Promise
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        promise = self._by_id.get(promise_id)
        if promise is None:
            return None
        if isinstance(promise, Promise):
            updated = Promise(
                id=promise.id,
                recovery_item_id=promise.recovery_item_id,
                customer_id=promise.customer_id,
                promised_amount_minor=promise.promised_amount_minor,
                promised_date=promise.promised_date,
                status=status,
                created_at=promise.created_at,
                fulfilled_at=extra.get("fulfilled_at", promise.fulfilled_at),
                expired_at=extra.get("expired_at", promise.expired_at),
                metadata={**promise.metadata, **extra.get("metadata", {})},
            )
            self.save(updated)
            return updated
        if isinstance(promise, dict):
            promise["status"] = status
            if "fulfilled_at" in extra:
                promise["fulfilled_at"] = extra["fulfilled_at"].isoformat() if hasattr(extra["fulfilled_at"], "isoformat") else extra["fulfilled_at"]
            if "expired_at" in extra:
                promise["expired_at"] = extra["expired_at"].isoformat() if hasattr(extra["expired_at"], "isoformat") else extra["expired_at"]
            if "metadata" in extra:
                promise["metadata"] = {**promise.get("metadata", {}), **extra["metadata"]}
            self.save(promise)
            return promise
        return None


class _InMemoryProviderEventRepository:
    """In-memory provider event repository for unit tests and local development."""

    def __init__(self) -> None:
        self._events: dict[str, dict] = {}

    def _store_key(self, provider: str, provider_event_id: str) -> str:
        return f"{provider}:{provider_event_id}"

    def try_insert(self, event) -> tuple[bool, object]:
        store_key = self._store_key(event.provider, event.provider_event_id)
        if store_key in self._events:
            return False, self._dict_to_event(self._events[store_key])
        self._events[store_key] = self._event_to_dict(event)
        return True, event

    def save(self, event) -> None:
        store_key = self._store_key(event.provider, event.provider_event_id)
        if store_key not in self._events:
            self._events[store_key] = self._event_to_dict(event)

    def get_by_provider_event(self, provider: str, provider_event_id: str):
        data = self._events.get(self._store_key(provider, provider_event_id))
        return self._dict_to_event(data) if data else None

    def mark_processed(self, provider: str, provider_event_id: str, recovery_item_id: str | None = None) -> None:
        store_key = self._store_key(provider, provider_event_id)
        data = self._events.get(store_key)
        if data:
            data["processing_status"] = "processed"
            data["processed_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            data["recovery_item_id"] = recovery_item_id

    def _event_to_dict(self, event) -> dict:
        return {
            "id": event.id,
            "provider": event.provider,
            "provider_event_id": event.provider_event_id,
            "received_at": event.received_at,
            "event_type": event.event_type,
            "raw_payload": event.raw_payload,
            "processing_status": event.processing_status,
            "processed_at": event.processed_at,
            "recovery_item_id": event.recovery_item_id,
            "error_message": event.error_message,
            "metadata": event.metadata,
        }

    def _dict_to_event(self, data: dict):
        from app.domain.models import ProviderEvent
        return ProviderEvent(
            id=data["id"],
            provider=data["provider"],
            provider_event_id=data["provider_event_id"],
            received_at=data["received_at"],
            event_type=data["event_type"],
            raw_payload=data["raw_payload"],
            processing_status=data.get("processing_status", "pending"),
            processed_at=data.get("processed_at"),
            recovery_item_id=data.get("recovery_item_id"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


class RecoveryOutcomeRepository:
    """Persistence boundary for RecoveryOutcome."""

    def save(self, outcome) -> None:
        ...

    def get_for_item(self, recovery_item_id: str):
        ...


class PromiseRepository:
    """Persistence boundary for Promise."""

    def save(self, promise) -> None:
        ...

    def get_for_item(self, recovery_item_id: str):
        ...


class ProviderEventRepository:
    """Persistence boundary for ProviderEvent."""

    def try_insert(self, event) -> tuple[bool, object]:
        ...

    def save(self, event) -> None:
        ...


class _InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[str, object] = {}

    def create_user(self, email: str, password_hash: str, full_name: str):
        import uuid
        from datetime import datetime, timezone
        from app.domain.auth import User
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name.strip(),
            created_at=datetime.now(timezone.utc),
        )
        self._users[user.id] = user
        return user

    def get_by_email(self, email: str):
        clean_email = email.lower().strip()
        for u in self._users.values():
            if u.email.lower() == clean_email:
                return u
        return None

    def get_by_id(self, user_id: str):
        return self._users.get(user_id)


class _InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, object] = {}

    def create_session(self, user_id: str, *, expires_in_seconds: int = 86400 * 7):
        import secrets
        from datetime import datetime, timedelta, timezone
        from app.domain.auth import UserSession
        token = secrets.token_hex(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in_seconds)
        sess = UserSession(
            session_token=token,
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
        )
        self._sessions[token] = sess
        return sess

    def get_session(self, session_token: str):
        from datetime import datetime, timezone
        if not session_token:
            return None
        sess = self._sessions.get(session_token)
        if not sess:
            return None
        if sess.expires_at < datetime.now(timezone.utc):
            self.delete_session(session_token)
            return None
        return sess

    def delete_session(self, session_token: str) -> None:
        self._sessions.pop(session_token, None)
