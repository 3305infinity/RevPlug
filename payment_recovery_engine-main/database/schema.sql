BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS webhook_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL CHECK (provider <> ''),
    provider_event_id text NOT NULL CHECK (provider_event_id <> ''),
    event_type text NOT NULL CHECK (event_type <> ''),
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    received_at timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz,
    processing_status text NOT NULL DEFAULT 'received'
        CHECK (processing_status IN ('received', 'processed', 'rejected', 'failed')),
    error_message text,
    UNIQUE (provider, provider_event_id)
);

CREATE TABLE IF NOT EXISTS recovery_cases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL DEFAULT 'stripe',
    provider_payment_intent_id text NOT NULL CHECK (provider_payment_intent_id <> ''),
    provider_customer_id text,
    customer_email text,
    amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
    currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    failure_category text NOT NULL CHECK (failure_category IN (
        'insufficient_funds', 'invalid_payment_method', 'authentication_required',
        'security_or_fraud', 'temporary_processing', 'hard_decline', 'unknown'
    )),
    provider_failure_code text NOT NULL,
    status text NOT NULL CHECK (status IN (
        'pending', 'attempting', 'action_required', 'manual_review', 'recovered', 'exhausted', 'cancelled'
    )),
    attempts_completed integer NOT NULL DEFAULT 0 CHECK (attempts_completed >= 0),
    max_attempts integer NOT NULL CHECK (max_attempts >= 0),
    next_retry_at timestamptz,
    policy_version text NOT NULL,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    lease_owner text,
    lease_expires_at timestamptz,
    recovered_at timestamptz,
    cancelled_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_payment_intent_id),
    CHECK (attempts_completed <= max_attempts),
    CHECK ((status IN ('recovered', 'cancelled', 'action_required', 'exhausted', 'manual_review') AND next_retry_at IS NULL)
        OR status IN ('pending', 'attempting')),
    CHECK ((status = 'recovered') = (recovered_at IS NOT NULL)),
    CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS recovery_cases_due_idx
    ON recovery_cases (next_retry_at)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS recovery_cases_expired_lease_idx
    ON recovery_cases (lease_expires_at)
    WHERE status = 'attempting';

CREATE TABLE IF NOT EXISTS retry_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_case_id uuid NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
    attempt_number integer NOT NULL CHECK (attempt_number > 0),
    provider_idempotency_key text NOT NULL CHECK (provider_idempotency_key <> ''),
    status text NOT NULL CHECK (status IN ('claimed', 'succeeded', 'failed', 'cancelled')),
    provider_error_code text,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    UNIQUE (recovery_case_id, attempt_number),
    UNIQUE (provider_idempotency_key)
);

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_case_id uuid NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
    notification_kind text NOT NULL CHECK (notification_kind <> ''),
    delivery_status text NOT NULL DEFAULT 'claimed'
        CHECK (delivery_status IN ('claimed', 'sent', 'failed', 'suppressed')),
    provider_message_id text,
    claimed_at timestamptz NOT NULL DEFAULT now(),
    sent_at timestamptz,
    UNIQUE (recovery_case_id, notification_kind)
);

CREATE TABLE IF NOT EXISTS recovery_transitions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_case_id uuid NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
    provider_event_id text NOT NULL,
    from_status text,
    to_status text NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (recovery_case_id, provider_event_id)
);

CREATE OR REPLACE FUNCTION claim_due_retries(
    p_worker_id text,
    p_limit integer DEFAULT 100,
    p_lease_seconds integer DEFAULT 300
)
RETURNS SETOF recovery_cases
LANGUAGE sql
AS $$
    WITH due AS (
        SELECT id
        FROM recovery_cases
        WHERE (status = 'pending' OR (status = 'attempting' AND lease_expires_at < now()))
          AND next_retry_at <= now()
          AND attempts_completed < max_attempts
        ORDER BY next_retry_at, id
        FOR UPDATE SKIP LOCKED
        LIMIT GREATEST(0, LEAST(p_limit, 1000))
    )
    UPDATE recovery_cases AS recovery
       SET status = 'attempting',
           lease_owner = p_worker_id,
           lease_expires_at = now() + make_interval(secs => GREATEST(1, p_lease_seconds)),
           version = recovery.version + 1,
           updated_at = now()
      FROM due
     WHERE recovery.id = due.id
    RETURNING recovery.*;
$$;

CREATE OR REPLACE FUNCTION mark_recovery_terminal(
    p_case_id uuid,
    p_expected_version integer,
    p_status text
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_status NOT IN ('recovered', 'cancelled') THEN
        RAISE EXCEPTION 'invalid terminal status: %', p_status;
    END IF;

    UPDATE recovery_cases
       SET status = p_status,
           next_retry_at = NULL,
           lease_owner = NULL,
           lease_expires_at = NULL,
           recovered_at = CASE WHEN p_status = 'recovered' THEN now() ELSE NULL END,
           cancelled_at = CASE WHEN p_status = 'cancelled' THEN now() ELSE NULL END,
           version = version + 1,
           updated_at = now()
     WHERE id = p_case_id
       AND version = p_expected_version
       AND status NOT IN ('recovered', 'cancelled');
    RETURN FOUND;
END;
$$;

COMMIT;
