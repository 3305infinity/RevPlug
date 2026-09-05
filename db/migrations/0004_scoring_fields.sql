-- Migration: 0004_scoring_fields.sql
-- Adds expected-value scoring fields to recovery_items.

BEGIN;

ALTER TABLE recovery_items
    ADD COLUMN IF NOT EXISTS intervention_cost bigint CHECK (intervention_cost IS NULL OR intervention_cost >= 0),
    ADD COLUMN IF NOT EXISTS score_version text,
    ADD COLUMN IF NOT EXISTS scoring_reason text,
    ADD COLUMN IF NOT EXISTS priority text CHECK (priority IS NULL OR priority IN ('CRITICAL','HIGH','MEDIUM','LOW'));

CREATE INDEX IF NOT EXISTS recovery_items_priority_idx
    ON recovery_items (priority);

CREATE INDEX IF NOT EXISTS recovery_items_expected_recovery_value_idx
    ON recovery_items (expected_recovery_value);

COMMIT;
