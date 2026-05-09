"""Indicator classifier — short-lists which RDTII 2.1 indicators an article touches."""

from __future__ import annotations

# Unified dictionary for all supported languages
_INDICATOR_PHRASES: dict[str, list[str]] = {
    "6.1": [
        "transfer abroad", "transferred abroad", "transferring abroad",
        "transfer data abroad", "transferred data abroad",
        "transferring data abroad", "transferring personal data abroad",
        "transferring personal information abroad",
        "providing personal information abroad",
        "provide personal information outside",
        "provided outside the territory",
        "outbound transfer", "cross-border transfer",
        "ban on transfer", "shall not transfer",
        "process locally", "data localization", "data localisation",
        "xử lý tại chỗ", "pemrosesan", "proses", "ห้ามโอนย้ายไปต่างประเทศ",
        "出境", "境外", "境内处理", "禁止传输", "本地处理"
    ],
    "6.2": [
        "store data within", "local storage", "stored locally",
        "lưu trữ dữ liệu", "disimpan", "penyimpanan", "เก็บรักษาไว้",
        "境内存储", "本地存储"
    ],
    "6.3": [
        "local data centre", "local data center", "data center within", "data centre within",
        "local server", "physical infrastructure", "establish a server",
        "服务器", "数据中心"
    ],
    "6.4": [
        "consent", "adequacy", "standard contract", "prior authorization", "security assessment",
        "同意", "充分性", "标准合同", "安全评估"
    ],
    "6.5": [
        "trade agreement", "depa", "cptpp", "rcep", "free flow of data",
        "自由贸易协定", "数字经济伙伴关系"
    ],
    "7.1": [
        "personal data protection", "privacy law", "data protection act",
        "luật bảo vệ dữ liệu", "undang-undang perlindungan data",
        "个人信息保护法", "隐私", "数据主体"
    ],
    "7.2": [
        "cybersecurity", "cybercrime", "an ninh mạng", "keamanan siber",
        "网络安全", "网络犯罪"
    ],
    "7.3": [
        "retain", "retention period", "minimum period",
        "thời gian lưu trữ", "periode retensi",
        "保留", "至少保存", "保留期"
    ],
    "7.4": [
        "data protection officer", "dpo", "dpia", "impact assessment",
        "数据保护官", "影响评估"
    ],
    "7.5": [
        "law enforcement access", "without warrant", "surveillance",
        "执法", "国家安全", "监视"
    ],
}

def classify_indicator(article_text: str) -> list[str]:
    if not article_text or not article_text.strip():
        return []

    lowered = article_text.lower()
    matched: set[str] = set()

    for indicator, phrases in _INDICATOR_PHRASES.items():
        for phrase in phrases:
            if phrase.lower() in lowered:
                matched.add(indicator)
                break

    return sorted(matched)
