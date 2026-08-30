-- Migration: 0008_users_auth.sql
-- User accounts and session persistence for RecoverOS authentication.

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id            uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    email         text            NOT NULL UNIQUE,
    password_hash text            NOT NULL,
    full_name     text            NOT NULL,
    created_at    timestamptz     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS users_email_idx ON users (email);

CREATE TABLE IF NOT EXISTS sessions (
    session_token text            PRIMARY KEY,
    user_id       uuid            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    timestamptz     NOT NULL DEFAULT now(),
    expires_at    timestamptz     NOT NULL
);

CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions (user_id);
CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions (expires_at);

COMMIT;
