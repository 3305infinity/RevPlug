-- Migration: 0001_init.sql
-- Initial schema for the Recovery Engine.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- recovery_items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recovery_items (
    id                          text PRIMARY KEY,
    source_type                 text NOT NULL,
    amount                      bigint NOT NULL CHECK (amount >= 0),
    currency                    text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    customer_id                 text NOT NULL,
    created_at                  timestamptz NOT NULL,
    status                      text NOT NULL,
    root_cause                  text,
    risk_score                  double precision,
    expected_recovery_value     bigint,
    metadata                    jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at                  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS recovery_items_status_idx
    ON recovery_items (status);

CREATE INDEX IF NOT EXISTS recovery_items_customer_id_idx
    ON recovery_items (customer_id);

-- ---------------------------------------------------------------------------
-- audit_log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_item_id text REFERENCES recovery_items(id) ON DELETE CASCADE,
    actor           text NOT NULL,
    action          text NOT NULL,
    reasoning       text,
    metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
    timestamp       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_log_recovery_item_id_idx
    ON audit_log (recovery_item_id);

CREATE INDEX IF NOT EXISTS audit_log_timestamp_idx
    ON audit_log (timestamp);

-- ---------------------------------------------------------------------------
-- idempotency_keys
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idempotency_keys (
    event_key       text PRIMARY KEY,
    processed_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- attempts
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attempts (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_item_id  text NOT NULL REFERENCES recovery_items(id) ON DELETE CASCADE,
    attempt_number    integer NOT NULL CHECK (attempt_number > 0),
    action            text NOT NULL,
    scheduled_at      timestamptz,
    executed_at       timestamptz,
    outcome           text,
    metadata          jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (recovery_item_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS attempts_recovery_item_id_idx
    ON attempts (recovery_item_id);

COMMIT;
