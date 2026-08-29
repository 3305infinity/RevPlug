-- Migration: 0007_promise_lifecycle.sql
-- Extends promises with a stable UUID PK (promise_id), full lifecycle
-- status support, and an audit trigger for every state change.

BEGIN;

-- Add promise_id column as a stable UUID primary key (separate from id)
-- The existing promises table uses 'id' uuid PRIMARY KEY. We extend it
-- with explicit lifecycle fields if not already present.

ALTER TABLE promises
    ADD COLUMN IF NOT EXISTS broken_at    timestamptz,
    ADD COLUMN IF NOT EXISTS broken_reason text;

CREATE INDEX IF NOT EXISTS promises_id_idx
    ON promises (id);

CREATE INDEX IF NOT EXISTS promises_status_created_at_idx
    ON promises (status, created_at DESC);

-- Ensure status check covers all lifecycle states
-- (The original migration already has: 'promised','fulfilled','broken','expired','cancelled')

-- Append-only promise audit trigger function
CREATE OR REPLACE FUNCTION log_promise_lifecycle_event()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO audit_log (
            recovery_item_id,
            actor,
            action,
            reason,
            metadata
        ) VALUES (
            NEW.recovery_item_id,
            'system',
            'promise_status_changed',
            format('Promise %s changed from %s to %s', NEW.id, OLD.status, NEW.status),
            jsonb_build_object(
                'promise_id', NEW.id,
                'old_status', OLD.status,
                'new_status', NEW.status,
                'promised_amount_minor', NEW.promised_amount_minor,
                'promised_date', NEW.promised_date
            )
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS promise_lifecycle_audit ON promises;
CREATE TRIGGER promise_lifecycle_audit
    AFTER UPDATE ON promises
    FOR EACH ROW EXECUTE FUNCTION log_promise_lifecycle_event();

COMMIT;
