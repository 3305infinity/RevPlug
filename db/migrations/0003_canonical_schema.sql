-- Migration: 0003_canonical_schema.sql
-- Adds canonical fields and tables for the unified recovery domain.

BEGIN;

-- ---------------------------------------------------------------------------
-- Extend recovery_items with canonical fields
-- ---------------------------------------------------------------------------
ALTER TABLE recovery_items
    ADD COLUMN IF NOT EXISTS external_id text,
    ADD COLUMN IF NOT EXISTS failure_category text CHECK (failure_category IN ('soft','hard','fraud','authentication_required','unknown','receivable','mandate')),
    ADD COLUMN IF NOT EXISTS provider text,
    ADD COLUMN IF NOT EXISTS provider_event_id text,
    ADD COLUMN IF NOT EXISTS actual_recovery_value bigint CHECK (actual_recovery_value IS NULL OR actual_recovery_value >= 0),
    ADD COLUMN IF NOT EXISTS recovery_status text CHECK (recovery_status IS NULL OR recovery_status IN ('recovered','partially_recovered','failed','stopped','escalated','expired')),
    ADD COLUMN IF NOT EXISTS due_at timestamptz;

CREATE INDEX IF NOT EXISTS recovery_items_external_id_idx
    ON recovery_items (external_id);

CREATE INDEX IF NOT EXISTS recovery_items_provider_event_id_idx
    ON recovery_items (provider, provider_event_id);

CREATE INDEX IF NOT EXISTS recovery_items_failure_category_idx
    ON recovery_items (failure_category);

CREATE INDEX IF NOT EXISTS recovery_items_recovery_status_idx
    ON recovery_items (recovery_status);

-- ---------------------------------------------------------------------------
-- Extend attempts with execution details
-- ---------------------------------------------------------------------------
ALTER TABLE attempts
    ADD COLUMN IF NOT EXISTS intervention_type text,
    ADD COLUMN IF NOT EXISTS started_at timestamptz,
    ADD COLUMN IF NOT EXISTS completed_at timestamptz,
    ADD COLUMN IF NOT EXISTS execution_status text,
    ADD COLUMN IF NOT EXISTS provider_response_status text,
    ADD COLUMN IF NOT EXISTS error_code text,
    ADD COLUMN IF NOT EXISTS error_message text,
    ADD COLUMN IF NOT EXISTS cost_minor bigint CHECK (cost_minor IS NULL OR cost_minor >= 0),
    ADD COLUMN IF NOT EXISTS resulting_state text;

-- ---------------------------------------------------------------------------
-- recovery_outcomes: authoritative financial outcome record
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recovery_outcomes (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_item_id        text NOT NULL UNIQUE REFERENCES recovery_items(id) ON DELETE CASCADE,
    outcome_type            text NOT NULL CHECK (outcome_type IN ('recovered','partially_recovered','failed','stopped','escalated','expired')),
    expected_recovery_minor bigint NOT NULL CHECK (expected_recovery_minor >= 0),
    actual_recovery_minor   bigint CHECK (actual_recovery_minor IS NULL OR actual_recovery_minor >= 0),
    recovery_cost_minor     bigint NOT NULL DEFAULT 0 CHECK (recovery_cost_minor >= 0),
    net_recovery_minor      bigint GENERATED ALWAYS AS (COALESCE(actual_recovery_minor, 0) - recovery_cost_minor) STORED,
    recovered_at            timestamptz,
    created_at              timestamptz NOT NULL DEFAULT now(),
    metadata                jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS recovery_outcomes_recovery_item_id_idx
    ON recovery_outcomes (recovery_item_id);

CREATE INDEX IF NOT EXISTS recovery_outcomes_outcome_type_idx
    ON recovery_outcomes (outcome_type);

-- ---------------------------------------------------------------------------
-- promises: promise-to-pay support
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS promises (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_item_id        text NOT NULL REFERENCES recovery_items(id) ON DELETE CASCADE,
    customer_id             text NOT NULL,
    promised_amount_minor   bigint NOT NULL CHECK (promised_amount_minor >= 0),
    promised_date           date NOT NULL,
    status                  text NOT NULL DEFAULT 'promised' CHECK (status IN ('promised','fulfilled','broken','expired','cancelled')),
    created_at              timestamptz NOT NULL DEFAULT now(),
    fulfilled_at            timestamptz,
    expired_at              timestamptz,
    metadata                jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS promises_recovery_item_id_idx
    ON promises (recovery_item_id);

CREATE INDEX IF NOT EXISTS promises_customer_id_idx
    ON promises (customer_id);

CREATE INDEX IF NOT EXISTS promises_status_idx
    ON promises (status);

-- ---------------------------------------------------------------------------
-- provider_events: raw ingestion with durable uniqueness
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provider_events (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider            text NOT NULL,
    provider_event_id   text NOT NULL,
    received_at         timestamptz NOT NULL DEFAULT now(),
    event_type          text NOT NULL,
    raw_payload         jsonb NOT NULL,
    processing_status   text NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending','processed','failed','duplicate')),
    processed_at        timestamptz,
    recovery_item_id    text REFERENCES recovery_items(id) ON DELETE SET NULL,
    error_message       text,
    metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, provider_event_id)
);

CREATE INDEX IF NOT EXISTS provider_events_provider_event_id_idx
    ON provider_events (provider, provider_event_id);

CREATE INDEX IF NOT EXISTS provider_events_recovery_item_id_idx
    ON provider_events (recovery_item_id);

CREATE INDEX IF NOT EXISTS provider_events_processing_status_idx
    ON provider_events (processing_status);

-- ---------------------------------------------------------------------------
-- audit_log: make append-only via trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only; UPDATE and DELETE are not allowed';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log;
CREATE TRIGGER audit_log_append_only
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- ---------------------------------------------------------------------------
-- recovery_items: prevent direct DELETE (use status transition instead)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_recovery_item_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'recovery_items must not be deleted; transition to stopped instead';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS recovery_items_no_delete ON recovery_items;
CREATE TRIGGER recovery_items_no_delete
    BEFORE DELETE ON recovery_items
    FOR EACH ROW EXECUTE FUNCTION prevent_recovery_item_delete();

COMMIT;
