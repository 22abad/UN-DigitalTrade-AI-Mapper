-- Sidecar document cache
-- Keyed by SHA-256 of raw file bytes so the same file is never OCR'd twice.
-- source_url lets the crawler do a URL lookup before downloading + hashing.
-- expires_at NULL = permanent; set for legal texts that need periodic refresh.

CREATE TABLE IF NOT EXISTS extracted_documents (
    id             TEXT        PRIMARY KEY,
    content_hash   TEXT        NOT NULL UNIQUE,
    source_url     TEXT,
    filename       TEXT        NOT NULL,
    source_type    TEXT        NOT NULL,
    ocr_provider   TEXT        NOT NULL DEFAULT '',
    extracted_text TEXT        NOT NULL,
    expires_at     TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ext_docs_hash
    ON extracted_documents (content_hash);

CREATE INDEX IF NOT EXISTS idx_ext_docs_url
    ON extracted_documents (source_url)
    WHERE source_url IS NOT NULL;

-- Partial index — only expirable rows need scanning by the eviction job.
CREATE INDEX IF NOT EXISTS idx_ext_docs_expires
    ON extracted_documents (expires_at)
    WHERE expires_at IS NOT NULL;

-- ── Link SENTINEL documents → sidecar extraction record ──────────────────────
-- Nullable: existing rows unaffected. Populated when ingestion went via sidecar.
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS sidecar_doc_id TEXT
    REFERENCES extracted_documents(id) ON DELETE SET NULL;

-- ── Link RAG chunks → sidecar extraction record ───────────────────────────────
-- Nullable: existing chunks unaffected. parent_document_id remains as-is.
ALTER TABLE chunks
  ADD COLUMN IF NOT EXISTS extracted_doc_id TEXT
    REFERENCES extracted_documents(id) ON DELETE SET NULL;
