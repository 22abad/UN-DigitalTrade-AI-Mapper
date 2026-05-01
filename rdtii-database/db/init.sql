-- ============================================================
-- UN-DigitalTrade-AI-Mapper Database Schema
-- PostgreSQL 17 + pgvector
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- Reference Data
-- ============================================================

CREATE TABLE countries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(3) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    region VARCHAR(100),
    is_escap_member BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rdtii_pillars (
    pillar_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pillar_number INTEGER NOT NULL,
    pillar_name VARCHAR(255) NOT NULL,
    criterion_id VARCHAR(50) NOT NULL,
    criterion_name VARCHAR(500) NOT NULL,
    indicator_id VARCHAR(50) NOT NULL,
    indicator_description TEXT,
    weight_score NUMERIC(5, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Document Ingestion Pipeline
-- ============================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    country_code VARCHAR(3) REFERENCES countries(code),
    source_url VARCHAR(2000),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'downloaded', 'processing', 'processed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_number VARCHAR(50),
    article_title VARCHAR(500),
    raw_text TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    source_pdf_offset INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- RAG: Chunks & Vector Embeddings
-- ============================================================

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES document_sections(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    country_code VARCHAR(3) REFERENCES countries(code),
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunk_embeddings_embedding ON chunk_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_chunk_embeddings_document ON chunk_embeddings(document_id);
CREATE INDEX idx_chunk_embeddings_country ON chunk_embeddings(country_code);

-- ============================================================
-- Extraction & Mapping
-- ============================================================

CREATE TABLE extracted_obligations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES document_sections(id) ON DELETE CASCADE,
    obligation_type VARCHAR(100),
    extracted_text TEXT NOT NULL,
    confidence_score NUMERIC(3, 2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE regulation_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    obligation_id UUID NOT NULL REFERENCES extracted_obligations(id) ON DELETE CASCADE,
    pillar_id UUID NOT NULL REFERENCES rdtii_pillars(pillar_id),
    criterion_id VARCHAR(50),
    evidence_text TEXT,
    compliance_status VARCHAR(20) CHECK (compliance_status IN ('compliant', 'partial', 'non-compliant', 'unknown')),
    mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    audited_by VARCHAR(100)
);

-- ============================================================
-- Transparency / Audit
-- ============================================================

CREATE TABLE audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mapping_id UUID NOT NULL REFERENCES regulation_mappings(id) ON DELETE CASCADE,
    source_section_id UUID NOT NULL REFERENCES document_sections(id) ON DELETE CASCADE,
    highlight_start INTEGER,
    highlight_end INTEGER,
    reviewer_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Optional: User Management
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    role VARCHAR(20) DEFAULT 'viewer' CHECK (role IN ('admin', 'reviewer', 'viewer')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
