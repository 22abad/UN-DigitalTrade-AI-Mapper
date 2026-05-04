-- RDTII AI Mapper Database Schema

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    source_legislation VARCHAR(500),
    source_url TEXT,
    last_update VARCHAR(100),
    raw_text TEXT,
    country_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mappings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    pillar INTEGER NOT NULL,
    indicator VARCHAR(10) NOT NULL,
    score NUMERIC(3, 2) NOT NULL,
    verbatim_quote TEXT NOT NULL,
    quote_start INTEGER NOT NULL,
    quote_end INTEGER NOT NULL,
    scope VARCHAR(50) DEFAULT 'unknown',
    features JSONB DEFAULT '{}'::jsonb,
    impact TEXT,
    requires_human_review BOOLEAN DEFAULT false,
    extraction_provider VARCHAR(100),
    review_status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mappings_doc_id ON mappings(document_id);
CREATE INDEX idx_mappings_review_status ON mappings(review_status);
