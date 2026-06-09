"""Indicator classifier — short-lists which RDTII 2.1 indicators an article touches."""

from __future__ import annotations

# Unified dictionary for all 12 supported RDTII indicators
_INDICATOR_PHRASES = {
    "1.1": ["tariff", "customs duty", "tax", "关税", "贸易防御"],
    "2.1": [
        "public procurement", "government tender", 
        "การจัดซื้อจัดจ้าง", "พัสดุ", "คณะกรรมการ", 
        "政府采购", "招投标"
    ],
    "3.1": [
        "foreign direct investment", "FDI", "foreign ownership",
        "外商投资", "外资", "外商投资法"
    ],
    "4.1": ["intellectual property", "patent", "copyright", "知识产权", "专利", "著作权"],
    "5.1": ["telecom", "broadband", "frequency", "电信", "宽带"],
    "5.3": [
        "government equity", "government ownership", "state-owned",
        "majority stake", "government share", "public sector",
        "telecom", "operator", "telecommunication service provider",
        "政府持股", "国有", "国有控股", "控股",
    ],
    "6.1": [
        "transfer abroad", "transferred abroad", "transferring abroad", "transferring data abroad", "ban on transfer",
        "process locally", "data localization", "data localisation",
        "xử lý tại chỗ", "pemrosesan", "proses", "ห้ามโอนย้ายไปต่างประเทศ",
        "出境", "境外", "境内处理", "禁止传输", "本地处理",
        "transfer personal data", "transfer of personal data", "restrict transfer",
        "prohibition of transfer", "no transfer", "shall not transfer"
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
        " согласие", "充分性", "标准合同", "安全评估",
        "data exporter", "data importer", "binding corporate", "adequate level of protection",
        "appropriate safeguard", "contractual clause", "transfer mechanism"
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
        "数据保护官", "影响评估",
        "compliance officer", "privacy officer", "registration with",
        "data controller", "data processor", "register of processing",
        "annual audit", "data audit", "compliance audit"
    ],
    "7.5": [
        "law enforcement access", "without warrant", "surveillance",
        "执法", "国家安全", "监视",
        "public interest", "public authority access", "government access",
        "national security", "public order", "disclosure to law enforcement",
        "obligation to notify", "competent authority", "regulatory authority"
    ],
    "8.1": ["intermediary liability", "safe harbor", "互联网平台责任", "责任承担"],
    "9.1": ["online content", "illegal content", "在线内容", "违法内容"],
    "10.1": ["non-tariff measure", "trade restriction", "非关税措施", "贸易限制"],
    "11.1": ["standards", "conformity assessment", "技术标准", "合格评定"],
    "12.1": ["online sales", "e-signature", "在线销售", "电子签名"]
}

def _phrase_in_text(phrase: str, text: str) -> bool:
    if phrase in text:
        return True
    words = phrase.split()
    if len(words) > 1:
        return all(w in text for w in words)
    return False

def classify_indicator(article_text: str) -> list[str]:
    if not article_text or not article_text.strip():
        return []

    lowered = article_text.lower()
    matched: set[str] = set()

    for indicator, phrases in _INDICATOR_PHRASES.items():
        for phrase in phrases:
            if _phrase_in_text(phrase.lower(), lowered):
                matched.add(indicator)
                break

    return sorted(matched)
