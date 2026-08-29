-- Migration: 0006_recovery_batches.sql
-- Adds recovery_batches table and batch_id FK to recovery_items.
--
-- Design: batch metrics are NEVER stored as duplicates of financial truth.
-- actual_recovered, recovered_count etc. are derived by joining recovery_outcomes
-- at query time; we only store batch-level metadata here.

BEGIN;

CREATE TABLE IF NOT EXISTS recovery_batches (
    batch_id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    text        NOT NULL,
    dataset_label           text        NOT NULL DEFAULT 'custom',
    is_synthetic            boolean     NOT NULL DEFAULT false,
    status                  text        NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','processing','completed','failed')),
    total_items             integer     NOT NULL DEFAULT 0  CHECK (total_items >= 0),
    total_amount_at_risk    bigint      NOT NULL DEFAULT 0  CHECK (total_amount_at_risk >= 0),
    expected_recovery       bigint      NOT NULL DEFAULT 0  CHECK (expected_recovery >= 0),
    created_at              timestamptz NOT NULL DEFAULT now(),
    completed_at            timestamptz,
    metadata                jsonb       NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE recovery_batches IS
    'Batch recovery runs. Metrics (actual_recovered, counts) are derived from '
    'recovery_outcomes + recovery_items at query time to avoid financial truth duplication.';

CREATE INDEX IF NOT EXISTS recovery_batches_status_idx
    ON recovery_batches (status);

CREATE INDEX IF NOT EXISTS recovery_batches_created_at_idx
    ON recovery_batches (created_at DESC);

-- Add batch_id FK to recovery_items
ALTER TABLE recovery_items
    ADD COLUMN IF NOT EXISTS batch_id uuid REFERENCES recovery_batches(batch_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS recovery_items_batch_id_idx
    ON recovery_items (batch_id)
    WHERE batch_id IS NOT NULL;

COMMIT;
