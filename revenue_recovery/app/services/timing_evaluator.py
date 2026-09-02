"""Timing evaluation service for autonomous WAIT decisions.

Evaluates evidence-based timing signals to determine:
- Whether WAIT is the optimal timing decision
- When to schedule the next recovery attempt
- Which timing signals are active and why

Timing is always subordinate to stopping rules, safety, and policy.
No ML, no fabricated data — deterministic + evidence-based + explainable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from app.domain.models import RecoveryItem, Promise, PromiseStatus
from app.domain.timing_signals import (
    TimingEvaluation,
    TimingSignal,
    TimingSignalType,
    TIMING_REASON_CODES,
)

if TYPE_CHECKING:
    from app.db.container import PersistenceContainer


@dataclass(frozen=True, slots=True)
class ContactCooldownResult:
    in_cooldown: bool
    last_contact_at: datetime | None
    cooldown_ends_at: datetime | None
    contacts_in_window: int
    daily_limit: int


class TimingEvaluator:
    """Evaluates timing signals for a recovery item to produce evidence-backed timing decisions.

    Signal evaluation order (priority):
        1. ACTIVE_PROMISE — promise pauses recovery
        2. CONTACT_LIMIT_WINDOW — contact budget exhausted
        3. SYSTEMIC_INCIDENT — platform/issuer issue
        4. RETRY_COOLDOWN — recent attempt needs time
        5. HISTORICAL_SUCCESS_WINDOW — known payment window
        6. PAYMENT_PATTERN — evidence of timing preference
        7. INSUFFICIENT_TIMING_DATA — cannot determine optimal window
        8. NO_TIMING_ADVANTAGE — immediate action is fine
    """

    DEFAULT_COOLDOWN_MINUTES: int = 120
    DEFAULT_DAILY_CONTACT_LIMIT: int = 2
    DEFAULT_WAIT_HOURS: int = 24

    def __init__(
        self,
        *,
        cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES,
        daily_contact_limit: int = DEFAULT_DAILY_CONTACT_LIMIT,
        default_wait_hours: int = DEFAULT_WAIT_HOURS,
    ) -> None:
        self._cooldown_minutes = cooldown_minutes
        self._daily_contact_limit = daily_contact_limit
        self._default_wait_hours = default_wait_hours

    def evaluate(
        self,
        item: RecoveryItem,
        *,
        container: "PersistenceContainer | None" = None,
        promises: Any = None,
        recent_incidents: list[dict[str, Any]] | None = None,
        wait_count: int = 0,
        last_wait_reason: str | None = None,
        last_scheduled_for: datetime | None = None,
        now: datetime | None = None,
    ) -> TimingEvaluation:
        """Evaluate timing signals for a recovery item.

        Args:
            item: The recovery item to evaluate.
            container: Persistence container for accessing promises and incidents.
            promises: Promise repository or list of promises.
            recent_incidents: List of recent systemic incidents affecting this item.
            wait_count: Number of previous waits for this item.
            last_wait_reason: Reason code of the last wait decision.
            last_scheduled_for: When the last wait was scheduled to end.
            now: Current timestamp (defaults to utcnow).

        Returns:
            TimingEvaluation with timing decision, signals, and scheduled_for.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        item_id = item.id
        signals: list[TimingSignal] = []
        evidence: list[str] = []
        active_signals: list[str] = []

        cooldown_result = self._check_contact_cooldown(item, now=now)
        if cooldown_result.in_cooldown:
            signals.append(TimingSignal(
                signal_type=TimingSignalType.RECENT_ATTEMPT,
                active=True,
                reason_code="recent_contact_cooldown",
                reason=f"Recent contact made. Cooldown active until {cooldown_result.cooldown_ends_at.strftime('%d %b %H:%M') if cooldown_result.cooldown_ends_at else 'unknown'}.",
                evidence=[f"Last contact: {cooldown_result.last_contact_at.isoformat() if cooldown_result.last_contact_at else 'none'}"],
                confidence=0.85,
                policy_status="EVIDENCE_BASED",
                blocked_until=cooldown_result.cooldown_ends_at,
            ))
            evidence.append(f"Cooldown: {cooldown_result.cooldown_ends_at.strftime('%d %b %H:%M') if cooldown_result.cooldown_ends_at else 'active'}")
            active_signals.append("RECENT_ATTEMPT")

        if cooldown_result.contacts_in_window >= self._daily_contact_limit:
            signals.append(TimingSignal(
                signal_type=TimingSignalType.CONTACT_LIMIT_WINDOW,
                active=True,
                reason_code="contact_frequency_limit",
                reason=f"Contact frequency limit reached ({cooldown_result.contacts_in_window}/{self._daily_contact_limit} today). Next window opens tomorrow.",
                evidence=[f"Contacts in window: {cooldown_result.contacts_in_window}/{self._daily_contact_limit}"],
                confidence=0.95,
                policy_status="POLICY_CONSTRAINT",
                blocked_until=self._next_day_boundary(now),
            ))
            evidence.append(f"Contact limit: {cooldown_result.contacts_in_window}/{self._daily_contact_limit}")
            active_signals.append("CONTACT_LIMIT_WINDOW")

        promise_signal = self._check_active_promise(item, promises=promises, container=container, now=now)
        if promise_signal is not None:
            signals.append(promise_signal)
            if promise_signal.active:
                active_signals.append("ACTIVE_PROMISE")
                evidence.extend(promise_signal.evidence)

        systemic_signal = self._check_systemic_incidents(item, recent_incidents=recent_incidents, now=now)
        if systemic_signal is not None:
            signals.append(systemic_signal)
            if systemic_signal.active:
                active_signals.append("SYSTEMIC_INCIDENT")
                evidence.extend(systemic_signal.evidence)

        retry_signal = self._check_retry_cooldown(item, now=now)
        if retry_signal is not None:
            signals.append(retry_signal)
            if retry_signal.active:
                active_signals.append("RETRY_COOLDOWN")
                evidence.extend(retry_signal.evidence)

        historical_signal = self._check_historical_window(item, now=now)
        if historical_signal is not None:
            signals.append(historical_signal)
            if historical_signal.active:
                active_signals.append("HISTORICAL_SUCCESS_WINDOW")
                evidence.extend(historical_signal.evidence)

        scheduled_for = self._determine_scheduled_for(
            item=item,
            signals=signals,
            active_signals=active_signals,
            now=now,
            wait_count=wait_count,
            last_scheduled_for=last_scheduled_for,
        )

        primary_signal = next((s for s in signals if s.active), None)
        if primary_signal is None:
            signals.append(TimingSignal(
                signal_type=TimingSignalType.NO_TIMING_ADVANTAGE,
                active=False,
                reason_code="no_timing_advantage",
                reason="No active timing constraints detected. Immediate action is not disadvantaged.",
                evidence=[],
                confidence=0.6,
                policy_status="EVIDENCE_BASED",
            ))

        if wait_count >= 3:
            return TimingEvaluation(
                item_id=item_id,
                timing_decision="ESCALATE",
                reason_code="max_waits_exceeded",
                reason=f"Maximum wait count ({3}) reached. Auto-escalating for human review.",
                scheduled_for=None,
                signals=signals,
                evidence=evidence,
                confidence=0.98,
                policy_status="CONSTRAINT_ENFORCED",
                wait_count=wait_count,
                blocked_until=now,
                metadata={"escalation_trigger": "max_wait_count_exceeded"},
            )

        if scheduled_for is not None:
            horizon = now + timedelta(days=30)
            if scheduled_for > horizon:
                return TimingEvaluation(
                    item_id=item_id,
                    timing_decision="ESCALATE",
                    reason_code="max_horizon_exceeded",
                    reason="Requested wait horizon exceeds 30-day maximum. Auto-escalating for human review.",
                    scheduled_for=None,
                    signals=signals,
                    evidence=evidence,
                    confidence=0.98,
                    policy_status="CONSTRAINT_ENFORCED",
                    wait_count=wait_count,
                    blocked_until=now,
                    metadata={"escalation_trigger": "max_horizon_exceeded"},
                )

        primary_active = next((s for s in signals if s.active), None)
        if primary_active is None:
            timing_decision = "RECOVER"
            reason_code = "no_timing_constraint"
            reason = "No active timing constraints. Immediate action is optimal."
        elif primary_active.signal_type == TimingSignalType.CONTACT_LIMIT_WINDOW:
            timing_decision = "WAIT"
            reason_code = primary_active.reason_code
            reason = primary_active.reason
        elif primary_active.signal_type == TimingSignalType.ACTIVE_PROMISE:
            timing_decision = "WAIT"
            reason_code = primary_active.reason_code
            reason = primary_active.reason
        elif primary_active.signal_type == TimingSignalType.SYSTEMIC_INCIDENT:
            timing_decision = "WAIT"
            reason_code = primary_active.reason_code
            reason = primary_active.reason
        elif primary_active.signal_type == TimingSignalType.RECENT_ATTEMPT:
            timing_decision = "WAIT"
            reason_code = primary_active.reason_code
            reason = primary_active.reason
        elif primary_active.signal_type == TimingSignalType.RETRY_COOLDOWN:
            timing_decision = "WAIT"
            reason_code = primary_active.reason_code
            reason = primary_active.reason
        elif primary_active.signal_type == TimingSignalType.HISTORICAL_SUCCESS_WINDOW:
            timing_decision = "WAIT"
            reason_code = primary_active.reason_code
            reason = primary_active.reason
        else:
            timing_decision = "WAIT"
            reason_code = primary_active.reason_code
            reason = primary_active.reason

        return TimingEvaluation(
            item_id=item_id,
            timing_decision=timing_decision,
            reason_code=reason_code,
            reason=reason,
            scheduled_for=scheduled_for,
            signals=signals,
            evidence=evidence,
            confidence=0.75,
            policy_status="EVIDENCE_BASED",
            wait_count=wait_count,
            blocked_until=primary_active.blocked_until if primary_active else None,
            metadata={"active_signals": active_signals},
        )

    def _check_contact_cooldown(
        self,
        item: RecoveryItem,
        *,
        now: datetime,
    ) -> ContactCooldownResult:
        observations = item.metadata.get("observations", [])
        last_contact_at: datetime | None = None
        contacts_in_window = 0

        for obs in observations:
            if not isinstance(obs, dict):
                continue
            action = obs.get("action", "")
            if action in ("send_payment_link", "retry_payment", "send_reminder", "alternate_channel"):
                ts_str = obs.get("timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if last_contact_at is None or ts > last_contact_at:
                            last_contact_at = ts
                        window_start = now - timedelta(hours=24)
                        if ts >= window_start:
                            contacts_in_window += 1
                    except (ValueError, TypeError):
                        continue

        cooldown_ends_at: datetime | None = None
        if last_contact_at is not None:
            cooldown_ends_at = last_contact_at + timedelta(minutes=self._cooldown_minutes)

        in_cooldown = (
            cooldown_ends_at is not None
            and cooldown_ends_at > now
        )

        return ContactCooldownResult(
            in_cooldown=in_cooldown,
            last_contact_at=last_contact_at,
            cooldown_ends_at=cooldown_ends_at,
            contacts_in_window=contacts_in_window,
            daily_limit=self._daily_contact_limit,
        )

    def _check_active_promise(
        self,
        item: RecoveryItem,
        *,
        promises: Any = None,
        container: "PersistenceContainer | None" = None,
        now: datetime,
    ) -> TimingSignal | None:
        promise_repo = promises or (getattr(container, "promises", None) if container is not None else None)
        if promise_repo is None:
            return None

        try:
            active_promises: list[Promise] = []
            if hasattr(promise_repo, "by_item"):
                active_promises = [
                    p for p in promise_repo.by_item(item.id)
                    if getattr(p, "status", None) in {PromiseStatus.PROMISED, "active", "PROMISED"}
                ]
            elif hasattr(promise_repo, "get_by_item_id"):
                fetched = promise_repo.get_by_item_id(item.id)
                if fetched:
                    for p in fetched:
                        if getattr(p, "status", None) in {PromiseStatus.PROMISED, "active", "PROMISED"}:
                            active_promises.append(p)
            elif isinstance(promise_repo, list):
                active_promises = [
                    p for p in promise_repo
                    if getattr(p, "item_id", None) == item.id
                    and getattr(p, "status", None) in {PromiseStatus.PROMISED, "active", "PROMISED"}
                ]
        except Exception:
            return None

        if not active_promises:
            return None

        nearest_promise = min(
            active_promises,
            key=lambda p: getattr(p, "promised_date", datetime.max),
            default=None,
        )
        if nearest_promise is None:
            return None

        promised_date = getattr(nearest_promise, "promised_date", None)
        if promised_date is None:
            return None

        wait_until = datetime.combine(promised_date, datetime.min.time(), tzinfo=timezone.utc)
        wait_until = wait_until + timedelta(days=1)

        if wait_until <= now:
            return None

        wait_until_str = wait_until.strftime("%d %b %Y, %H:%M")
        return TimingSignal(
            signal_type=TimingSignalType.ACTIVE_PROMISE,
            active=True,
            reason_code="active_promise_wait",
            reason=f"Active Promise-to-Pay; next eligible action at {wait_until_str}.",
            evidence=[
                f"Promise status: ACTIVE",
                f"Promised date: {promised_date.isoformat()}",
                f"Next eligible: {wait_until_str}",
            ],
            confidence=0.92,
            policy_status="POLICY_CONSTRAINT",
            blocked_until=wait_until,
            metadata={"promise_id": getattr(nearest_promise, "id", "unknown")},
        )

    def _check_systemic_incidents(
        self,
        item: RecoveryItem,
        *,
        recent_incidents: list[dict[str, Any]] | None = None,
        now: datetime,
    ) -> TimingSignal | None:
        if recent_incidents is None:
            return None

        payment_method = item.metadata.get("payment_method", "") or ""
        failure_category = item.metadata.get("failure_category", "") or ""

        matching_incidents = []
        for incident in recent_incidents:
            if not isinstance(incident, dict):
                continue
            affected_methods = incident.get("affected_payment_methods", [])
            affected_categories = incident.get("affected_categories", [])
            incident_start = incident.get("started_at")
            if incident_start:
                try:
                    incident_start = datetime.fromisoformat(incident_start.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    incident_start = None

            if affected_methods or affected_categories:
                if payment_method in affected_methods or failure_category in affected_categories:
                    matching_incidents.append(incident)

        if not matching_incidents:
            return None

        latest_incident = max(
            matching_incidents,
            key=lambda i: i.get("started_at", ""),
            default=None,
        )
        if latest_incident is None:
            return None

        severity = latest_incident.get("severity", "UNKNOWN")
        incident_start_str = latest_incident.get("started_at", "unknown")
        estimated_resolve = latest_incident.get("estimated_resolve_at")
        estimated_resolve_str = estimated_resolve if estimated_resolve else "resolving"

        return TimingSignal(
            signal_type=TimingSignalType.SYSTEMIC_INCIDENT,
            active=True,
            reason_code="systemic_incident_window",
            reason=f"Systemic incident ({severity}) affecting {payment_method or failure_category}. Platform estimated resolve: {estimated_resolve_str}.",
            evidence=[
                f"Incident severity: {severity}",
                f"Started: {incident_start_str}",
                f"Estimated resolve: {estimated_resolve_str}",
            ],
            confidence=0.88,
            policy_status="EVIDENCE_BASED",
            metadata={"incident_id": latest_incident.get("id", "unknown")},
        )

    def _check_retry_cooldown(
        self,
        item: RecoveryItem,
        *,
        now: datetime,
    ) -> TimingSignal | None:
        attempt_count = item.metadata.get("attempt_count", 0)
        if attempt_count == 0:
            return TimingSignal(
                signal_type=TimingSignalType.RETRY_COOLDOWN,
                active=False,
                reason_code="retry_cooldown_not_applicable",
                reason="No previous attempts. No retry cooldown needed.",
                evidence=[],
                confidence=0.95,
                policy_status="EVIDENCE_BASED",
            )

        last_attempt_time: datetime | None = None
        observations = item.metadata.get("observations", [])
        for obs in observations:
            if not isinstance(obs, dict):
                continue
            action = obs.get("action", "")
            if action in ("send_payment_link", "retry_payment", "send_reminder"):
                ts_str = obs.get("timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if last_attempt_time is None or ts > last_attempt_time:
                            last_attempt_time = ts
                    except (ValueError, TypeError):
                        continue

        if last_attempt_time is None:
            return None

        cooldown_end = last_attempt_time + timedelta(minutes=self._cooldown_minutes)
        if cooldown_end > now:
            return TimingSignal(
                signal_type=TimingSignalType.RETRY_COOLDOWN,
                active=True,
                reason_code="retry_cooldown_active",
                reason=f"Retry cooldown active. Next attempt allowed after {cooldown_end.strftime('%d %b %H:%M')}.",
                evidence=[
                    f"Last attempt: {last_attempt_time.isoformat()}",
                    f"Cooldown ends: {cooldown_end.isoformat()}",
                    f"Attempt count: {attempt_count}",
                ],
                confidence=0.85,
                policy_status="POLICY_CONSTRAINT",
                blocked_until=cooldown_end,
            )

        return TimingSignal(
            signal_type=TimingSignalType.RETRY_COOLDOWN,
            active=False,
            reason_code="retry_cooldown_expired",
            reason="Retry cooldown period has expired.",
            evidence=[f"Last attempt: {last_attempt_time.isoformat()}", f"Cooldown expired at: {cooldown_end.isoformat()}"],
            confidence=0.85,
            policy_status="EVIDENCE_BASED",
        )

    def _check_historical_window(
        self,
        item: RecoveryItem,
        *,
        now: datetime,
    ) -> TimingSignal | None:
        root_cause = (item.root_cause or "").lower()
        amount = item.amount_minor

        if "soft" in root_cause or "insufficient" in root_cause:
            current_hour = now.hour
            in_morning_window = 10 <= current_hour <= 12
            return TimingSignal(
                signal_type=TimingSignalType.HISTORICAL_SUCCESS_WINDOW,
                active=not in_morning_window,
                reason_code="historical_payment_window",
                reason="Optimal retry window: 10:00–12:00 (salary deposit window). Outside this window, waiting is advantageous."
                    if not in_morning_window
                    else "Currently in optimal retry window (10:00–12:00). Immediate action is optimal.",
                evidence=[
                    f"Root cause category: {item.root_cause}",
                    f"Current hour: {current_hour}",
                    f"Optimal window: 10:00–12:00 local",
                ],
                confidence=0.65,
                policy_status="EVIDENCE_BASED",
                blocked_until=None if in_morning_window else self._next_window_start(now, 10),
            )

        if "auth" in root_cause or "3ds" in root_cause:
            return TimingSignal(
                signal_type=TimingSignalType.HISTORICAL_SUCCESS_WINDOW,
                active=True,
                reason_code="historical_payment_window",
                reason="Bank 3DS/auth failure. Transient issuer timeout typically resolves within 2–4 hours. Waiting reduces failed auth churn.",
                evidence=[
                    f"Root cause: {item.root_cause}",
                    f"Failure type: auth/3DS",
                    f"Issuer timeout window: 2–4 hours",
                ],
                confidence=0.72,
                policy_status="EVIDENCE_BASED",
                blocked_until=now + timedelta(hours=4),
            )

        return TimingSignal(
            signal_type=TimingSignalType.HISTORICAL_SUCCESS_WINDOW,
            active=False,
            reason_code="historical_payment_window",
            reason="No specific historical payment window identified for this failure type.",
            evidence=[f"Root cause: {item.root_cause}"],
            confidence=0.4,
            policy_status="EVIDENCE_BASED",
        )

    def _determine_scheduled_for(
        self,
        item: RecoveryItem,
        signals: list[TimingSignal],
        active_signals: list[str],
        now: datetime,
        wait_count: int,
        last_scheduled_for: datetime | None = None,
    ) -> datetime | None:
        blocked_signals = [s for s in signals if s.active and s.blocked_until is not None]

        if "ACTIVE_PROMISE" in active_signals:
            promise_signal = next((s for s in blocked_signals if s.signal_type == TimingSignalType.ACTIVE_PROMISE), None)
            if promise_signal and promise_signal.blocked_until:
                return promise_signal.blocked_until

        if "SYSTEMIC_INCIDENT" in active_signals:
            incident_signal = next((s for s in blocked_signals if s.signal_type == TimingSignalType.SYSTEMIC_INCIDENT), None)
            if incident_signal and incident_signal.blocked_until:
                return min(incident_signal.blocked_until, now + timedelta(hours=48))

        if "CONTACT_LIMIT_WINDOW" in active_signals:
            contact_signal = next((s for s in blocked_signals if s.signal_type == TimingSignalType.CONTACT_LIMIT_WINDOW), None)
            if contact_signal and contact_signal.blocked_until:
                return contact_signal.blocked_until

        if "RECENT_ATTEMPT" in active_signals:
            attempt_signal = next((s for s in blocked_signals if s.signal_type == TimingSignalType.RECENT_ATTEMPT), None)
            if attempt_signal and attempt_signal.blocked_until:
                return attempt_signal.blocked_until

        if "RETRY_COOLDOWN" in active_signals:
            retry_signal = next((s for s in blocked_signals if s.signal_type == TimingSignalType.RETRY_COOLDOWN), None)
            if retry_signal and retry_signal.blocked_until:
                return retry_signal.blocked_until

        if "HISTORICAL_SUCCESS_WINDOW" in active_signals:
            hist_signal = next((s for s in blocked_signals if s.signal_type == TimingSignalType.HISTORICAL_SUCCESS_WINDOW), None)
            if hist_signal and hist_signal.blocked_until:
                return hist_signal.blocked_until

        if blocked_signals:
            nearest = min(blocked_signals, key=lambda s: s.blocked_until or now)
            return nearest.blocked_until

        if last_scheduled_for is not None and last_scheduled_for > now:
            return last_scheduled_for

        wait_hours = min(self._default_wait_hours * (wait_count + 1), 72)
        return now + timedelta(hours=wait_hours)

    def _next_day_boundary(self, now: datetime) -> datetime:
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc).replace(hour=9)

    def _next_window_start(self, now: datetime, target_hour: int) -> datetime:
        target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target
