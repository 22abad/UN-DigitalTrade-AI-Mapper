"""Pydantic schemas for the RDTII AI mapper.

The schema is the contract between the LLM, the deterministic scorer,
the verification layer, and the frontend audit view.

Design rules (anti-hallucination):
- LLM never decides the score — it only emits structured features.
- Every mapping must carry a `verbatim_quote` that exists character-for-character
  in the source. The verification layer rejects mappings that fail this check.
- Scoring is applied by `scoring.score_indicator()` (deterministic Python),
  using the rules from the RDTII 2.1 guide.
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, Field

# RDTII 2.1 valid scores (the indicator-level rule yields one of these)
Score = Literal[0.0, 0.25, 0.5, 1.0]

# We focus on Pillars 6 and 7 for MVP; framework supports adding more later.
PillarId = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
IndicatorId = Literal[
    "1.1", "2.1", "3.1", "4.1", "5.1",
    "6.1", "6.2", "6.3", "6.4", "6.5",
    "7.1", "7.2", "7.3", "7.4", "7.5",
    "8.1", "9.1", "10.1", "11.1", "12.1"
]

ScopeKind = Literal["horizontal", "sectoral", "unknown"]

# Feature dict values can be bool / int / str depending on the indicator spec.
FeatureValue = Union[bool, int, str]


class IndicatorMapping(BaseModel):
    """One mapping from one article (or clause) to one RDTII indicator.

    Multiple mappings per source document are normal — a single law often
    touches several indicators.
    """

    pillar: PillarId
    indicator: IndicatorId
    score: Score

    # Source grounding (the kill switch acts on these)
    verbatim_quote: str = Field(
        ...,
        description="Exact text from source. Must match string-for-string.",
    )
    quote_start: int = Field(
        ...,
        ge=0,
        description="Character offset of verbatim_quote within the original text.",
    )
    quote_end: int = Field(
        ...,
        ge=0,
        description="End character offset (exclusive) within the original text.",
    )

    # Legal-text metadata (the 6 mandatory fields from Witada PPT)
    article_clause: str = Field(default="", description="Specific article, section, or clause number")
    source_legislation: str = Field(default="", description="Law / regulation title")
    last_update: str = Field(default="", description="Last amended / promulgation date")
    source_url: str = Field(default="", description="Authoritative source URL")
    scope: ScopeKind = "unknown"

    # Structured flags driving the deterministic scorer
    features: dict[str, FeatureValue] = Field(default_factory=dict)

    # Human-readable description (for the audit view)
    impact: str = Field(default="")

    # Audit metadata
    requires_human_review: bool = False
    flag_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons this mapping was flagged by the anti-hallucination validation layer.",
    )
    extraction_provider: str = Field(
        default="unknown",
        description="LLM identifier (e.g. 'gemini-1.5-flash', 'claude-sonnet-4', 'llama-3-8b-local')",
    )

    # Legal Inventory taxonomy (the 6 fields from the Target Schema Template)
    coverage: str = Field(
        default="",
        description="Detailed coverage description of the measure (e.g. 'ICT products', 'Telecommunication equipments')",
    )
    Coverage: str = Field(
        default="",
        description="Detailed coverage description of the measure (e.g. 'ICT products', 'Telecommunication equipments')",
    )
    cluster: str = Field(
        default="",
        description="High-level policy cluster (e.g. 'Traditional trade policies', 'Digital governance policies', 'Other domestic policies')",
    )
    region: str = Field(
        default="",
        description="Geographic region (e.g. 'South-East Asia', 'Pacific'). Derived from economy client-side if empty.",
    )
    cov_name: str = Field(
        default="",
        description="Coverage name derived from scope: 'Cross-cutting' (horizontal) or 'Sectoral' (sectoral)",
    )
    name: str = Field(
        default="",
        description="Mid-level policy category (e.g. 'Tariffs & trade defence', 'Non-technical NTMs', 'Online sales & transactions')",
    )
    policy_description: str = Field(
        default="",
        description="Specific policy type (e.g. 'Trade defence measures', 'Import bans', 'Local content requirements')",
    )

    # Timestamp verification — triple-source audit of the last_update field
    timestamp_verification: dict = Field(
        default_factory=dict,
        description=(
            "Results of triple-source timestamp verification: "
            "{verified: bool, best_date: str, verification_log: str, source_details: list}"
        ),
    )

    # RDTII 2.1 — 10 Fields (and their aliases for compatibility)
    Pillar_ID: str = Field(default="", description="Pillar ID, e.g. '6.0'")
    pillar_id: str = Field(default="", description="Pillar ID alias, e.g. '6.0'")
    
    Indicator_ID: str = Field(default="", description="Indicator ID, e.g. '6.1'")
    indicator_id: str = Field(default="", description="Indicator ID alias, e.g. '6.1'")
    
    Cat_Score: float = Field(default=0.0, description="Sum of raw scores, capped at 1")
    cat_score: float = Field(default=0.0, description="Sum of raw scores, capped at 1")
    
    Raw_Score: float = Field(default=0.0, description="0 / 0.5 / 1 per exact scoring criteria")
    raw_score: float = Field(default=0.0, description="0 / 0.5 / 1 per exact scoring criteria")
    
    Act_and_or_practice: str = Field(default="", description="Title of the regulation/law")
    act_and_or_practice: str = Field(default="", description="Title of the regulation/law")
    act_title: str = Field(default="", description="Act title alias")
    
    Impact_or_comments: str = Field(default="", description="Multi-paragraph legal analysis explaining the score")
    impact_or_comments: str = Field(default="", description="Multi-paragraph legal analysis explaining the score")
    impact_comments: str = Field(default="", description="Impact comments alias")
    
    Timeframe: str = Field(default="", description="Enactment + amendment dates")
    timeframe: str = Field(default="", description="Enactment + amendment dates")
    
    References: str = Field(default="", description="Primary source URLs (official gov) + secondary sources")
    references: str = Field(default="", description="Primary source URLs (official gov) + secondary sources")
    
    Note: str = Field(default="", description="Internal researcher notes")
    note: str = Field(default="", description="Internal researcher notes")


class RejectedExtraction(BaseModel):
    """A failed mapping — surfaced for debugging / audit, not shown to user."""

    reason: str
    chunk_preview: str = Field(default="", max_length=400)
    raw_output: dict = Field(default_factory=dict)


class ExtractionResponse(BaseModel):
    """Top-level response from /api/extract.

    A single document may yield many mappings; rejections are kept separately
    so the UI can show "we tried but couldn't verify" cases.
    """

    mappings: list[IndicatorMapping] = Field(default_factory=list)
    rejected: list[RejectedExtraction] = Field(default_factory=list)
    provider: str = Field(default="unknown")
    source_text: str = Field(default="", description="The actual text used for extraction (may differ from input when URL was crawled or PDF was parsed).")


class ReviewRequest(BaseModel):
    """Request schema for /api/mappings/review."""

    decision: Literal["approved", "rejected"]
    country_code: str
    mapping: IndicatorMapping
    reviewer_notes: str | None = Field(default=None, description="Optional human review notes/feedback for fine-tuning")


class ExtractionRequest(BaseModel):
    """Optional structured request (the form-encoded path is also supported)."""

    text: str
    source_url: str = ""
    source_legislation: str = ""


class RAGQueryRequest(BaseModel):
    """Request schema for /api/rag/query."""

    question: str
    role: str = ""
    context: str = ""
    output_format: str = ""
    source_text: str = ""
    country_code: str = ""
    provider: str = ""


class RAGQueryResponse(BaseModel):
    """Response schema for /api/rag/query."""

    answer: str
    provider: str
    retrieved_chunks: list[str] = []
    retrieval_count: int = 0
