-- Migration 002: Password reset tokens
-- Run once: psql -U rdtii_user -d rdtii -f migrate_002_reset_tokens.sql

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP   NOT NULL,
    used       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prt_token   ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_prt_user_id ON password_reset_tokens(user_id);
