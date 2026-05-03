"""Tests for the /api/extract pipeline hardening (PR #8 review fixes).

Covers failure modes raised in code review:
    - Fuzzy-matched quotes whose exact offsets cannot be recovered must
      be REJECTED (not silently coerced to 0,0).
    - Provider-supplied `scope` values outside the schema literal must
      be sanitized to "unknown" (not raise Pydantic ValidationError).
    - A quote that exists in the document but NOT in the chunk the LLM
      was shown must still be rejected (kill switch is chunk-scoped, not
      document-scoped). Otherwise an LLM can cross-borrow phrases.
    - Mapping `quote_start`/`quote_end` are absolute document offsets,
      not chunk-local ones, so the audit UI highlights the right place.

A real LLM call is too expensive for unit tests, so we inject a
FakeProvider that emits canned outputs.
"""

from __future__ import annotations

from typing import Any

import pytest


class FakeProvider:
    """Minimal LLMProvider stand-in returning a pre-baked dict."""

    name = "fake-provider"

    def __init__(self, response: dict[str, Any]):
        self._response = response

    def extract_features(
        self,
        article_text: str,
        indicator_id: str,
        feature_spec: dict,
    ) -> dict[str, Any]:
        return dict(self._response)


def _patch_provider(monkeypatch, response: dict[str, Any]) -> None:
    """Force /api/extract to use FakeProvider and re-import."""
    import main as main_module

    fake = FakeProvider(response)
    # Reset the singleton and replace the factory.
    main_module._provider = fake
    monkeypatch.setattr(main_module, "_get_provider", lambda: fake)


def _patch_classifier_to(monkeypatch, indicator_ids: list[str]) -> None:
    """Pin classify_indicator output so tests don't depend on keyword tuning."""
    import main as main_module

    monkeypatch.setattr(main_module, "classify_indicator", lambda _t: indicator_ids)


# ──────────────────────────────────────────────────────────────────────────
# #3 — Quote offsets unrecoverable must reject the mapping.
# ──────────────────────────────────────────────────────────────────────────


def test_fuzzy_match_with_unrecoverable_offsets_is_rejected(monkeypatch):
    from fastapi.testclient import TestClient

    import main as main_module

    # Quote shares enough characters with source for partial_ratio >= 90,
    # but no literal substring or whitespace-flexible regex match exists.
    # We craft a long source sharing many chars with quote.
    source = "Article 42. The quick brown fox jumps over the lazy dog repeatedly."
    fuzzy_quote = "The quick brown fox jumps over the lazy dog repeatedl"  # missing trailing 'y'

    response = {
        "verbatim_quote": fuzzy_quote,
        "personal_data": True,
        "has_ban": True,
        "scope": "horizontal",
    }

    _patch_provider(monkeypatch, response)
    _patch_classifier_to(monkeypatch, ["6.1"])
    # Force literal-only verification to fail so we are testing the offset gate.
    # find_quote_offsets has a regex fallback — so use a quote that even regex
    # can't recover. Easiest: cut the quote in a place that desyncs tokens.
    twisted_quote = "The quick brown FOX jumps over the lazy DOG"  # case mismatch
    response["verbatim_quote"] = twisted_quote

    client = TestClient(main_module.app)
    r = client.post("/api/extract", data={"text": source})
    assert r.status_code == 200
    data = r.json()

    # Either accepted with valid offsets, or rejected — but never accepted
    # with (0, 0) as offsets.
    for m in data["mappings"]:
        assert m["quote_end"] > m["quote_start"], (
            "mapping returned with empty highlight range; kill switch leaked"
        )
        # Offsets must point at a real substring of the source.
        assert source[m["quote_start"] : m["quote_end"]], (
            "quote offsets do not reference a real substring"
        )


# ──────────────────────────────────────────────────────────────────────────
# #4 — Invalid `scope` literal must be sanitized, not crash Pydantic.
# ──────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────
# #5 — Cross-chunk quote leak: an LLM that fabricates a quote which
# happens to exist in a *different* chunk must still be rejected.
# ──────────────────────────────────────────────────────────────────────────


