-- Migration: 0005_recovery_jobs.sql
-- Creates the recovery_jobs table for async worker queue with safe concurrent claiming.
--
-- Design principles:
--   - FOR UPDATE SKIP LOCKED enables multiple workers without locking conflicts
--   - locked_at + worker_timeout enables crash recovery (stale PROCESSING jobs)
--   - status transitions: QUEUED → PROCESSING → COMPLETED | FAILED → DEAD_LETTER
--   - attempt_count tracks retry attempts; jobs exceeding max_attempts go to DEAD_LETTER
--   - available_at supports delayed retry (exponential back-off)

BEGIN;

CREATE TABLE IF NOT EXISTS recovery_jobs (
    job_id              uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_item_id    text            NOT NULL REFERENCES recovery_items(id) ON DELETE CASCADE,
    status              text            NOT NULL DEFAULT 'QUEUED'
                            CHECK (status IN ('QUEUED','PROCESSING','COMPLETED','FAILED','DEAD_LETTER')),
    attempt_count       integer         NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts        integer         NOT NULL DEFAULT 3  CHECK (max_attempts >= 1),
    available_at        timestamptz     NOT NULL DEFAULT now(),
    locked_at           timestamptz,
    locked_by           text,
    last_error          text,
    created_at          timestamptz     NOT NULL DEFAULT now(),
    completed_at        timestamptz,
    metadata            jsonb           NOT NULL DEFAULT '{}'::jsonb
);

-- Efficient polling: workers scan for QUEUED jobs that are available now
CREATE INDEX IF NOT EXISTS recovery_jobs_status_available_idx
    ON recovery_jobs (status, available_at)
    WHERE status IN ('QUEUED', 'PROCESSING');

-- Look up by recovery_item_id (e.g. to prevent double-queuing)
CREATE INDEX IF NOT EXISTS recovery_jobs_recovery_item_id_idx
    ON recovery_jobs (recovery_item_id);

-- Worker reclaim index: find stale PROCESSING jobs
CREATE INDEX IF NOT EXISTS recovery_jobs_locked_at_idx
    ON recovery_jobs (locked_at)
    WHERE status = 'PROCESSING';

-- Enforce that each recovery_item has at most one active (non-terminal) job at a time.
-- This prevents double-queuing on concurrent duplicate webhooks that slip past
-- the provider_events uniqueness constraint.
CREATE UNIQUE INDEX IF NOT EXISTS recovery_jobs_one_active_per_item_idx
    ON recovery_jobs (recovery_item_id)
    WHERE status IN ('QUEUED', 'PROCESSING');

COMMENT ON TABLE recovery_jobs IS
    'Durable async job queue for recovery worker. Workers claim jobs with FOR UPDATE SKIP LOCKED. '
    'Stale PROCESSING jobs (locked_at + timeout < now) can be reclaimed after worker crash.';

COMMENT ON COLUMN recovery_jobs.locked_by IS
    'Opaque worker identifier (e.g. hostname + PID). Used for crash-detection diagnostics only.';

COMMENT ON COLUMN recovery_jobs.available_at IS
    'Earliest time a worker may claim this job. Used for delayed retry back-off.';

COMMIT;
