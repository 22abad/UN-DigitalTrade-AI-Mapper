"""Indicator classifier — short-lists which RDTII 2.1 indicators an article touches.

The deterministic scorer in `scoring/` is comparatively expensive (LLM-driven
feature extraction). To avoid running it against every indicator on every
article, this classifier filters the indicator set down to a small candidate
list using multilingual keyword/phrase matching.

Languages: English (case-insensitive) + Simplified Chinese (exact match).
Returns a sorted, de-duplicated list of indicator IDs. Empty list if no
trigger phrases hit.
"""

from __future__ import annotations

# Per-indicator trigger phrases. English phrases are matched
# case-insensitively (the article is lower-cased before scanning); Chinese
# phrases are matched against the original text exactly.
#
# Note on inflected forms: the upstream spec specified bare "transfer abroad"
# for 6.1, but real legal text frequently uses "transferred abroad" /
# "transferring abroad" / "transferring data abroad". Those have been added
# so e.g. "Personal data must not be transferred abroad" classifies into 6.1.
_INDICATOR_PHRASES_EN: dict[str, list[str]] = {
    "6.1": [
        "transfer abroad",
        "transferred abroad",
        "transferring abroad",
        "transferring data abroad",
        "ban on transfer",
        "shall not transfer",
        "process locally",
        "data localization",
        "data localisation",
    ],
    "6.2": [
        "store data within",
        "local storage",
        "stored locally",
        "copy of data",
        "stored in",
    ],
    "6.3": [
        "local data centre",
        "local data center",
        "data center within",
        "data centre within",
        "local server",
        "physical infrastructure",
        "establish a server",
    ],
    "6.4": [
        "consent",
        "adequacy",
        "standard contract",
        "prior authorization",
        "prior authorisation",
        "security assessment",
    ],
    "6.5": [
        "trade agreement",
        "depa",
        "cptpp",
        "rcep",
        "free flow of data",
        "binding commitment",
    ],
    "7.1": [
        "personal data protection",
        "privacy law",
        "data protection act",
        "rights of data subject",
    ],
    "7.2": [
        "cybersecurity",
        "cybercrime",
        "computer security",
        "network security",
    ],
    "7.3": [
        "retain",
        "retention period",
        "minimum period",
        "maintain records",
        "retain for at least",
    ],
    "7.4": [
        "data protection officer",
        "dpo",
        "dpia",
        "impact assessment",
        "appoint a person responsible",
    ],
    "7.5": [
        "law enforcement access",
        "authority access",
        "state security",
        "intelligence agency",
        "without warrant",
        "surveillance",
    ],
}

_INDICATOR_PHRASES_ZH: dict[str, list[str]] = {
    "6.1": ["出境", "境内处理", "禁止传输", "本地处理"],
    "6.2": ["境内存储", "本地存储"],
    "6.3": ["服务器", "数据中心", "本地服务器"],
    "6.4": ["同意", "充分性", "标准合同", "安全评估", "事先批准"],
    "6.5": ["自由贸易协定", "数字经济伙伴关系"],
    "7.1": ["个人信息保护法", "隐私", "数据主体"],
    "7.2": ["网络安全", "网络犯罪"],
    "7.3": ["保留", "至少保存", "保留期"],
    "7.4": ["数据保护官", "影响评估", "负责人"],
    "7.5": ["执法", "国家安全", "监视", "情报", "公安机关"],
}


def classify_indicator(article_text: str) -> list[str]:
    """Return RDTII 2.1 indicator IDs that this article potentially touches.

    Sorted, unique, possibly empty.
    """
    if not article_text or not article_text.strip():
        return []

    lowered = article_text.lower()
    matched: set[str] = set()

    for indicator, phrases in _INDICATOR_PHRASES_EN.items():
        for phrase in phrases:
            if phrase in lowered:
                matched.add(indicator)
                break

    for indicator, phrases in _INDICATOR_PHRASES_ZH.items():
        if indicator in matched:
            continue
        for phrase in phrases:
            if phrase in article_text:
                matched.add(indicator)
                break

    return sorted(matched)