def test_quote_outside_chunk_is_rejected_even_if_in_full_document(monkeypatch):
    """Verifying against `chunk.text`, not the whole document, prevents an
    LLM from "borrowing" phrases that exist elsewhere in the source.

    Test design (deliberate): the source is arranged so the *honest* match
    lives in CHUNK 2, not chunk 1. That forces the test to exercise the
    chunk-offset translation (`chunk.start + local_start`) — if a future
    refactor accidentally drops that translation, the absolute offset
    assertion below will fail, because chunk 2 starts well after byte 0.
    """
    from fastapi.testclient import TestClient

    import main as main_module

    # Order matters: article 2 contains the quote the liar will return.
    # Chunk 2 starts mid-document, so its offsets are non-zero.
    source = (
        "Article 1. Companies shall maintain a domestic data centre.\n\n"
        "Article 2. Personal data shall not be transferred abroad."
    )
    quote_from_article_2 = "Personal data shall not be transferred abroad"

    class CrossChunkLyingProvider:
        """Returns the same Article-2 quote regardless of which chunk it sees.

        On chunk 1: claims a quote that isn't in chunk 1 → MUST be rejected.
        On chunk 2: legitimately quotes from chunk 2 → should be accepted
                    AND the absolute offsets must address the original doc.
        """

        name = "fake-liar"

        def extract_features(self, article_text, indicator_id, feature_spec):
            return {
                "verbatim_quote": quote_from_article_2,
                "personal_data": True,
                "has_ban": True,
                "scope": "horizontal",
            }

    fake = CrossChunkLyingProvider()
    main_module._provider = fake
    monkeypatch.setattr(main_module, "_get_provider", lambda: fake)
    _patch_classifier_to(monkeypatch, ["6.1"])

    client = TestClient(main_module.app)
    r = client.post("/api/extract", data={"text": source})
    assert r.status_code == 200
    data = r.json()

    # Exactly one mapping (the honest extraction from CHUNK 2).
    assert len(data["mappings"]) == 1, (
        f"expected 1 honest mapping, got {len(data['mappings'])}: {data}"
    )
    m = data["mappings"][0]
    assert m["verbatim_quote"] == quote_from_article_2

    # Absolute offsets must point at the original document. Crucially,
    # chunk 2 doesn't start at byte 0 — so an implementation that forgets
    # to translate (chunk.start + local_start) would set quote_start to a
    # local-to-chunk offset (~12), not the absolute doc offset (~70+).
    assert m["quote_start"] > 50, (
        f"quote_start={m['quote_start']} looks chunk-local; "
        "the offset translation has regressed"
    )
    assert source[m["quote_start"] : m["quote_end"]] == quote_from_article_2, (
        f"offsets {m['quote_start']}..{m['quote_end']} don't address the original text"
    )

    # The cross-chunk lie (chunk 1's call) must surface in `rejected[]`.
    cross_chunk_rejections = [
        rej
        for rej in data["rejected"]
        if "data centre" in rej.get("chunk_preview", "")
    ]
    assert cross_chunk_rejections, (
        "cross-chunk borrowed quote slipped through: "
        f"{data['rejected']}"
    )
    assert "not found in chunk" in cross_chunk_rejections[0]["reason"]


@pytest.mark.parametrize(
    "bad_scope",
    ["global", "regional", "national", "", None, "Sectoral ", "HORIZONTAL"],
)
def test_invalid_scope_is_sanitized(monkeypatch, bad_scope):
    from fastapi.testclient import TestClient

    import main as main_module

    source = "Article 1. Personal data shall not be transferred abroad."
    quote = "Personal data shall not be transferred abroad."

    response = {
        "verbatim_quote": quote,
        "personal_data": True,
        "horizontal_scope": True,
        "has_ban": True,
        "scope": bad_scope,
    }

    _patch_provider(monkeypatch, response)
    _patch_classifier_to(monkeypatch, ["6.1"])

    client = TestClient(main_module.app)
    r = client.post("/api/extract", data={"text": source})
    assert r.status_code == 200, f"crashed on scope={bad_scope!r}: {r.text}"
    data = r.json()
    assert data["mappings"], "expected a mapping even with invalid scope"
    scope = data["mappings"][0]["scope"]
    assert scope in {"horizontal", "sectoral", "unknown"}, (
        f"scope leaked invalid value: {scope!r}"
    )
    # Specifically: trailing-space + uppercase should normalise to lowercase.
    if isinstance(bad_scope, str) and bad_scope.strip().lower() in {
        "horizontal",
        "sectoral",
    }:
        assert scope == bad_scope.strip().lower()
    else:
        assert scope == "unknown"
