from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable

from app.audit.models import AuditEvent
from app.db.session import PostgresConnection
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryProposal
from app.idempotency.store import IdempotencyStore
from app.ledger.attempts import AttemptLedger, AttemptRecord


class PostgresRecoveryItemRepository:
    """PostgreSQL-backed RecoveryItem repository."""

    def __init__(self, conn: PostgresConnection) -> None:
        self._conn = conn

    def save(self, item: RecoveryItem) -> None:
        self._conn.execute(
            """
            INSERT INTO recovery_items
                (id, source_type, amount, currency, customer_id, created_at,
                 status, root_cause, risk_score, expected_recovery_value,
                 metadata, updated_at)
            VALUES (%(id)s, %(source_type)s, %(amount)s, %(currency)s,
                    %(customer_id)s, %(created_at)s, %(status)s, %(root_cause)s,
                    %(risk_score)s, %(expected_recovery_value)s, %(metadata)s,
                    now())
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                root_cause = EXCLUDED.root_cause,
                risk_score = EXCLUDED.risk_score,
                expected_recovery_value = EXCLUDED.expected_recovery_value,
                metadata = EXCLUDED.metadata,
                updated_at = now()
            """,
            {
                "id": item.id,
                "source_type": item.source_type.value,
                "amount": item.amount_minor,
                "currency": item.currency,
                "customer_id": item.customer_id,
                "created_at": item.created_at,
                "status": item.status.value,
                "root_cause": item.root_cause,
                "risk_score": item.recovery_probability,
                "expected_recovery_value": item.expected_recovery_value,
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
            id=row["id"],
            source_type=SourceType(row["source_type"]),
            external_id=row["id"],
            customer_id=row["customer_id"],
            amount_minor=row["amount"],
            currency=row["currency"],
            created_at=row["created_at"],
            status=RecoveryStatus(row["status"]),
            root_cause=row["root_cause"],
            recovery_probability=row["risk_score"],
            expected_recovery_value=row["expected_recovery_value"],
            metadata=row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"]),
        )

    def update_status(self, item_id: str, status: RecoveryStatus) -> None:
        self._conn.execute(
            "UPDATE recovery_items SET status = %s, updated_at = now() WHERE id = %s",
            (status.value, item_id),
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
            # UNIQUE violation means already processed; treat as idempotent success.
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
    ) -> AuditEvent:
        row = self._conn.fetchone(
            """
            INSERT INTO audit_log (recovery_item_id, actor, action, reasoning, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, recovery_item_id, actor, action, reasoning, metadata, timestamp
            """,
            (recovery_item_id, actor, action, reason, json.dumps(metadata or {})),
        )
        return AuditEvent(
            id=str(row["id"]),
            recovery_item_id=row["recovery_item_id"] or "",
            actor=row["actor"],
            action=row["action"],
            reason=row["reasoning"],
            metadata=row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"]),
            timestamp=row["timestamp"],
        )

    def events_for(self, recovery_item_id: str) -> list[AuditEvent]:
        rows = self._conn.fetchall(
            "SELECT * FROM audit_log WHERE recovery_item_id = %s ORDER BY timestamp",
            (recovery_item_id,),
        )
        return [
            AuditEvent(
                id=str(r["id"]),
                recovery_item_id=r["recovery_item_id"],
                actor=r["actor"],
                action=r["action"],
                reason=r["reasoning"],
                metadata=r["metadata"] if isinstance(r["metadata"], dict) else json.loads(r["metadata"]),
                timestamp=r["timestamp"],
            )
            for r in rows
        ]


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
                recovery_item_id=r["recovery_item_id"],
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
        return [dict(r) for r in rows]
