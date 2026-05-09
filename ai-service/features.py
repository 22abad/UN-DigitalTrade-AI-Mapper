"""Feature specifications per RDTII 2.1 indicator.

Each indicator's scoring rule (in `scoring/`) consumes a structured features dict.
The LLM provider's job is to read an article and emit these features —
nothing else. The deterministic scorer then applies the rule from the RDTII
2.1 guide to map features → score (0 / 0.5 / 1).

The `description` strings double as LLM prompt material: the provider injects
them into the extraction prompt so the LLM knows what to look for.

Sources:
- ESCAP RDTII 2.1 Guide, Chapter 3, Pillars 6 & 7
- Cross-checked against CHN-RDTII.xlsx (sample data)
"""

from __future__ import annotations

# Each indicator's spec maps feature_name -> (type_hint, description)
INDICATOR_FEATURES: dict[str, dict[str, dict[str, str]]] = {
    # ── Pillar 6: Cross-border data policies ─────────────────────────
    "1.1": {"tariff_rate": {"type": "float", "description": "Applicable tariff rate"}},
    "2.1": {"procurement_preference": {"type": "bool", "description": "Local preference in procurement?"}},
    "3.1": {"foreign_equity_limit": {"type": "float", "description": "FDI equity limit"}},
    "4.1": {"ip_protection_level": {"type": "str", "description": "IP protection level"}},
    "5.1": {"telecom_competition": {"type": "bool", "description": "Telecom market competition"}},
    "6.1": {
        "personal_data": {
            "type": "bool",
            "description": "Does the measure apply to personal data (name, ID, IP address, health, etc.)?",
        },
        "horizontal_scope": {
            "type": "bool",
            "description": "Does it apply across all sectors (horizontal), as opposed to a single sector?",
        },
        "has_ban": {
            "type": "bool",
            "description": "Does the measure impose an outright ban on cross-border data transfer?",
        },
        "has_local_processing": {
            "type": "bool",
            "description": "Does it require data to be processed within the country?",
        },
        "applies_to_government_data_only": {
            "type": "bool",
            "description": "Is the measure limited to government data only? (If true, indicator is excluded.)",
        },
        "num_economies_affected": {
            "type": "int",
            "description": "Number of foreign economies affected (1 = bilateral, 2+ = multilateral).",
        },
    },
    "6.2": {
        "personal_data": {"type": "bool", "description": "Applies to personal data?"},
        "horizontal_scope": {"type": "bool", "description": "Horizontal across all sectors?"},
        "has_local_storage": {
            "type": "bool",
            "description": "Mandates that a copy of certain data be stored within the country?",
        },
        "applies_to_government_data_only": {"type": "bool", "description": "Only government data?"},
    },
    "6.3": {
        "has_infrastructure_req": {
            "type": "bool",
            "description": "Mandates establishment of a local data centre / dedicated physical infrastructure?",
        },
        "applies_to_government_data_only": {"type": "bool", "description": "Only government data?"},
    },
    "6.4": {
        "personal_data": {"type": "bool", "description": "Applies to personal data?"},
        "horizontal_scope": {"type": "bool", "description": "Horizontal across all sectors?"},
        "has_conditional_flow": {
            "type": "bool",
            "description": "Imposes conditions on cross-border transfer (consent, adequacy, gov approval, SCC)?",
        },
    },
    "6.5": {
        "has_binding_agreement": {
            "type": "bool",
            "description": "Is the country signatory to a binding agreement on cross-border data flows (CPTPP, DEPA, RCEP Art. 12.15, etc.)?",
        },
    },
    "7.1": {
        "has_comprehensive_framework": {
            "type": "bool",
            "description": "Does the country have a comprehensive cross-sectoral data protection law?",
        },
        "has_sectoral_framework_only": {
            "type": "bool",
            "description": "Only sectoral data protection laws exist (no horizontal framework)?",
        },
    },
    "7.2": {
        "has_dedicated_cybersecurity_law": {
            "type": "bool",
            "description": "Dedicated horizontal cybersecurity legal framework exists?",
        },
        "has_sectoral_cybersecurity_only": {
            "type": "bool",
            "description": "Only sectoral or non-dedicated cybersecurity provisions?",
        },
    },
    "7.3": {
        "has_minimum_retention_period": {
            "type": "bool",
            "description": "Imposes a minimum data retention period (days/months/years explicitly stated)?",
        },
        "applies_to_government_data_only": {"type": "bool", "description": "Only government data?"},
    },
    "7.4": {
        "has_dpo_requirement": {
            "type": "bool",
            "description": "Requires firms to appoint a Data Protection Officer (DPO)?",
        },
        "has_dpia_requirement": {
            "type": "bool",
            "description": "Requires firms to perform a Data Protection Impact Assessment (DPIA)?",
        },
        "horizontal_scope": {"type": "bool", "description": "Horizontal across all sectors?"},
    },
    "7.5": {
        "has_government_access_without_judicial_oversight": {
            "type": "bool",
            "description": "Allows government access to personal data without judicial warrant / independent oversight?",
        },
    },
    "8.1": {"intermediary_liability": {"type": "str", "description": "Liability of intermediaries"}},
    "9.1": {"content_restriction": {"type": "str", "description": "Restriction on content"}},
    "10.1": {"non_tariff_measure": {"type": "str", "description": "Non-tariff measure type"}},
    "11.1": {"standards_interoperability": {"type": "bool", "description": "Standards interoperability"}},
    "12.1": {"e_signature_validity": {"type": "bool", "description": "E-signature validity"}}
}


def get_feature_spec(indicator_id: str) -> dict[str, dict[str, str]]:
    """Return the feature spec for an indicator, or empty dict if unknown."""
    return INDICATOR_FEATURES.get(indicator_id, {})


def list_supported_indicators() -> list[str]:
    """Return all indicator IDs the system can handle."""
    return list(INDICATOR_FEATURES.keys())
