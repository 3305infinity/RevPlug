-- Migration: 0002_recovery_decisions.sql
-- Adds a table for persisting agent proposals and decisions.

BEGIN;

CREATE TABLE IF NOT EXISTS recovery_decisions (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_item_id    text REFERENCES recovery_items(id) ON DELETE CASCADE,
    agent_name          text NOT NULL,
    model_name          text NOT NULL DEFAULT 'mock',
    proposed_action     text NOT NULL,
    reason              text NOT NULL,
    confidence          double precision NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    customer_message    text,
    proposed_retry      boolean NOT NULL DEFAULT FALSE,
    retry_metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
    evidence            jsonb NOT NULL DEFAULT '{}'::jsonb,
    policy_allowed      boolean,
    policy_rule         text,
    final_action        text,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS recovery_decisions_recovery_item_id_idx
    ON recovery_decisions (recovery_item_id);

CREATE INDEX IF NOT EXISTS recovery_decisions_created_at_idx
    ON recovery_decisions (created_at);

COMMIT;
