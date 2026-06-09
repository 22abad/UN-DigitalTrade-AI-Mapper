"""Cross-jurisdiction legal terminology glossary for RDTII indicator matching.

Maps canonical RDTII terms to jurisdiction-specific synonyms across
India (DPDP), China (PIPL), Thailand (PDPA), EU (GDPR), and US/APAC.

Usage:
    from terminology import expand_phrases
    expanded = expand_phrases(["data controller", "dpo"])
    # → ["data controller", "dpo", "data fiduciary", "personal information processor",
    #     "privacy officer", "个人信息处理者", ...]
"""

# ── Canonical concept → jurisdiction-specific synonyms ────────────────────
# Each key is an RDTII canonical term; values are alternative phrasings
# found in specific jurisdictions.
_SYNONYM_MAP: dict[str, list[str]] = {
    # -- Data controller / processor (7.4, 7.1) --
    "data controller": [
        "data fiduciary",
        "personal information processor",
        "data handler",
        "个人信息处理者",
        "ผู้ควบคุมข้อมูลส่วนบุคคล",
        "người kiểm soát dữ liệu",
    ],
    "data processor": [
        "data fiduciary",
        "personal information processor",
        "data handler",
        "委托处理个人信息的",
        "ผู้ประมวลผลข้อมูลส่วนบุคคล",
        "người xử lý dữ liệu",
    ],

    # -- Data subject / principal (7.1) --
    "data subject": [
        "data principal",
        "个人信息主体",
        "เจ้าของข้อมูลส่วนบุคคล",
        "chủ thể dữ liệu",
    ],
    "数据主体": [
        "data subject",
        "data principal",
    ],

    # -- Personal data / information (7.1) --
    "personal data": [
        "personal information",
        "personally identifiable information",
        "pii",
        "个人信息",
        "ข้อมูลส่วนบุคคล",
        "dữ liệu cá nhân",
        "thông tin cá nhân",
    ],
    "personal information": [
        "personal data",
        "personally identifiable information",
        "pii",
        "个人信息",
        "ข้อมูลส่วนบุคคล",
    ],

    # -- Consent (6.4, 7.1) --
    "consent": [
        "explicit consent",
        "unambiguous consent",
        "freely given consent",
        "specific consent",
        "informed consent",
        "同意",
        "ความยินยอม",
        "sự đồng ý",
    ],

    # -- DPO / privacy officer (7.4) --
    "data protection officer": [
        "privacy officer",
        "data privacy officer",
        "数据保护官",
        "เจ้าหน้าที่คุ้มครองข้อมูลส่วนบุคคล",
        "nhân viên bảo vệ dữ liệu",
    ],
    "dpo": [
        "privacy officer",
        "data protection officer",
        "数据保护官",
        "nhân viên bảo vệ dữ liệu",
    ],

    # -- DPIA / impact assessment (7.4) --
    "impact assessment": [
        "data protection impact assessment",
        "privacy impact assessment",
        "data privacy impact assessment",
        "个人信息保护影响评估",
        "การประเมินผลกระทบ",
        "đánh giá tác động",
    ],

    # -- Data breach (7.1, 7.5) --
    "data breach": [
        "personal data breach",
        "security incident",
        "data leak",
        "数据泄露",
        "การละเมิดข้อมูล",
        "vi phạm dữ liệu",
    ],

    # -- Cross-border transfer (6.1, 6.4) --
    "cross-border transfer": [
        "cross-border data flow",
        "international transfer",
        "transborder data flow",
        "跨境数据流动",
        "跨境传输",
        "การโอนย้ายข้อมูลข้ามพรมแดน",
        "chuyển dữ liệu xuyên biên giới",
    ],
    "data localization": [
        "data localisation",
        "local storage requirement",
        "境内存储",
        "localisation",
    ],

    # -- Adequacy / safeguards (6.4) --
    "adequacy decision": [
        "adequacy finding",
        "adequate level of protection",
        "充分性认定",
        "adequate safeguard",
    ],
    "standard contractual clauses": [
        "model clauses",
        "standard data protection clauses",
        "标准合同条款",
        "ข้อสัญญามาตรฐาน",
    ],

    # -- Regulatory authority (7.5, 7.4) --
    "supervisory authority": [
        "data protection authority",
        "commissioner",
        "competent authority",
        "regulatory authority",
        "监管机构",
        "หน่วยงานผู้มีอำนาจ",
        "cơ quan có thẩm quyền",
    ],

    # -- Registration / notification (7.4) --
    "register of processing": [
        "record of processing",
        "processing register",
        "登记",
        "ทะเบียน",
    ],

    # -- National security / public interest (7.5) --
    "national security": [
        "国家安全",
        "ความมั่นคงของชาติ",
        "an ninh quốc gia",
    ],
    "public order": [
        "public interest",
        "ordre public",
        "公共秩序",
        "ความสงบเรียบร้อย",
        "trật tự công cộng",
    ],
}


def expand_phrases(phrases: list[str]) -> list[str]:
    """Expand a list of indicator keywords with jurisdiction-specific synonyms.

    Each phrase is looked up in the synonym map. If found, all synonyms
    for that canonical concept are appended. The original phrases are
    kept so existing matches remain unchanged.

    Args:
        phrases: Original indicator keyword list.

    Returns:
        Expanded list with jurisdiction synonyms appended.
    """
    result = list(phrases)
    seen: set[str] = set(p.lower() for p in phrases)
    for phrase in phrases:
        lowered = phrase.lower()
        synonyms = _SYNONYM_MAP.get(lowered) or _SYNONYM_MAP.get(phrase, [])
        for syn in synonyms:
            if syn.lower() not in seen:
                result.append(syn)
                seen.add(syn.lower())
    return result


def classify_indicator_expanded(article_text: str) -> list[str]:
    """Same as classifier.classify_indicator but with expanded jurisdiction keywords.

    This mirrors the original classify_indicator logic but feeds the
    indicator phrases through expand_phrases() first so that jurisdiction-
    specific terms (e.g. "data fiduciary" for India) also trigger matches.

    Note: For production use, prefer integrating expand_phrases directly
    into the classifier's _INDICATOR_PHRASES at module load time:
        from terminology import expand_phrases
        _INDICATOR_PHRASES = {k: expand_phrases(v) for k, v in _ORIGINAL_PHRASES.items()}
    """
    from classifier import _INDICATOR_PHRASES, _phrase_in_text as _match

    if not article_text or not article_text.strip():
        return []
    lowered = article_text.lower()
    matched: set[str] = set()
    for indicator, phrases in _INDICATOR_PHRASES.items():
        expanded = expand_phrases(phrases)
        for phrase in expanded:
            if _match(phrase.lower(), lowered):
                matched.add(indicator)
                break
    return sorted(matched)
