-- Migration 001: Add auth fields to users table
-- Run once: psql -U rdtii_user -d rdtii -f migrate_001_auth.sql

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS last_login    TIMESTAMP;
