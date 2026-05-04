"""Tests for verification.verify_quote and verification.find_quote_offsets."""

from __future__ import annotations

from verification import find_quote_offsets, verify_quote


# ── verify_quote ───────────────────────────────────────────────────


def test_strict_substring_success():
    original = "The quick brown fox jumps over the lazy dog."
    assert verify_quote("quick brown fox", original) is True


def test_strict_substring_failure():
    original = "The quick brown fox jumps over the lazy dog."
    assert verify_quote("slow green turtle", original, fuzzy=False) is False


def test_whitespace_normalization_extra_spaces():
    original = "Personal data must  not   be transferred  abroad."
    quote = "Personal data must not be transferred abroad."
    assert verify_quote(quote, original) is True


def test_whitespace_normalization_newlines_and_tabs():
    original = "Article 5\n\tof the\nPersonal Information Protection Law"
    quote = "Article 5 of the Personal Information Protection Law"
    assert verify_quote(quote, original) is True


def test_unicode_nfc_normalization():
    """Composed (é = U+00E9) vs decomposed (e + U+0301) must match."""
    composed = "café society"  # é as single codepoint
    decomposed = "café society"  # e + combining acute
    assert verify_quote(composed, decomposed) is True
    assert verify_quote(decomposed, composed) is True


def test_fuzzy_match_one_char_ocr_substitution():
    """An OCR pipe-for-l substitution should still match with fuzzy=True."""
    original = "Article 5 of the Personal Information Protection Law of 2021"
    quote = "Artic|e 5 of the Personal Information Protection Law"
    assert verify_quote(quote, original, fuzzy=True) is True


def test_fuzzy_disabled_rejects_ocr_substitution_below_strict():
    original = "Article 5 of the Personal Information Protection Law of 2021"
    quote = "Artic|e 5 of the Personal Information Protection Law"
    assert verify_quote(quote, original, fuzzy=False) is False


def test_fuzzy_match_fails_on_completely_different_text():
    original = "The annual rainfall in the region exceeds 2000 millimetres."
    quote = "Personal data shall not be transferred abroad without consent."
    assert verify_quote(quote, original, fuzzy=True) is False


def test_empty_inputs_return_false():
    assert verify_quote("", "anything") is False
    assert verify_quote("anything", "") is False
    assert verify_quote("", "") is False


# ── find_quote_offsets ────────────────────────────────────────────


def test_find_quote_offsets_returns_correct_indices():
    original = "The quick brown fox jumps over the lazy dog."
    start, end = find_quote_offsets("brown fox", original)
    assert (start, end) == (10, 19)
    assert original[start:end] == "brown fox"


def test_find_quote_offsets_not_found():
    original = "Hello world."
    assert find_quote_offsets("goodbye", original) == (-1, -1)


def test_find_quote_offsets_flexible_whitespace():
    """When the quote and source differ in spacing, we still return offsets
    that point into the ORIGINAL string (not the normalized one)."""
    original = "Article  5\nof the Law"
    start, end = find_quote_offsets("Article 5 of the Law", original)
    assert start == 0
    assert end == len(original)
    assert original[start:end] == original


def test_find_quote_offsets_empty_inputs():
    assert find_quote_offsets("", "anything") == (-1, -1)
    assert find_quote_offsets("anything", "") == (-1, -1)
    assert find_quote_offsets("   ", "anything") == (-1, -1)
