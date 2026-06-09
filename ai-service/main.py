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
import json
import logging
import os
import tempfile

import httpx
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import Depends
from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# psycopg2 is imported lazily inside the persistence handler so that
# importing `main` (e.g. for tests, or for /health on a stripped image)
# doesn't require the Postgres driver to be installed.

from chunker import regex_legal_chunker
from classifier import classify_indicator
from coverage_classifier import classify_coverage
from features import get_feature_spec
from providers import canonical_name, get_default_provider, list_providers, get_provider
from providers.base import ExtractionError
from source_validator import grade_source, require_primary_source
from timeframe_extractor import extract_timeframe, build_timeframe_column

# crawler.py pulls in playwright; pdf_reader pulls in pymupdf / tesseract.
# Both are heavy and only needed for the URL-ingestion path, so import
# them lazily inside the request handler. Keeping main importable
# without these makes /health, /providers and the unit-test suite work
# in environments where the crawl/OCR stack isn't installed.
from providers.base import ExtractionError
from schemas import (
    ExtractionResponse,
    IndicatorMapping,
    RAGQueryRequest,
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


# ── Shared extraction pipeline (used by /api/extract and /api/upload) ────


async def _run_extraction(text: str, llm_provider) -> ExtractionResponse:
    import time as _time
    _t0 = _time.time()

    chunks = regex_legal_chunker(text)

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
                results = []
                for ind_id, spec in indicators:
                    data = batch.get(ind_id) if isinstance(batch, dict) else None
                    results.append((ind_id, spec, data))

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

                # ── Source validation ─────────────────────────────────
                src_val = grade_source(
                    url=data.get("source_url", ""),
                    title=data.get("source_legislation", ""),
                    text_snippet=chunk.text[:300],
                )
                features["_source_grade"] = src_val.get("grade", "unknown")
                features["_source_grade_confidence"] = str(round(src_val.get("confidence", 0.0), 2))

                # ── Coverage classification override ─────────────────
                if scope_value == "unknown":
                    cc = classify_coverage(
                        provision_text=data.get("verbatim_quote", ""),
                        source_legislation=data.get("source_legislation", ""),
                        indicator_id=ind_id,
                    )
                    scope_value = cc["scope"]
                    features["_coverage_reasons"] = "; ".join(cc.get("reasons", []))

                # ── Timeframe extraction ─────────────────────────────
                tf = extract_timeframe(
                    text=chunk.text,
                    source_legislation=data.get("source_legislation", ""),
                    source_url=data.get("source_url", ""),
                )
                tf_column = build_timeframe_column(
                    status=tf["status"],
                    in_force_date=tf.get("in_force_date"),
                    last_amended_date=tf.get("last_amended_date"),
                    repealed_date=tf.get("repealed_date"),
                )
                features["_timeframe_status"] = tf["status"]
                features["_timeframe_column"] = tf_column

                # ── 三重时间戳核实 ─────────────────────────────────
                source_url_val = data.get("source_url", "")
                last_update_val = data.get("last_update", "")
                ts_verification = {}
                if source_url_val and last_update_val:
                    try:
                        from crawler import verify_law_timeline
                        ts_verification = await verify_law_timeline(
                            source_url_val, last_update_val,
                        )
                    except Exception:
                        pass

                mapped.append((IndicatorMapping(
                    pillar=int(ind_id.split(".", 1)[0]),
                    indicator=ind_id,
                    score=score,
                    verbatim_quote=data["verbatim_quote"],
                    quote_start=chunk.start + local_start,
                    quote_end=chunk.start + local_end,
                    source_legislation=data.get("source_legislation", ""),
                    last_update=ts_verification.get("best_date") or last_update_val,
                    source_url=source_url_val,
                    scope=scope_value,
                    features=features,
                    impact=justification,
                    requires_human_review=False,
                    extraction_provider=llm_provider.name,
                    timestamp_verification=ts_verification,
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


import httpx

@app.get("/providers/ollama-models")
def ollama_models():
    """List models available on the local Ollama instance.

    Queries the Ollama HTTP API at ``OLLAMA_BASE_URL`` (default
    http://localhost:11434/v1) and returns model names suitable for
    ``OLLAMA_MODEL``.

    Returns ``{"models": ["gemma4:12b", ...], "error": null}`` on
    success, or ``{"models": [], "error": "…"}`` when Ollama is
    unreachable.
    """
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    api_base = base.rstrip("/v1").rstrip("/")  # Ollama /api/tags is outside /v1
    url = f"{api_base}/api/tags"
    try:
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return {"models": sorted(models), "error": None}
    except Exception as exc:
        return {"models": [], "error": str(exc)}


@app.post("/embed")
def embed(req: TextRequest):
    from sklearn.preprocessing import normalize

    vector = _get_embed_model().encode([req.text])
    vector = normalize(vector)
    return {"vector": vector[0].tolist()}


# ── RAG / Chat with local Ollama ──────────────────────────────────────

_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6")

_RDTII_SYSTEM_PROMPT = """You are a UN ESCAP digital trade policy analyst specializing in the Regional Digital Trade Integration Index (RDTII) 2.1 framework.

Your role is to help researchers and policymakers evaluate a country's digital trade policies using the RDTII 2.1 methodology.

CORE KNOWLEDGE:
- RDTII covers 12 pillars: Tariffs, Public Procurement, FDI, Intellectual Property Rights, Telecom Regulations, Cross-border Data Policies, Data Protection & Privacy, Intermediary Liability, Content Access, Non-technical NTMs, Standards & Procedures, Online Sales & Transactions.
- Each pillar contains multiple indicators scored {0, 0.25, 0.5, 0.75, 1.0} where 0 = most open / least restrictive and 1 = most restrictive.
- Scoring follows deterministic rules (e.g. a comprehensive data protection law → score 0 for indicator 7.1; no law → score 1).
- The LLM extracts structured features from legal text; scores are computed by deterministic Python code.

RESPONSE GUIDELINES:
- Be precise and reference specific RDTII pillars/indicators when relevant.
- Ground your analysis in the legal text provided in the context.
- Explain which provisions of the law map to which indicators.
- If asked about scoring, describe the criteria but do NOT output a final score (that is the system's job).
- Keep answers concise and actionable for a policy audience.
- If the context includes specific legal text, quote relevant clauses before analyzing them."""


@app.post("/api/rag/query")
async def chat_query(req: RAGQueryRequest):
    """RAG-style LLM query with streaming SSE response.

    Calls a local Ollama instance (qwen3.6) via the OpenAI-compatible API.
    Configure via env vars:
        OLLAMA_BASE_URL  (default: http://host.docker.internal:11434/v1)
        OLLAMA_MODEL     (default: qwen3.6)
    """
    parts = [f"Question: {req.question}"]
    if req.role:
        parts.insert(0, f"Your role: {req.role}")
    if req.context:
        parts.append(f"Additional context: {req.context}")
    if req.country_code:
        parts.append(f"Country / Economy under review: {req.country_code}")
    if req.source_text:
        parts.append(f"Legal text being analyzed:\n\"\"\"\n{req.source_text}\n\"\"\"")
    user_prompt = "\n\n".join(parts)

    client = OpenAI(base_url=_OLLAMA_BASE, api_key="ollama")

    async def _stream():
        try:
            stream = client.chat.completions.create(
                model=_OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": _RDTII_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
                temperature=0.3,
            )
            full_answer = ""
            for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                if content:
                    full_answer += content
                    yield f"event: token\ndata: {json.dumps(content)}\n\n"

            yield (
                f"event: done\ndata: "
                f"{json.dumps({'answer': full_answer, 'provider': f'ollama/{_OLLAMA_MODEL}'})}\n\n"
            )
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _is_thai_query(t: str) -> bool:
    """Check if text is a short Thai search query (not a full document)."""
    import re
    thai_chars = sum(1 for c in t if '\u0E00' <= c <= '\u0E7F')
    return thai_chars > 0 and len(t) < 200


def _is_garbage_content(t: str) -> bool:
    """Detect if crawled content is garbage (JS/CSS/block page)."""
    if len(t) < 500:
        return True
    garbage_signals = [
        "window.addEventListener", "DOMContentLoaded", "archive_analytics",
        "performing security", "just a moment", "cloudflare ray id",
        "webpackJsonp", "this.addEventListener",
    ]
    return any(s in t.lower()[:2000] for s in garbage_signals)


@app.post("/api/extract", response_model=ExtractionResponse)
async def extract(text: str = Form(""), source_url: str = Form(""), provider: str = Form(None), model: str = Form(None)):
    """Extract RDTII indicator mappings from a block of legal text.

    Priority:
      1. If source_url is provided → crawl URL (web page / PDF / Word doc).
         If crawled content is garbage + user has Thai query → try OCS search.
      2. If only text looks like Thai law name (short, Thai chars) → search OCS.
      3. Otherwise → score text directly.
    """
    from crawler import fetch_legal_content, fetch_thai_law_by_keyword
    from pdf_reader import read_pdf

    original_text = text

    # ── Path A: URL provided → crawl ──
    if source_url.strip():
        crawl_result = await fetch_legal_content(source_url)

        if crawl_result["type"] == "text":
            text = crawl_result["text"]
            # If crawled content is garbage AND user has Thai query → try OCS
            if _is_garbage_content(text) and _is_thai_query(original_text):
                print(f"[extract] 爬取内容为垃圾内容，尝试 OCS 搜索: {original_text[:60]}")
                ocs_result = await fetch_thai_law_by_keyword(original_text.strip())
                if ocs_result["type"] == "text":
                    text = ocs_result["text"]
        elif crawl_result["type"] == "pdf":
            try:
                pages = await asyncio.to_thread(read_pdf, crawl_result["pdf_path"])
                text = "\n".join(pages)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")
        elif crawl_result["type"] == "docx":
            text = crawl_result["text"]
        else:
            # crawl_result["type"] == "error"
            if _is_thai_query(original_text):
                print(f"[extract] URL 爬取错误，尝试 OCS 搜索: {original_text[:60]}")
                ocs_result = await fetch_thai_law_by_keyword(original_text.strip())
                if ocs_result["type"] == "text":
                    text = ocs_result["text"]
                else:
                    raise HTTPException(status_code=400, detail=f"Crawl failed: {crawl_result['message']}")
            else:
                raise HTTPException(status_code=400, detail=f"Crawl failed: {crawl_result['message']}")

    # ── Path B: No URL, just text ──
    else:
        if _is_thai_query(text):
            print(f"[extract] 检测到泰语搜索词，尝试 OCS 搜索: {text[:60]}")
            ocs_result = await fetch_thai_law_by_keyword(text.strip())
            if ocs_result["type"] == "text":
                text = ocs_result["text"]
            else:
                print(f"[extract] OCS 搜索未返回结果: {ocs_result.get('message', '')}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text provided and crawl returned no content.")

    if provider:
        try:
            if provider == "ollama" and model:
                from providers.ollama import OllamaProvider
                llm_provider = OllamaProvider(model=model)
            else:
                llm_provider = get_provider(provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ExtractionError as e:
            raise HTTPException(status_code=503, detail=str(e))
    else:
        llm_provider = _get_provider()

    return await _run_extraction(text, llm_provider)


# ── SSE streaming extraction (used by frontend) ────────────


async def _stream_extraction(text: str, llm_provider) -> AsyncGenerator[str, None]:
    """Run extraction and yield SSE events progressively.

    Events:
      event: started  {source_text}
      event: mapping  {IndicatorMapping}
      event: rejected {RejectedExtraction}
      event: warning  {message}
      event: done     {}
      event: error    {detail}
    """
    from chunker import regex_legal_chunker
    from classifier import classify_indicator
    from coverage_classifier import classify_coverage
    from features import get_feature_spec
    from source_validator import grade_source
    from timeframe_extractor import extract_timeframe, build_timeframe_column
    from verification import find_quote_offsets, verify_quote

    import time as _time

    def _sse(event: str, payload: object) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"

    yield _sse("started", {"source_text": text})

    chunks = regex_legal_chunker(text)
    chunk_groups: list[tuple] = []
    for chunk in chunks:
        indicators: list[tuple[str, dict]] = []
        for indicator_id in classify_indicator(chunk.text):
            spec = get_feature_spec(indicator_id)
            if spec:
                indicators.append((indicator_id, spec))
        if indicators:
            chunk_groups.append((chunk, indicators))

    mapping_count = 0
    rejected_count = 0

    for chunk, indicators in chunk_groups:
        try:
            batch = await asyncio.to_thread(
                llm_provider.extract_batch, chunk.text, indicators,
            )
        except ExtractionError as e:
            logger.warning("stream batch failed, per-indicator fallback: %s", e)
            for ind_id, spec in indicators:
                try:
                    data = await asyncio.to_thread(
                        llm_provider.extract_features, chunk.text, ind_id, spec,
                    )
                except ExtractionError:
                    yield _sse("rejected", RejectedExtraction(
                        reason="LLM extraction failed",
                        chunk_preview=chunk.text[:200],
                    ).model_dump())
                    rejected_count += 1
                    continue
                for _ev in _process_single(chunk, ind_id, spec, data, text, llm_provider.name):
                    yield _ev
                mapping_count += 1
        else:
            for ind_id, spec in indicators:
                data = batch.get(ind_id) if isinstance(batch, dict) else None
                if data is None:
                    yield _sse("rejected", RejectedExtraction(
                        reason="missing indicator in batch response",
                        chunk_preview=chunk.text[:200],
                    ).model_dump())
                    rejected_count += 1
                    continue
                for _ev in _process_single(chunk, ind_id, spec, data, text, llm_provider.name):
                    yield _ev
                mapping_count += 1

    yield _sse("done", {
        "mappings_count": mapping_count,
        "rejected_count": rejected_count,
        "provider": llm_provider.name,
    })


def _process_single(chunk, ind_id, spec, data, full_text, provider_name="unknown"):
    """Process one LLM extraction result — yield 0 or 1 SSE events for it."""
    from coverage_classifier import classify_coverage
    from source_validator import grade_source
    from timeframe_extractor import extract_timeframe, build_timeframe_column
    from verification import find_quote_offsets, verify_quote
    from scoring import score_indicator
    from schemas import IndicatorMapping, RejectedExtraction

    def _sse(event, payload):
        return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"

    quote = (data.get("verbatim_quote") or "").strip()
    if not quote or not verify_quote(quote, chunk.text):
        yield _sse("rejected", RejectedExtraction(
            reason="verbatim_quote not found in chunk shown to LLM",
            chunk_preview=chunk.text[:200],
            raw_output=data,
        ).model_dump())
        return

    local_start, local_end = find_quote_offsets(quote, chunk.text)
    if local_start < 0 or local_end <= local_start:
        yield _sse("rejected", RejectedExtraction(
            reason="verbatim_quote matched fuzzily but exact offsets unrecoverable",
            chunk_preview=chunk.text[:200],
            raw_output=data,
        ).model_dump())
        return

    features = {k: data[k] for k in spec.keys() if k in data}
    try:
        score, justification = score_indicator(ind_id, features)
    except NotImplementedError:
        score, justification = 0.5, "Scoring rules not implemented."

    raw_scope = (data.get("scope") or "").strip().lower()
    scope_value = raw_scope if raw_scope in {"horizontal", "sectoral"} else "unknown"

    src_val = grade_source(
        url=data.get("source_url", ""),
        title=data.get("source_legislation", ""),
        text_snippet=chunk.text[:300],
    )
    features["_source_grade"] = src_val.get("grade", "unknown")
    features["_source_grade_confidence"] = str(round(src_val.get("confidence", 0.0), 2))

    if scope_value == "unknown":
        cc = classify_coverage(
            provision_text=data.get("verbatim_quote", ""),
            source_legislation=data.get("source_legislation", ""),
            indicator_id=ind_id,
        )
        scope_value = cc["scope"]
        features["_coverage_reasons"] = "; ".join(cc.get("reasons", []))

    tf = extract_timeframe(
        text=chunk.text,
        source_legislation=data.get("source_legislation", ""),
        source_url=data.get("source_url", ""),
    )
    tf_column = build_timeframe_column(
        status=tf["status"],
        in_force_date=tf.get("in_force_date"),
        last_amended_date=tf.get("last_amended_date"),
        repealed_date=tf.get("repealed_date"),
    )
    features["_timeframe_status"] = tf["status"]
    features["_timeframe_column"] = tf_column

    source_url_val = data.get("source_url", "")
    last_update_val = data.get("last_update", "")
    ts_verification = {}

    mapping = IndicatorMapping(
        pillar=int(ind_id.split(".", 1)[0]),
        indicator=ind_id,
        score=score,
        verbatim_quote=data["verbatim_quote"],
        quote_start=chunk.start + local_start,
        quote_end=chunk.start + local_end,
        source_legislation=data.get("source_legislation", ""),
        last_update=ts_verification.get("best_date") or last_update_val,
        source_url=source_url_val,
        scope=scope_value,
        features=features,
        impact=justification,
        requires_human_review=False,
        extraction_provider=provider_name,
        timestamp_verification=ts_verification,
    )
    yield _sse("mapping", mapping.model_dump())


@app.post("/api/extract/stream")
async def extract_stream(text: str = Form(""), source_url: str = Form(""), provider: str = Form(None), model: str = Form(None)):
    """Stream RDTII extraction results via Server-Sent Events.

    Same pipeline as /api/extract but emits each mapping as an SSE event
    for progressive rendering in the frontend.
    """
    from crawler import fetch_legal_content, fetch_thai_law_by_keyword
    from pdf_reader import read_pdf

    def _sse(event, payload):
        return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"

    original_text = text
    source_text = ""

    if source_url.strip():
        crawl_result = await fetch_legal_content(source_url)
        if crawl_result["type"] == "text":
            text = crawl_result["text"]
            source_text = text
            if _is_garbage_content(text) and _is_thai_query(original_text):
                ocs_result = await fetch_thai_law_by_keyword(original_text.strip())
                if ocs_result["type"] == "text":
                    text = ocs_result["text"]
                    source_text = text
        elif crawl_result["type"] == "pdf":
            try:
                pages = await asyncio.to_thread(read_pdf, crawl_result["pdf_path"])
                text = "\n".join(pages)
                source_text = text
            except Exception as e:
                async def _error():
                    yield _sse("error", {"detail": f"PDF parsing failed: {str(e)}"})
                return StreamingResponse(_error(), media_type="text/event-stream")
        elif crawl_result["type"] == "docx":
            text = crawl_result["text"]
            source_text = text
        else:
            if _is_thai_query(original_text):
                ocs_result = await fetch_thai_law_by_keyword(original_text.strip())
                if ocs_result["type"] == "text":
                    text = ocs_result["text"]
                    source_text = text
                else:
                    async def _err():
                        yield _sse("error", {"detail": f"Crawl failed: {crawl_result['message']}"})
                    return StreamingResponse(_err(), media_type="text/event-stream")
            else:
                async def _err():
                    yield _sse("error", {"detail": f"Crawl failed: {crawl_result['message']}"})
                return StreamingResponse(_err(), media_type="text/event-stream")
    else:
        if _is_thai_query(text):
            ocs_result = await fetch_thai_law_by_keyword(text.strip())
            if ocs_result["type"] == "text":
                text = ocs_result["text"]
                source_text = text

    if not text.strip():
        async def _empty():
            yield _sse("error", {"detail": "No text provided and crawl returned no content."})
        return StreamingResponse(_empty(), media_type="text/event-stream")

    try:
        if provider:
            if provider == "ollama" and model:
                from providers.ollama import OllamaProvider
                llm_provider = OllamaProvider(model=model)
            else:
                llm_provider = get_provider(provider)
        else:
            llm_provider = _get_provider()
    except (ValueError, ExtractionError) as e:
        async def _bad_provider():
            yield _sse("error", {"detail": str(e)})
        return StreamingResponse(_bad_provider(), media_type="text/event-stream")

    stream = _stream_extraction(text, llm_provider)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/upload", response_model=ExtractionResponse)
async def upload(file: UploadFile = File(...), provider: str = Form(None), model: str = Form(None)):
    """Upload a PDF file and extract RDTII indicator mappings from it."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    from pdf_reader import read_pdf

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        content = await file.read()
        await asyncio.to_thread(tmp.write, content)
        tmp.close()

        pages = await asyncio.to_thread(read_pdf, tmp.name)
        text = "\n".join(pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")
    finally:
        await asyncio.to_thread(os.unlink, tmp.name)

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")

    if provider:
        try:
            if provider == "ollama" and model:
                from providers.ollama import OllamaProvider
                llm_provider = OllamaProvider(model=model)
            else:
                llm_provider = get_provider(provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ExtractionError as e:
            raise HTTPException(status_code=503, detail=str(e))
    else:
        llm_provider = _get_provider()

    return await _run_extraction(text, llm_provider)


# ── Alias: /api/ingest/document → upload ────────────────


@app.post("/api/ingest/document", response_model=ExtractionResponse)
async def ingest_document(file: UploadFile = File(...), provider: str = Form(None), model: str = Form(None)):
    """Alias for /api/upload — used by frontend INGEST_API_URL."""
    return await upload(file, provider, model)


# ── /api/fetch-text — crawl a URL and return raw text ────


class FetchTextRequest(BaseModel):
    source_url: str = ""


class FetchTextResponse(BaseModel):
    text: str = ""


@app.post("/api/fetch-text")
async def fetch_text(req: FetchTextRequest):
    """Crawl a URL and return extracted plain text without LLM extraction."""
    from crawler import fetch_legal_content
    from pdf_reader import read_pdf

    if not req.source_url.strip():
        raise HTTPException(status_code=400, detail="source_url is required.")

    crawl_result = await fetch_legal_content(req.source_url)
    if crawl_result["type"] == "text":
        return FetchTextResponse(text=crawl_result["text"])
    elif crawl_result["type"] == "pdf":
        try:
            pages = await asyncio.to_thread(read_pdf, crawl_result["pdf_path"])
            return FetchTextResponse(text="\n".join(pages))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")
    elif crawl_result["type"] == "docx":
        return FetchTextResponse(text=crawl_result["text"])
    else:
        raise HTTPException(status_code=400, detail=f"Crawl failed: {crawl_result.get('message', 'unknown error')}")


# ── Auth (register routes from auth.py) ────────────────────


from auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    _bearer,
    forgot_password,
    get_current_user,
    login,
    register,
    reset_password,
)


class LoginRequestOut(BaseModel):
    email: str
    password: str


@app.post("/auth/register")
async def auth_register(req: RegisterRequest):
    return await register(req)


@app.post("/auth/login")
async def auth_login(req: LoginRequest):
    return await login(req)


@app.post("/auth/forgot-password")
async def auth_forgot_password(req: ForgotPasswordRequest):
    return await forgot_password(req)


@app.post("/auth/reset-password")
async def auth_reset_password(req: ResetPasswordRequest):
    return await reset_password(req)


@app.get("/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ── Database-backed review ──────────────────────────────


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


# ── Excel export ──────────────────────────────────────────


class ExcelExportRequest(BaseModel):
    """Request for Excel export of indicator mappings."""
    country: str = "unknown"
    mappings: list[IndicatorMapping] = []
    filename: str = "rdtii_mappings.xlsx"


@app.post("/api/excel/export")
async def export_excel(req: ExcelExportRequest):
    """Export indicator mappings to Excel (.xlsx) format.
    
    Returns the Excel file as a download attachment.
    Follows RDTII 2.1 data collection practice format.
    """
    from excel_exporter import create_excel_response, mappings_to_excel

    try:
        return create_excel_response(
            mappings=req.mappings,
            country=req.country,
            filename=req.filename,
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Excel export unavailable: {e}. Install openpyxl.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel export failed: {str(e)}")


# ── Source validation ──────────────────────────────────────


class SourceValidationRequest(BaseModel):
    url: str = ""
    title: str = ""
    text_snippet: str = ""


class SourceValidationResponse(BaseModel):
    grade: str
    confidence: float
    reasons: list[str]
    is_primary: bool
    warning: str = ""


@app.post("/api/validate/source")
def validate_source(req: SourceValidationRequest):
    """Validate whether a source is a primary/official legal instrument.
    
    Primary sources: official legal instruments with legal effect.
    Secondary sources: news, commentaries, academic publications.
    """
    from source_validator import require_primary_source

    result = require_primary_source(
        url=req.url,
        title=req.title,
        text_snippet=req.text_snippet,
    )
    return SourceValidationResponse(
        grade=result["grade"],
        confidence=result["confidence"],
        reasons=result["reasons"],
        is_primary=result["is_primary"],
        warning=result.get("warning", ""),
    )


# ── Timestamp verification (existing, documented) ────────


class TimestampVerificationRequest(BaseModel):
    url: str = ""
    last_update: str = ""


class TimestampVerificationResponse(BaseModel):
    verified: bool
    best_date: str
    verification_log: str
    source_details: list = []


@app.post("/api/verify/timestamp")
async def verify_timestamp(req: TimestampVerificationRequest):
    """Three-source timestamp verification for a legal source URL."""
    try:
        from crawler import verify_law_timeline
        result = await verify_law_timeline(req.url, req.last_update)
        return TimestampVerificationResponse(
            verified=result.get("verified", False),
            best_date=result.get("best_date", ""),
            verification_log=result.get("verification_log", ""),
            source_details=result.get("source_details", []),
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="crawler module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timestamp verification failed: {str(e)}")


# ── Coverage classification ─────────────────────────────


class CoverageRequest(BaseModel):
    provision_text: str = ""
    source_legislation: str = ""
    indicator_id: str = ""


@app.post("/api/classify/coverage")
def classify_coverage_api(req: CoverageRequest):
    """Classify a legal measure as horizontal or sectoral."""
    from coverage_classifier import classify_coverage

    result = classify_coverage(
        provision_text=req.provision_text,
        source_legislation=req.source_legislation,
        indicator_id=req.indicator_id,
    )
    return result
