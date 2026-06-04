-- Migration 003: User document ownership and access control
-- Run once: psql -U rdtii_user -d rdtii -f migrate_003_document_ownership.sql

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);

CREATE TABLE IF NOT EXISTS user_document_access (
    user_id      UUID        NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
    document_id  UUID        NOT NULL REFERENCES documents(id)  ON DELETE CASCADE,
    access_level VARCHAR(20) NOT NULL DEFAULT 'viewer'
        CHECK (access_level IN ('owner', 'reviewer', 'viewer')),
    granted_by   UUID        REFERENCES users(id) ON DELETE SET NULL,
    granted_at   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_uda_user_id     ON user_document_access(user_id);
CREATE INDEX IF NOT EXISTS idx_uda_document_id ON user_document_access(document_id);
