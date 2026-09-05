from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from app.audit.models import AuditEvent
from app.db.session import PostgresConnection
from app.domain.models import (
    RecoveryItem,
    RecoveryOutcome,
    RecoveryStatus,
    SourceType,
    ProviderEvent,
    Promise,
)
from app.domain.proposals import RecoveryProposal
from app.idempotency.store import IdempotencyStore
from app.ledger.attempts import AttemptLedger, AttemptRecord


class PostgresRecoveryItemRepository:
    """PostgreSQL-backed RecoveryItem repository with canonical schema."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def save(self, item: RecoveryItem) -> None:
        self._conn.execute(
            """
            INSERT INTO recovery_items
                (id, source_type, external_id, customer_id, amount, currency,
                 created_at, due_at, status, root_cause, risk_score,
                 expected_recovery_value, intervention_cost, failure_category,
                 provider, provider_event_id, actual_recovery_value, recovery_status,
                 score_version, scoring_reason, priority,
                 metadata, updated_at)
            VALUES (%(id)s, %(source_type)s, %(external_id)s, %(customer_id)s,
                    %(amount)s, %(currency)s, %(created_at)s, %(due_at)s,
                    %(status)s, %(root_cause)s, %(risk_score)s,
                    %(expected_recovery_value)s, %(intervention_cost)s, %(failure_category)s,
                    %(provider)s, %(provider_event_id)s, %(actual_recovery_value)s, %(recovery_status)s,
                    %(score_version)s, %(scoring_reason)s, %(priority)s,
                    %(metadata)s, now())
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                root_cause = EXCLUDED.root_cause,
                risk_score = EXCLUDED.risk_score,
                expected_recovery_value = EXCLUDED.expected_recovery_value,
                intervention_cost = EXCLUDED.intervention_cost,
                failure_category = EXCLUDED.failure_category,
                provider = EXCLUDED.provider,
                provider_event_id = EXCLUDED.provider_event_id,
                actual_recovery_value = EXCLUDED.actual_recovery_value,
                recovery_status = EXCLUDED.recovery_status,
                score_version = EXCLUDED.score_version,
                scoring_reason = EXCLUDED.scoring_reason,
                priority = EXCLUDED.priority,
                metadata = EXCLUDED.metadata,
                updated_at = now()
            """,
            {
                "id": item.id,
                "source_type": item.source_type.value,
                "external_id": item.external_id,
                "customer_id": item.customer_id,
                "amount": item.amount_minor,
                "currency": item.currency,
                "created_at": item.created_at,
                "due_at": item.due_at,
                "status": item.status.value,
                "root_cause": item.root_cause,
                "risk_score": item.recovery_probability,
                "expected_recovery_value": item.expected_recovery_value,
                "intervention_cost": item.intervention_cost,
                "failure_category": item.failure_category,
                "provider": item.provider,
                "provider_event_id": item.provider_event_id,
                "actual_recovery_value": item.actual_recovery_value,
                "recovery_status": item.recovery_status,
                "score_version": item.score_version,
                "scoring_reason": item.scoring_reason,
                "priority": item.priority,
                "metadata": json.dumps(item.metadata),
            },
        )

    def get(self, item_id: str) -> RecoveryItem | None:
        row = self._conn.fetchone(
            "SELECT * FROM recovery_items WHERE id = %s", (item_id,)
        )
        if not row:
            return None
        return RecoveryItem(
            id=str(row["id"]),
            source_type=SourceType(row["source_type"]),
            external_id=row.get("external_id", row["id"]),
            customer_id=row["customer_id"],
            amount_minor=row["amount"],
            currency=row["currency"],
            created_at=row["created_at"],
            due_at=row.get("due_at"),
            status=RecoveryStatus(row["status"]),
            root_cause=row.get("root_cause"),
            recovery_probability=row.get("risk_score"),
            expected_recovery_value=row.get("expected_recovery_value"),
            intervention_cost=row.get("intervention_cost"),
            failure_category=row.get("failure_category"),
            provider=row.get("provider"),
            provider_event_id=row.get("provider_event_id"),
            actual_recovery_value=row.get("actual_recovery_value"),
            recovery_status=row.get("recovery_status"),
            score_version=row.get("score_version"),
            scoring_reason=row.get("scoring_reason"),
            priority=row.get("priority"),
            metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else json.loads(row.get("metadata", "{}")),
        )

    def update_status(self, item_id: str, status: RecoveryStatus) -> None:
        self._conn.execute(
            "UPDATE recovery_items SET status = %s, updated_at = now() WHERE id = %s",
            (status.value, item_id),
        )

    def list_all(self, limit: int = 5000) -> list[RecoveryItem]:
        """Return all recovery items, newest first. Used by dashboard API."""
        rows = self._conn.fetchall(
            "SELECT * FROM recovery_items ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        result = []
        for row in rows:
            try:
                result.append(RecoveryItem(
                    id=str(row["id"]),
                    source_type=SourceType(row["source_type"]),
                    external_id=row.get("external_id", row["id"]),
                    customer_id=row["customer_id"],
                    amount_minor=row["amount"],
                    currency=row["currency"],
                    created_at=row["created_at"],
                    due_at=row.get("due_at"),
                    status=RecoveryStatus(row["status"]),
                    root_cause=row.get("root_cause"),
                    recovery_probability=row.get("risk_score"),
                    expected_recovery_value=row.get("expected_recovery_value"),
                    intervention_cost=row.get("intervention_cost"),
                    failure_category=row.get("failure_category"),
                    provider=row.get("provider"),
                    provider_event_id=row.get("provider_event_id"),
                    actual_recovery_value=row.get("actual_recovery_value"),
                    recovery_status=row.get("recovery_status"),
                    score_version=row.get("score_version"),
                    scoring_reason=row.get("scoring_reason"),
                    priority=row.get("priority"),
                    metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else json.loads(row.get("metadata") or "{}"),
                ))
            except Exception:
                continue
        return result


class PostgresRecoveryOutcomeRepository:
    """PostgreSQL-backed recovery outcome repository."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def save(self, outcome: RecoveryOutcome) -> None:
        self._conn.execute(
            """
            INSERT INTO recovery_outcomes
                (id, recovery_item_id, outcome_type, expected_recovery_minor,
                 actual_recovery_minor, recovery_cost_minor,
                 recovered_at, created_at, metadata)
            VALUES (%(id)s, %(recovery_item_id)s, %(outcome_type)s,
                    %(expected_recovery_minor)s, %(actual_recovery_minor)s,
                    %(recovery_cost_minor)s,
                    %(recovered_at)s, %(created_at)s, %(metadata)s)
            ON CONFLICT (recovery_item_id) DO UPDATE SET
                outcome_type = EXCLUDED.outcome_type,
                actual_recovery_minor = EXCLUDED.actual_recovery_minor,
                recovery_cost_minor = EXCLUDED.recovery_cost_minor,
                recovered_at = EXCLUDED.recovered_at,
                metadata = EXCLUDED.metadata
            """,
            {
                "id": outcome.id,
                "recovery_item_id": outcome.recovery_item_id,
                "outcome_type": outcome.outcome_type,
                "expected_recovery_minor": outcome.expected_recovery_minor,
                "actual_recovery_minor": outcome.actual_recovery_minor,
                "recovery_cost_minor": outcome.recovery_cost_minor,
                "net_recovery_minor": outcome.net_recovery_minor,
                "recovered_at": outcome.recovered_at,
                "created_at": outcome.created_at or datetime.now(),
                "metadata": json.dumps(outcome.metadata),
            },
        )

    def get_for_item(self, recovery_item_id: str) -> RecoveryOutcome | None:
        row = self._conn.fetchone(
            "SELECT * FROM recovery_outcomes WHERE recovery_item_id = %s",
            (recovery_item_id,),
        )
        if not row:
            return None
        return self._row_to_outcome(row)

    def _row_to_outcome(self, row: dict[str, Any]) -> RecoveryOutcome:
        return RecoveryOutcome(
            id=str(row["id"]),
            recovery_item_id=str(row["recovery_item_id"]),
            outcome_type=row["outcome_type"],
            expected_recovery_minor=row["expected_recovery_minor"],
            actual_recovery_minor=row.get("actual_recovery_minor"),
            recovery_cost_minor=row.get("recovery_cost_minor", 0),
            net_recovery_minor=row.get("net_recovery_minor"),
            recovered_at=row.get("recovered_at"),
            created_at=row.get("created_at"),
            metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else json.loads(row.get("metadata", "{}")),
        )

    def list_all(self, limit: int = 5000) -> list[RecoveryOutcome]:
        """Return all outcomes. Used by dashboard API financial truth aggregation."""
        rows = self._conn.fetchall(
            "SELECT * FROM recovery_outcomes ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        result = []
        for row in rows:
            try:
                result.append(self._row_to_outcome(row))
            except Exception:
                continue
        return result


class PostgresPromiseRepository:
    """PostgreSQL-backed promise-to-pay repository."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def save(self, promise: Promise) -> None:
        self._conn.execute(
            """
            INSERT INTO promises
                (id, recovery_item_id, customer_id, promised_amount_minor,
                 promised_date, status, created_at, fulfilled_at, expired_at, metadata)
            VALUES (%(id)s, %(recovery_item_id)s, %(customer_id)s,
                    %(promised_amount_minor)s, %(promised_date)s, %(status)s,
                    %(created_at)s, %(fulfilled_at)s, %(expired_at)s, %(metadata)s)
            """,
            {
                "id": promise.id,
                "recovery_item_id": promise.recovery_item_id,
                "customer_id": promise.customer_id,
                "promised_amount_minor": promise.promised_amount_minor,
                "promised_date": promise.promised_date,
                "status": promise.status,
                "created_at": promise.created_at or datetime.now(),
                "fulfilled_at": promise.fulfilled_at,
                "expired_at": promise.expired_at,
                "metadata": json.dumps(promise.metadata),
            },
        )

    def get_for_item(self, recovery_item_id: str) -> Promise | None:
        row = self._conn.fetchone(
            "SELECT * FROM promises WHERE recovery_item_id = %s ORDER BY created_at DESC LIMIT 1",
            (recovery_item_id,),
        )
        if not row:
            return None
        return Promise(
            id=str(row["id"]),
            recovery_item_id=str(row["recovery_item_id"]),
            customer_id=row["customer_id"],
            promised_amount_minor=row["promised_amount_minor"],
            promised_date=row["promised_date"],
            status=row["status"],
            created_at=row.get("created_at"),
            fulfilled_at=row.get("fulfilled_at"),
            expired_at=row.get("expired_at"),
            metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else json.loads(row.get("metadata", "{}")),
        )


class PostgresProviderEventRepository:
    """PostgreSQL-backed provider event repository with durable uniqueness."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def try_insert(self, event: ProviderEvent) -> tuple[bool, ProviderEvent | None]:
        row = self._conn.fetchone(
            """
            INSERT INTO provider_events
                (id, provider, provider_event_id, received_at, event_type,
                 raw_payload, processing_status, processed_at,
                 recovery_item_id, error_message, metadata)
            VALUES (%(id)s, %(provider)s, %(provider_event_id)s, %(received_at)s,
                    %(event_type)s, %(raw_payload)s, %(processing_status)s,
                    %(processed_at)s, %(recovery_item_id)s, %(error_message)s,
                    %(metadata)s)
            ON CONFLICT (provider, provider_event_id) DO NOTHING
            RETURNING id, provider, provider_event_id, received_at, event_type,
                      raw_payload, processing_status, processed_at,
                      recovery_item_id, error_message, metadata
            """,
            {
                "id": event.id,
                "provider": event.provider,
                "provider_event_id": event.provider_event_id,
                "received_at": event.received_at,
                "event_type": event.event_type,
                "raw_payload": json.dumps(event.raw_payload),
                "processing_status": event.processing_status,
                "processed_at": event.processed_at,
                "recovery_item_id": event.recovery_item_id,
                "error_message": event.error_message,
                "metadata": json.dumps(event.metadata),
            },
        )
        if row:
            return True, self._row_to_event(row)
        existing = self.get_by_provider_event(event.provider, event.provider_event_id)
        return False, existing

    def save(self, event: ProviderEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO provider_events
                (id, provider, provider_event_id, received_at, event_type,
                 raw_payload, processing_status, processed_at,
                 recovery_item_id, error_message, metadata)
            VALUES (%(id)s, %(provider)s, %(provider_event_id)s, %(received_at)s,
                    %(event_type)s, %(raw_payload)s, %(processing_status)s,
                    %(processed_at)s, %(recovery_item_id)s, %(error_message)s,
                    %(metadata)s)
            ON CONFLICT (provider, provider_event_id) DO NOTHING
            """,
            {
                "id": event.id,
                "provider": event.provider,
                "provider_event_id": event.provider_event_id,
                "received_at": event.received_at,
                "event_type": event.event_type,
                "raw_payload": json.dumps(event.raw_payload),
                "processing_status": event.processing_status,
                "processed_at": event.processed_at,
                "recovery_item_id": event.recovery_item_id,
                "error_message": event.error_message,
                "metadata": json.dumps(event.metadata),
            },
        )

    def get_by_provider_event(self, provider: str, provider_event_id: str) -> ProviderEvent | None:
        row = self._conn.fetchone(
            "SELECT * FROM provider_events WHERE provider = %s AND provider_event_id = %s",
            (provider, provider_event_id),
        )
        if not row:
            return None
        return self._row_to_event(row)

    def mark_processed(self, provider: str, provider_event_id: str, recovery_item_id: str | None = None) -> None:
        self._conn.execute(
            """
            UPDATE provider_events
            SET processing_status = 'processed', processed_at = now(),
                recovery_item_id = %(recovery_item_id)s
            WHERE provider = %(provider)s AND provider_event_id = %(provider_event_id)s
            """,
            {"provider": provider, "provider_event_id": provider_event_id, "recovery_item_id": recovery_item_id},
        )

    def _row_to_event(self, row: dict[str, Any]) -> ProviderEvent:
        return ProviderEvent(
            id=str(row["id"]),
            provider=row["provider"],
            provider_event_id=row["provider_event_id"],
            received_at=row["received_at"],
            event_type=row["event_type"],
            raw_payload=row.get("raw_payload", {}) if isinstance(row.get("raw_payload"), dict) else json.loads(row.get("raw_payload", "{}")),
            processing_status=row.get("processing_status", "pending"),
            processed_at=row.get("processed_at"),
            recovery_item_id=str(row.get("recovery_item_id")) if row.get("recovery_item_id") else None,
            error_message=row.get("error_message"),
            metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else json.loads(row.get("metadata", "{}")),
        )


class PostgresIdempotencyStore:
    """PostgreSQL-backed idempotency store using UNIQUE constraint on event_key."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def has_processed(self, key: str) -> bool:
        row = self._conn.fetchone(
            "SELECT event_key FROM idempotency_keys WHERE event_key = %s", (key,)
        )
        return row is not None

    def mark_processed(self, key: str) -> None:
        try:
            self._conn.execute(
                "INSERT INTO idempotency_keys (event_key) VALUES (%s)", (key,)
            )
        except Exception:
            self._conn._conn.rollback()


class PostgresAuditLog:
    """PostgreSQL-backed audit log."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def log(
        self,
        recovery_item_id: str | None,
        actor: str,
        action: str,
        reason: str | None = None,
        metadata: dict | None = None,
        event_type: str = "",
        source: str = "",
        reason_code: str = "",
        context_hash: str = "",
        correlation_id: str = "",
    ) -> AuditEvent:
        meta = metadata or {}
        if event_type: meta["event_type"] = event_type
        if source: meta["source"] = source
        if reason_code: meta["reason_code"] = reason_code
        if context_hash: meta["context_hash"] = context_hash
        if correlation_id: meta["correlation_id"] = correlation_id

        row = self._conn.fetchone(
            """
            INSERT INTO audit_log (recovery_item_id, actor, action, reasoning, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, recovery_item_id, actor, action, reasoning, metadata, timestamp
            """,
            (recovery_item_id, actor, action, reason, json.dumps(meta)),
        )
        parsed_meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
        return AuditEvent(
            id=str(row["id"]),
            recovery_item_id=str(row["recovery_item_id"]) if row.get("recovery_item_id") else "",
            actor=row["actor"],
            action=row["action"],
            reason=row["reasoning"],
            metadata=parsed_meta,
            timestamp=row["timestamp"],
            event_type=parsed_meta.get("event_type", ""),
            source=parsed_meta.get("source", ""),
            reason_code=parsed_meta.get("reason_code", ""),
            context_hash=parsed_meta.get("context_hash", ""),
            correlation_id=parsed_meta.get("correlation_id", ""),
        )

    def events_for(self, recovery_item_id: str) -> list[AuditEvent]:
        rows = self._conn.fetchall(
            "SELECT * FROM audit_log WHERE recovery_item_id = %s ORDER BY timestamp",
            (recovery_item_id,),
        )
        res = []
        for r in rows:
            meta = r["metadata"] if isinstance(r["metadata"], dict) else json.loads(r["metadata"])
            res.append(AuditEvent(
                id=str(r["id"]),
                recovery_item_id=str(r["recovery_item_id"]) if r.get("recovery_item_id") else "",
                actor=r["actor"],
                action=r["action"],
                reason=r["reasoning"],
                metadata=meta,
                timestamp=r["timestamp"],
                event_type=meta.get("event_type", ""),
                source=meta.get("source", ""),
                reason_code=meta.get("reason_code", ""),
                context_hash=meta.get("context_hash", ""),
                correlation_id=meta.get("correlation_id", ""),
            ))
        return res


class PostgresAttemptLedger:
    """PostgreSQL-backed attempt ledger."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def record(self, record: AttemptRecord) -> AttemptRecord:
        self._conn.execute(
            """
            INSERT INTO attempts
                (recovery_item_id, attempt_number, action, scheduled_at,
                 executed_at, outcome, metadata)
            VALUES (%(item_id)s, %(number)s, %(action)s, %(scheduled)s,
                    %(executed)s, %(outcome)s, %(metadata)s)
            """,
            {
                "item_id": record.recovery_item_id,
                "number": record.attempt_number,
                "action": record.action,
                "scheduled": record.scheduled_at,
                "executed": record.executed_at,
                "outcome": record.outcome,
                "metadata": json.dumps(record.metadata),
            },
        )
        return record

    def attempts_for(self, recovery_item_id: str) -> list[AttemptRecord]:
        rows = self._conn.fetchall(
            "SELECT * FROM attempts WHERE recovery_item_id = %s ORDER BY attempt_number",
            (recovery_item_id,),
        )
        return [
            AttemptRecord(
                recovery_item_id=str(r["recovery_item_id"]) if r.get("recovery_item_id") else None,
                attempt_number=r["attempt_number"],
                action=r["action"],
                scheduled_at=r["scheduled_at"],
                executed_at=r["executed_at"],
                outcome=r["outcome"],
                metadata=r["metadata"] if isinstance(r["metadata"], dict) else json.loads(r["metadata"]),
            )
            for r in rows
        ]


class PostgresRecoveryDecisionRepository:
    """PostgreSQL-backed recovery decision repository."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def save_decision(
        self,
        proposal: RecoveryProposal,
        *,
        item_id: str,
        agent_name: str,
        policy_allowed: bool | None = None,
        policy_rule: str | None = None,
        policy_reason: str | None = None,
        final_action: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO recovery_decisions
                (recovery_item_id, agent_name, model_name, proposed_action,
                 reason, confidence, customer_message, proposed_retry,
                 retry_metadata, evidence, policy_allowed, policy_rule,
                 final_action)
            VALUES
                (%(item_id)s, %(agent_name)s, %(model_name)s, %(action)s,
                 %(reason)s, %(confidence)s, %(message)s, %(retry)s,
                 %(retry_meta)s, %(evidence)s, %(allowed)s, %(rule)s,
                 %(final)s)
            """,
            {
                "item_id": item_id,
                "agent_name": agent_name,
                "model_name": proposal.model_name,
                "action": proposal.action.value,
                "reason": proposal.reason,
                "confidence": proposal.confidence,
                "message": proposal.customer_message,
                "retry": proposal.proposed_retry,
                "retry_meta": json.dumps(proposal.retry_metadata),
                "evidence": json.dumps(proposal.evidence),
                "allowed": policy_allowed,
                "rule": policy_rule,
                "final": final_action,
            },
        )

    def list_by_recovery_item_id(self, item_id: str) -> list[dict]:
        rows = self._conn.fetchall(
            "SELECT * FROM recovery_decisions WHERE recovery_item_id = %s ORDER BY created_at",
            (item_id,),
        )
        result = []
        for r in rows:
            d = dict(r)
            if d.get("id"):
                d["id"] = str(d["id"])
            if d.get("recovery_item_id"):
                d["recovery_item_id"] = str(d["recovery_item_id"])
            if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            result.append(d)
        return result


class PostgresRecoveryJobRepository:
    """PostgreSQL-backed recovery job repository using FOR UPDATE SKIP LOCKED."""

    def __init__(self, conn) -> None:
        self._conn = conn

    def create_job(
        self,
        recovery_item_id: str,
        *,
        max_attempts: int = 3,
        metadata: dict | None = None,
    ):
        """Create a QUEUED job. Returns None if an active job already exists (ON CONFLICT DO NOTHING)."""
        from app.worker.models import RecoveryJob, JobStatus
        job_id = str(uuid.uuid4())
        row = self._conn.fetchone(
            """
            INSERT INTO recovery_jobs
                (job_id, recovery_item_id, status, max_attempts, metadata)
            VALUES (%(job_id)s, %(item_id)s, 'QUEUED', %(max_attempts)s, %(meta)s)
            ON CONFLICT (recovery_item_id)
                WHERE status IN ('QUEUED', 'PROCESSING')
            DO NOTHING
            RETURNING job_id, recovery_item_id, status, attempt_count, max_attempts,
                      available_at, locked_at, locked_by, last_error, created_at,
                      completed_at, metadata
            """,
            {
                "job_id": job_id,
                "item_id": recovery_item_id,
                "max_attempts": max_attempts,
                "meta": json.dumps(metadata or {}),
            },
        )
        if row is None:
            return None  # active job already existed
        return self._row_to_job(row)

    def claim_next_job(
        self,
        worker_id: str,
        *,
        worker_timeout_seconds: int = 300,
    ):
        """Atomically claim the next available job using FOR UPDATE SKIP LOCKED."""
        from app.worker.models import RecoveryJob, JobStatus
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(seconds=worker_timeout_seconds)

        row = self._conn.fetchone(
            """
            UPDATE recovery_jobs
            SET locked_at = %(now)s, locked_by = %(worker_id)s
            WHERE job_id = (
                SELECT job_id FROM recovery_jobs
                WHERE status = 'PROCESSING'
                  AND locked_at IS NOT NULL
                  AND locked_at < %(stale_cutoff)s
                ORDER BY locked_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING job_id, recovery_item_id, status, attempt_count, max_attempts,
                      available_at, locked_at, locked_by, last_error, created_at,
                      completed_at, metadata
            """,
            {"now": now, "worker_id": worker_id, "stale_cutoff": stale_cutoff},
        )
        if row:
            return self._row_to_job(row)

        row = self._conn.fetchone(
            """
            UPDATE recovery_jobs
            SET status = 'PROCESSING',
                locked_at = %(now)s,
                locked_by = %(worker_id)s,
                attempt_count = attempt_count + 1
            WHERE job_id = (
                SELECT job_id FROM recovery_jobs
                WHERE status = 'QUEUED'
                  AND available_at <= %(now)s
                ORDER BY available_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING job_id, recovery_item_id, status, attempt_count, max_attempts,
                      available_at, locked_at, locked_by, last_error, created_at,
                      completed_at, metadata
            """,
            {"now": now, "worker_id": worker_id},
        )
        if not row:
            return None
        return self._row_to_job(row)

    def mark_completed(self, job_id: str) -> None:
        self._conn.execute(
            """
            UPDATE recovery_jobs
            SET status = 'COMPLETED', completed_at = now(), locked_at = NULL, locked_by = NULL
            WHERE job_id = %s
            """,
            (job_id,),
        )

    def mark_failed(
        self,
        job_id: str,
        error: str,
        *,
        retry_delay_seconds: int = 0,
    ) -> None:
        """Re-queue if retries remain, dead-letter otherwise."""
        self._conn.execute(
            """
            UPDATE recovery_jobs
            SET
                last_error = %(error)s,
                locked_at = NULL,
                locked_by = NULL,
                status = CASE
                    WHEN attempt_count >= max_attempts THEN 'DEAD_LETTER'
                    ELSE 'QUEUED'
                END,
                available_at = CASE
                    WHEN attempt_count >= max_attempts THEN available_at
                    ELSE now() + (%(delay)s || ' seconds')::interval
                END
            WHERE job_id = %(job_id)s
            """,
            {"job_id": job_id, "error": error, "delay": retry_delay_seconds},
        )

    def mark_dead_letter(self, job_id: str, reason: str) -> None:
        self._conn.execute(
            """
            UPDATE recovery_jobs
            SET status = 'DEAD_LETTER', last_error = %s, locked_at = NULL, locked_by = NULL
            WHERE job_id = %s
            """,
            (reason, job_id),
        )

    def get_job(self, job_id: str):
        row = self._conn.fetchone(
            """
            SELECT job_id, recovery_item_id, status, attempt_count, max_attempts,
                   available_at, locked_at, locked_by, last_error, created_at,
                   completed_at, metadata
            FROM recovery_jobs WHERE job_id = %s
            """,
            (job_id,),
        )
        if not row:
            return None
        return self._row_to_job(row)

    def list_jobs(self, status=None, limit: int = 50):
        if status is not None:
            status_val = status.value if hasattr(status, "value") else status
            rows = self._conn.fetchall(
                """
                SELECT job_id, recovery_item_id, status, attempt_count, max_attempts,
                       available_at, locked_at, locked_by, last_error, created_at,
                       completed_at, metadata
                FROM recovery_jobs WHERE status = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (status_val, limit),
            )
        else:
            rows = self._conn.fetchall(
                """
                SELECT job_id, recovery_item_id, status, attempt_count, max_attempts,
                       available_at, locked_at, locked_by, last_error, created_at,
                       completed_at, metadata
                FROM recovery_jobs
                ORDER BY created_at DESC LIMIT %s
                """,
                (limit,),
            )
        return [self._row_to_job(r) for r in rows]

    def get_job_for_item(self, recovery_item_id: str):
        row = self._conn.fetchone(
            """
            SELECT job_id, recovery_item_id, status, attempt_count, max_attempts,
                   available_at, locked_at, locked_by, last_error, created_at,
                   completed_at, metadata
            FROM recovery_jobs WHERE recovery_item_id = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (recovery_item_id,),
        )
        if not row:
            return None
        return self._row_to_job(row)

    def _row_to_job(self, row: dict):
        from app.worker.models import RecoveryJob, JobStatus
        return RecoveryJob(
            job_id=str(row["job_id"]),
            recovery_item_id=str(row["recovery_item_id"]),
            status=JobStatus(row["status"]),
            attempt_count=row["attempt_count"],
            max_attempts=row["max_attempts"],
            available_at=row["available_at"],
            locked_at=row.get("locked_at"),
            locked_by=row.get("locked_by"),
            last_error=row.get("last_error"),
            created_at=row["created_at"],
            completed_at=row.get("completed_at"),
            metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else json.loads(row.get("metadata", "{}")),
        )


class PostgresUserRepository:
    """PostgreSQL-backed user accounts repository."""

    def __init__(self, conn) -> None:
        self._conn = conn

    def create_user(self, email: str, password_hash: str, full_name: str) -> User:
        from app.domain.auth import User
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        row = self._conn.fetchone(
            """
            INSERT INTO users (id, email, password_hash, full_name, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, email, password_hash, full_name, created_at
            """,
            (user_id, email.lower().strip(), password_hash, full_name.strip(), now),
        )
        return User(
            id=str(row["id"]),
            email=row["email"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            created_at=row["created_at"],
        )

    def get_by_email(self, email: str) -> User | None:
        from app.domain.auth import User
        row = self._conn.fetchone(
            "SELECT id, email, password_hash, full_name, created_at FROM users WHERE LOWER(email) = %s",
            (email.lower().strip(),),
        )
        if not row:
            return None
        return User(
            id=str(row["id"]),
            email=row["email"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            created_at=row["created_at"],
        )

    def get_by_id(self, user_id: str) -> User | None:
        from app.domain.auth import User
        row = self._conn.fetchone(
            "SELECT id, email, password_hash, full_name, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        if not row:
            return None
        return User(
            id=str(row["id"]),
            email=row["email"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            created_at=row["created_at"],
        )


class PostgresSessionRepository:
    """PostgreSQL-backed user sessions repository."""

    def __init__(self, conn) -> None:
        self._conn = conn

    def create_session(self, user_id: str, *, expires_in_seconds: int = 86400 * 7) -> UserSession:
        from app.domain.auth import UserSession
        token = secrets.token_hex(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in_seconds)
        row = self._conn.fetchone(
            """
            INSERT INTO sessions (session_token, user_id, created_at, expires_at)
            VALUES (%s, %s, %s, %s)
            RETURNING session_token, user_id, created_at, expires_at
            """,
            (token, user_id, now, expires_at),
        )
        return UserSession(
            session_token=row["session_token"],
            user_id=str(row["user_id"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    def get_session(self, session_token: str) -> UserSession | None:
        from app.domain.auth import UserSession
        if not session_token:
            return None
        row = self._conn.fetchone(
            "SELECT session_token, user_id, created_at, expires_at FROM sessions WHERE session_token = %s",
            (session_token,),
        )
        if not row:
            return None
        expires_at = row["expires_at"]
        if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            self.delete_session(session_token)
            return None
        return UserSession(
            session_token=row["session_token"],
            user_id=str(row["user_id"]),
            created_at=row["created_at"],
            expires_at=expires_at,
        )

    def delete_session(self, session_token: str) -> None:
        if not session_token:
            return
        self._conn.execute(
            "DELETE FROM sessions WHERE session_token = %s",
            (session_token,),
        )
