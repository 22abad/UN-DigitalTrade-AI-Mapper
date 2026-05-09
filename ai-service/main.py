"""RDTII AI Mapper — FastAPI entry point.

Pipeline:
    1. Chunk the input text into article-level segments (chunker.regex_legal_chunker).
    2. For each chunk, classify which indicators it touches (classifier).
    3. For each (chunk, indicator) pair, ask the LLM provider to extract
       the structured features defined in features.INDICATOR_FEATURES.
    4. Verify the LLM's verbatim_quote is a literal substring of the source
       (verification — anti-hallucination kill switch). Reject otherwise.
    5. Apply the deterministic scoring rule (scoring.score_indicator).
    6. Return all surviving mappings + the rejection log.

The provider is selected via env var RDTII_LLM_PROVIDER ('gemini' / 'claude'
/ 'llama3'). Anywhere `provider` is referenced is the swap point — there is
zero hardcoded LLM logic outside `providers/`.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# psycopg2 is imported lazily inside the persistence handler so that
# importing `main` (e.g. for tests, or for /health on a stripped image)
# doesn't require the Postgres driver to be installed.

from chunker import regex_legal_chunker
from classifier import classify_indicator
from features import get_feature_spec
from providers import canonical_name, get_default_provider, list_providers, get_provider
from providers.base import ExtractionError

# crawler.py pulls in playwright; pdf_reader pulls in pymupdf / tesseract.
# Both are heavy and only needed for the URL-ingestion path, so import
# them lazily inside the request handler. Keeping main importable
# without these makes /health, /providers and the unit-test suite work
# in environments where the crawl/OCR stack isn't installed.
from providers.base import ExtractionError
from schemas import (
    ExtractionResponse,
    IndicatorMapping,
    RejectedExtraction,
    ReviewRequest,
)
from scoring import score_indicator
from verification import find_quote_offsets, verify_quote

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)  # prefer root .env regardless of CWD
load_dotenv(override=True)           # CWD .env overrides root for local dev

app = FastAPI(title="RDTII AI Mapper", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy embedding model — loaded on first /embed call so the app can boot
# without downloading 100MB+ of weights and to keep test imports fast.
_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        _embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embed_model


# Lazy provider singleton — initialized on first /api/extract call so the
# app can boot without API keys (useful for /health and /providers).
_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        try:
            _provider = get_default_provider()
        except ExtractionError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Provider unavailable: {e}. Check .env for API keys.",
            )
    return _provider


# ── Request / response models for utility routes ─────────────────────────


class TextRequest(BaseModel):
    text: str


# ── Routes ───────────────────────────────────────────────────────────────


def _active_provider_name() -> tuple[str, str | None]:
    """Return (raw_env, canonical) for the configured provider.

    Canonical is `None` when the env var doesn't resolve to any known
    provider — endpoints surface that as a misconfiguration rather than
    pretending the unknown name is a valid choice.
    """
    raw = os.getenv("RDTII_LLM_PROVIDER", "gemini")
    return raw, canonical_name(raw)


@app.get("/health")
def health():
    """Lightweight liveness + config-name probe.

    `status: "ok"` only confirms RDTII_LLM_PROVIDER resolves to a
    registered name. It does NOT verify the provider can actually be
    instantiated (SDK installed, API key set, local model file present);
    those failure modes only surface on the first /api/extract call.
    Treat this as a shallow config sanity check, not a full health probe.
    """
    raw, canonical = _active_provider_name()
    return {
        "status": "ok" if canonical else "misconfigured",
        "provider_env": raw,
        "active_provider": canonical,  # None on misconfiguration
        "available_providers": list_providers(),
    }


@app.get("/providers")
def providers_info():
    """List swappable providers and which one is active.

    Contract: when `active` is non-null, it is guaranteed to be a member
    of `available`. When `RDTII_LLM_PROVIDER` doesn't resolve, `active`
    is null and `active_alias` carries the raw value so operators can see
    what was misconfigured.

    The `name_recognised` field reports ONLY whether the configured name
    is in the registry. It is deliberately not called "valid" or "ready"
    because we don't dry-run instantiation — a recognised name with a
    missing API key / model file will still 500 on the first extract
    call. (Doing eager instantiation here would have side effects, e.g.
    loading multi-GB Llama weights at health-check time.)
    """
    raw, canonical = _active_provider_name()
    if canonical is None:
        return {
            "active": None,
            "active_alias": raw,
            "name_recognised": False,
            "available": list_providers(),
        }
    return {
        "active": canonical,
        "active_alias": raw if raw != canonical else None,
        "name_recognised": True,
        "available": list_providers(),
    }


@app.post("/embed")
def embed(req: TextRequest):
    from sklearn.preprocessing import normalize

    vector = _get_embed_model().encode([req.text])
    vector = normalize(vector)
    return {"vector": vector[0].tolist()}


@app.post("/api/extract", response_model=ExtractionResponse)
async def extract(text: str = Form(""), source_url: str = Form(""), provider: str = Form(None)):
    """Extract RDTII indicator mappings from a block of legal text.

    If text is empty but source_url is provided, it crawls the URL first.
    提取法律文本中的 RDTII 指标映射。如果文本为空但提供了 URL，则先抓取。
    """
    if not text.strip() and source_url.strip():
        # Task 2: Backend Crawler Linkage | 任务 2：后端爬虫联动
        # Lazy imports — see top-of-file note.
        from crawler import fetch_legal_content
        from pdf_reader import read_pdf

        crawl_result = await fetch_legal_content(source_url)
        if crawl_result["type"] == "error":
            raise HTTPException(status_code=400, detail=f"Crawl failed: {crawl_result['message']}")

        if crawl_result["type"] == "text":
            text = crawl_result["text"]
        elif crawl_result["type"] == "pdf":
            try:
                pages = read_pdf(crawl_result["pdf_path"])
                text = "\n".join(pages)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text provided and crawl returned no content.")

    import time as _time
    _t0 = _time.time()
    
    if provider:
        try:
            llm_provider = get_provider(provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ExtractionError as e:
            raise HTTPException(status_code=503, detail=str(e))
    else:
        llm_provider = _get_provider()
        
    chunks = regex_legal_chunker(text)

    # Group indicators by chunk — one LLM call per chunk
    chunk_groups: list[tuple] = []
    for chunk in chunks:
        indicators: list[tuple[str, dict]] = []
        for indicator_id in classify_indicator(chunk.text):
            spec = get_feature_spec(indicator_id)
            if spec:
                indicators.append((indicator_id, spec))
        if indicators:
            chunk_groups.append((chunk, indicators))

    logger.debug("[TIMING] %d chunks, concurrency=5", len(chunk_groups))

    semaphore = asyncio.Semaphore(5)

    async def _extract_chunk(chunk, indicators):
        _ct = _time.time()
        async with semaphore:
            try:
                batch = await asyncio.to_thread(
                    llm_provider.extract_batch, chunk.text, indicators,
                )
            except ExtractionError as e:
                # Batch failed (truncation etc.) — fall back to per-indicator
                logger.warning("batch failed, falling back per-indicator: %s", e)
                results: list = []
                for ind_id, spec in indicators:
                    try:
                        data = await asyncio.to_thread(
                            llm_provider.extract_features, chunk.text, ind_id, spec,
                        )
                        results.append((ind_id, spec, data))
                    except ExtractionError:
                        results.append((ind_id, spec, None))
            else:
                # Convert batch dict → list of (ind_id, spec, data)
                results = []
                for ind_id, spec in indicators:
                    data = batch.get(ind_id) if isinstance(batch, dict) else None
                    results.append((ind_id, spec, data))

            # Shared per-indicator processing
            mapped: list[tuple] = []
            for ind_id, spec, data in results:
                if data is None:
                    mapped.append((None, RejectedExtraction(
                        reason="missing indicator in batch/fallback response",
                        chunk_preview=chunk.text[:200],
                    )))
                    continue

                quote = (data.get("verbatim_quote") or "").strip()
                if not quote or not verify_quote(quote, chunk.text):
                    mapped.append((None, RejectedExtraction(
                        reason="verbatim_quote not found in chunk shown to LLM",
                        chunk_preview=chunk.text[:200],
                        raw_output=data,
                    )))
                    continue

                local_start, local_end = find_quote_offsets(quote, chunk.text)
                if local_start < 0 or local_end <= local_start:
                    mapped.append((None, RejectedExtraction(
                        reason="verbatim_quote matched fuzzily but exact offsets unrecoverable",
                        chunk_preview=chunk.text[:200],
                        raw_output=data,
                    )))
                    continue

                features = {k: data[k] for k in spec.keys() if k in data}
                try:
                    score, justification = score_indicator(ind_id, features)
                except NotImplementedError:
                    score, justification = 0.5, "Scoring rules not implemented."

                raw_scope = (data.get("scope") or "").strip().lower()
                scope_value = raw_scope if raw_scope in {"horizontal", "sectoral"} else "unknown"

                mapped.append((IndicatorMapping(
                    pillar=int(ind_id.split(".", 1)[0]),
                    indicator=ind_id,
                    score=score,
                    verbatim_quote=data["verbatim_quote"],
                    quote_start=chunk.start + local_start,
                    quote_end=chunk.start + local_end,
                    source_legislation=data.get("source_legislation", ""),
                    last_update=data.get("last_update", ""),
                    source_url=data.get("source_url", ""),
                    scope=scope_value,
                    features=features,
                    impact=justification,
                    requires_human_review=False,
                    extraction_provider=llm_provider.name,
                ), None))

            logger.debug("[TIMING] chunk [%s] %.1fs", ','.join(i for i,_ in indicators), _time.time()-_ct)
            return mapped, _time.time() - _ct

    all_results = await asyncio.gather(*[_extract_chunk(c, inds) for c, inds in chunk_groups])

    logger.debug("[TIMING] total=%.1fs", _time.time()-_t0)

    mappings: list[IndicatorMapping] = []
    rejected: list[RejectedExtraction] = []
    for chunk_results, _dur in all_results:
        for mapping, rej in chunk_results:
            if mapping:
                mappings.append(mapping)
            elif rej:
                rejected.append(rej)

    return ExtractionResponse(
        mappings=mappings,
        rejected=rejected,
        provider=llm_provider.name,
    )


@app.post("/api/mappings/review")
def review_mapping(req: ReviewRequest):
    """Task 3: Backend Database Review Interface | 任务 3：后端数据库落盘接口
    
    Persists human review decisions into PostgreSQL across 3 tables.
    将人工审核决定持久化到 PostgreSQL 的三张表中。
    """
    db_config = {
        "dbname": os.getenv("POSTGRES_DB", "rdtii"),
        "user": os.getenv("POSTGRES_USER", "rdtii_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "rdtii_password"),
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
    }
    
    import psycopg2  # lazy: see top-of-file note

    conn = None
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # 0. Ensure country exists | 确保国家代码存在
        cur.execute(
            "INSERT INTO countries (code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
            (req.country_code, req.country_code)
        )
        
        # 1. Ensure document and section exist | 确保文档和章节存在
        filename = req.mapping.source_legislation or "Web Extraction"
        source_url = req.mapping.source_url or "Unknown"
        
        cur.execute(
            "INSERT INTO documents (filename, source_url, country_code, status, file_path) "
            "VALUES (%s, %s, %s, 'processed', 'N/A') "
            "ON CONFLICT (source_url) DO NOTHING RETURNING id",
            (filename, source_url, req.country_code)
        )
        doc_res = cur.fetchone()
        if not doc_res:
            cur.execute("SELECT id FROM documents WHERE source_url = %s", (source_url,))
            doc_id = cur.fetchone()[0]
        else:
            doc_id = doc_res[0]
            
        cur.execute(
            "INSERT INTO document_sections (document_id, raw_text) VALUES (%s, %s) RETURNING id",
            (doc_id, req.mapping.verbatim_quote)
        )
        section_id = cur.fetchone()[0]

        cur.execute("SELECT pillar_id FROM rdtii_pillars WHERE indicator_id = %s LIMIT 1", (req.mapping.indicator,))
        pillar_row = cur.fetchone()
        if not pillar_row:
            cur.execute(
                "INSERT INTO rdtii_pillars (pillar_number, pillar_name, indicator_id, criterion_id, criterion_name) "
                "VALUES (%s, %s, %s, 'AUTO', 'Auto-generated') RETURNING pillar_id",
                (req.mapping.pillar, f"Pillar {req.mapping.pillar}", req.mapping.indicator)
            )
            pillar_uuid = cur.fetchone()[0]
        else:
            pillar_uuid = pillar_row[0]

        cur.execute(
            "INSERT INTO extracted_obligations (section_id, extracted_text, status) "
            "VALUES (%s, %s, %s) RETURNING id",
            (section_id, req.mapping.verbatim_quote, "reviewed" if req.decision == "approved" else "rejected")
        )
        obligation_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO regulation_mappings (obligation_id, pillar_id, compliance_status) "
            "VALUES (%s, %s, %s) RETURNING id",
            (obligation_id, pillar_uuid, "compliant" if req.decision == "approved" else "non-compliant")
        )
        mapping_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO audit_trail (mapping_id, source_section_id, highlight_start, highlight_end) "
            "VALUES (%s, %s, %s, %s)",
            (mapping_id, section_id, req.mapping.quote_start, req.mapping.quote_end)
        )

        conn.commit()
        cur.close()
        return {"status": "success", "mapping_id": str(mapping_id)}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database transaction failed: {str(e)}")
    finally:
        if conn:
            conn.close()
