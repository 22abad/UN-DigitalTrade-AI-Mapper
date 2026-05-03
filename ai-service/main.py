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

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chunker import regex_legal_chunker
from classifier import classify_indicator
from features import get_feature_spec
from providers import get_default_provider, list_providers
from providers.base import ExtractionError
from schemas import (
    ExtractionResponse,
    IndicatorMapping,
    RejectedExtraction,
)
from scoring import score_indicator
from verification import find_quote_offsets, verify_quote

load_dotenv()

app = FastAPI(title="RDTII AI Mapper", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(","),
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
        _provider = get_default_provider()
    return _provider


# ── Request / response models for utility routes ─────────────────────────


class TextRequest(BaseModel):
    text: str


# ── Routes ───────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider_env": os.getenv("RDTII_LLM_PROVIDER", "gemini"),
        "available_providers": list_providers(),
    }


@app.get("/providers")
def providers_info():
    """List swappable providers and which one is active."""
    return {
        "active": os.getenv("RDTII_LLM_PROVIDER", "gemini"),
        "available": list_providers(),
    }


@app.post("/embed")
def embed(req: TextRequest):
    from sklearn.preprocessing import normalize

    vector = _get_embed_model().encode([req.text])
    vector = normalize(vector)
    return {"vector": vector[0].tolist()}


@app.post("/api/extract", response_model=ExtractionResponse)
def extract(text: str = Form(...), source_url: str = Form("")):
    """Extract RDTII indicator mappings from a block of legal text.

    The full pipeline runs per (chunk, indicator) pair. Failed extractions
    surface in `rejected` rather than aborting the whole request.
    """
    provider = _get_provider()
    chunks = regex_legal_chunker(text)

    mappings: list[IndicatorMapping] = []
    rejected: list[RejectedExtraction] = []

    for chunk in chunks:
        candidate_indicators = classify_indicator(chunk)
        for indicator_id in candidate_indicators:
            spec = get_feature_spec(indicator_id)
            if not spec:
                continue

            # 1. Ask the LLM provider for features
            try:
                raw = provider.extract_features(chunk, indicator_id, spec)
            except ExtractionError as e:
                rejected.append(
                    RejectedExtraction(
                        reason=f"provider error: {e}",
                        chunk_preview=chunk[:200],
                    )
                )
                continue

            # 2. Verify the quote (anti-hallucination kill switch).
            # Two-stage gate: (a) the quote must match (allowing fuzzy for
            # OCR/whitespace tolerance) AND (b) we must be able to recover
            # exact offsets — otherwise the audit UI's highlight would point
            # nowhere, breaking the kill-switch contract.
            quote = (raw.get("verbatim_quote") or "").strip()
            if not quote or not verify_quote(quote, text):
                rejected.append(
                    RejectedExtraction(
                        reason="verbatim_quote not found in source",
                        chunk_preview=chunk[:200],
                        raw_output=raw,
                    )
                )
                continue

            q_start, q_end = find_quote_offsets(quote, text)
            if q_start < 0 or q_end <= q_start:
                # Fuzzy-passed but offsets unrecoverable: reject rather than
                # render a (0, 0) highlight. Surfaces in the audit log.
                rejected.append(
                    RejectedExtraction(
                        reason="verbatim_quote matched fuzzily but exact offsets unrecoverable",
                        chunk_preview=chunk[:200],
                        raw_output=raw,
                    )
                )
                continue

            # 3. Apply deterministic scoring
            features = {
                k: v
                for k, v in raw.items()
                if k
                not in {
                    "verbatim_quote",
                    "source_legislation",
                    "last_update",
                    "scope",
                    "impact",
                    "url",
                }
            }
            try:
                score = score_indicator(indicator_id, features)
            except NotImplementedError:
                # Stub scorer — proceed with placeholder so the pipeline
                # is debuggable until Commit 2 lands.
                score = 0.5  # type: ignore[assignment]

            # 4. Sanitize provider-supplied scope: schema requires a Literal
            # value, an unknown string would crash Pydantic construction.
            raw_scope = (raw.get("scope") or "").strip().lower()
            scope_value = raw_scope if raw_scope in {"horizontal", "sectoral"} else "unknown"

            mappings.append(
                IndicatorMapping(
                    pillar=int(indicator_id.split(".", 1)[0]),  # type: ignore[arg-type]
                    indicator=indicator_id,  # type: ignore[arg-type]
                    score=score,  # type: ignore[arg-type]
                    verbatim_quote=quote,
                    quote_start=q_start,
                    quote_end=q_end,
                    source_legislation=raw.get("source_legislation", ""),
                    last_update=raw.get("last_update", ""),
                    source_url=source_url or raw.get("url", ""),
                    scope=scope_value,  # type: ignore[arg-type]
                    features=features,
                    impact=raw.get("impact", ""),
                    extraction_provider=provider.name,
                )
            )

    return ExtractionResponse(
        mappings=mappings,
        rejected=rejected,
        provider=provider.name,
    )
