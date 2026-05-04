"""Tests for classifier.classify_indicator."""

from __future__ import annotations

from classifier import classify_indicator


# ── Pillar 6 ────────────────────────────────────────────────────


def test_p6_1_data_localization():
    text = "The new measure imposes a strict data localization requirement."
    assert "6.1" in classify_indicator(text)


def test_p6_2_local_storage():
    text = "Operators must keep a copy of data in local storage at all times."
    assert "6.2" in classify_indicator(text)


def test_p6_3_local_server():
    text = "Each licensee shall establish a server inside the national territory."
    assert "6.3" in classify_indicator(text)


def test_p6_4_security_assessment():
    text = "Cross-border transfers must pass a national security assessment."
    assert "6.4" in classify_indicator(text)


def test_p6_5_trade_agreement():
    text = "The provisions of the CPTPP trade agreement allow free flow of data."
    assert "6.5" in classify_indicator(text)


# ── Pillar 7 ────────────────────────────────────────────────────


def test_p7_1_personal_data_protection():
    text = "The bill is the country's first comprehensive personal data protection statute."
    assert "7.1" in classify_indicator(text)


def test_p7_2_cybersecurity():
    text = "A new cybersecurity law was enacted to address emerging cyber threats."
    assert "7.2" in classify_indicator(text)


def test_p7_3_retention_period():
    text = "Telecommunications operators shall observe a minimum retention period of 12 months."
    assert "7.3" in classify_indicator(text)


def test_p7_4_dpo():
    text = "Each controller must appoint a Data Protection Officer (DPO)."
    assert "7.4" in classify_indicator(text)


def test_p7_5_law_enforcement_access():
    text = "The statute grants law enforcement access to subscriber records without warrant."
    assert "7.5" in classify_indicator(text)


# ── Multilingual / edge cases ─────────────────────────────────


def test_chinese_personal_information_protection():
    text = "本法是中华人民共和国个人信息保护法的核心条款。"
    assert "7.1" in classify_indicator(text)


def test_chinese_cybersecurity():
    text = "网络安全法对关键信息基础设施提出了新的要求。"
    assert "7.2" in classify_indicator(text)


def test_chinese_data_export_triggers_6_1():
    text = "个人信息出境需要满足相关条件。"
    assert "6.1" in classify_indicator(text)


def test_empty_input_returns_empty_list():
    assert classify_indicator("") == []
    assert classify_indicator("   \n\t ") == []


def test_no_keyword_match_returns_empty_list():
    text = "The annual rainfall in the region exceeds 2000 millimetres each year."
    assert classify_indicator(text) == []


def test_multiple_indicators_triggered():
    text = (
        "Personal information processors must obtain individual consent before "
        "transferring data abroad. The law also establishes a national "
        "cybersecurity regime and creates a comprehensive personal data "
        "protection framework."
    )
    result = classify_indicator(text)
    assert "6.1" in result  # transferring data abroad
    assert "6.4" in result  # consent
    assert "7.1" in result  # personal data protection
    assert "7.2" in result  # cybersecurity


def test_result_is_sorted_and_unique():
    text = (
        "Cybersecurity. cybersecurity. Network security. "
        "Personal data protection. Privacy law."
    )
    result = classify_indicator(text)
    assert result == sorted(set(result))
    assert "7.1" in result
    assert "7.2" in result
