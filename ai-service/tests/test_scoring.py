"""Tests for the deterministic scoring functions (Pillars 6 & 7).

Each indicator gets at least 3 cases covering:
    - the high-score path (1.0)
    - a mid-score path where applicable (0.5 / 0.25)
    - the low-score / "no requirement" path (0.0)
    - the government-data exclusion where applicable

Indicator IDs are exercised both via the per-indicator function and via
the top-level `score_indicator` dispatcher to verify wiring.
"""

from __future__ import annotations

import pytest

from scoring import score_indicator
from scoring.pillar_6 import (
    score_6_1,
    score_6_2,
    score_6_3,
    score_6_4,
    score_6_5,
)
from scoring.pillar_7 import (
    score_7_1,
    score_7_2,
    score_7_3,
    score_7_4,
    score_7_5,
)


# ──────────────────────────────────────────────────────────────────────────
# Pillar 6
# ──────────────────────────────────────────────────────────────────────────


class TestIndicator6_1:
    """Ban & local processing requirements."""

    def test_personal_data_alone_scores_1(self):
        # Locks in the verification command behaviour: personal_data=True
        # alone is enough for score 1, even without an explicit ban /
        # local-processing flag.
        assert score_6_1({"personal_data": True}) == 1.0

    def test_personal_data_with_ban_scores_1(self):
        assert score_6_1({"personal_data": True, "has_ban": True}) == 1.0

    def test_horizontal_scope_with_local_processing_scores_1(self):
        assert (
            score_6_1({"horizontal_scope": True, "has_local_processing": True}) == 1.0
        )

    def test_two_economies_affected_scores_1(self):
        assert (
            score_6_1(
                {
                    "has_ban": True,
                    "num_economies_affected": 2,
                    "personal_data": False,
                    "horizontal_scope": False,
                }
            )
            == 1.0
        )

    def test_non_personal_specific_sector_scores_half(self):
        assert (
            score_6_1(
                {
                    "has_local_processing": True,
                    "personal_data": False,
                    "horizontal_scope": False,
                    "num_economies_affected": 1,
                }
            )
            == 0.5
        )

    def test_no_requirement_scores_zero(self):
        assert (
            score_6_1({"has_ban": False, "has_local_processing": False}) == 0.0
        )

    def test_government_data_only_excluded(self):
        # Even with personal data + ban, gov-only excludes the indicator.
        assert (
            score_6_1(
                {
                    "applies_to_government_data_only": True,
                    "personal_data": True,
                    "has_ban": True,
                }
            )
            == 0.0
        )

    def test_empty_features_scores_zero(self):
        assert score_6_1({}) == 0.0


class TestIndicator6_2:
    """Local storage requirements."""

    def test_personal_data_with_storage_scores_1(self):
        assert score_6_2({"personal_data": True, "has_local_storage": True}) == 1.0

    def test_horizontal_scope_with_storage_scores_1(self):
        assert (
            score_6_2({"horizontal_scope": True, "has_local_storage": True}) == 1.0
        )

    def test_sectoral_non_personal_scores_half(self):
        assert (
            score_6_2(
                {
                    "has_local_storage": True,
                    "personal_data": False,
                    "horizontal_scope": False,
                }
            )
            == 0.5
        )

    def test_no_storage_requirement_scores_zero(self):
        assert score_6_2({"has_local_storage": False, "personal_data": True}) == 0.0

    def test_government_data_only_excluded(self):
        assert (
            score_6_2(
                {
                    "applies_to_government_data_only": True,
                    "has_local_storage": True,
                    "personal_data": True,
                }
            )
            == 0.0
        )


class TestIndicator6_3:
    """Infrastructure requirements (binary)."""

    def test_with_infrastructure_scores_1(self):
        assert score_6_3({"has_infrastructure_req": True}) == 1.0

    def test_without_infrastructure_scores_zero(self):
        assert score_6_3({"has_infrastructure_req": False}) == 0.0

    def test_government_data_only_excluded(self):
        assert (
            score_6_3(
                {
                    "applies_to_government_data_only": True,
                    "has_infrastructure_req": True,
                }
            )
            == 0.0
        )

    def test_empty_features_scores_zero(self):
        assert score_6_3({}) == 0.0


class TestIndicator6_4:
    """Conditional flow regimes."""

    def test_personal_data_with_condition_scores_1(self):
        assert (
            score_6_4({"personal_data": True, "has_conditional_flow": True}) == 1.0
        )

    def test_horizontal_scope_with_condition_scores_1(self):
        assert (
            score_6_4({"horizontal_scope": True, "has_conditional_flow": True}) == 1.0
        )

    def test_sectoral_non_personal_scores_half(self):
        assert (
            score_6_4(
                {
                    "has_conditional_flow": True,
                    "personal_data": False,
                    "horizontal_scope": False,
                }
            )
            == 0.5
        )

    def test_no_condition_scores_zero(self):
        assert (
            score_6_4({"has_conditional_flow": False, "personal_data": True}) == 0.0
        )


class TestIndicator6_5:
    """Not in agreement with binding commitments (inverted score)."""

    def test_no_binding_agreement_scores_1(self):
        assert score_6_5({"has_binding_agreement": False}) == 1.0

    def test_has_binding_agreement_scores_zero(self):
        assert score_6_5({"has_binding_agreement": True}) == 0.0

    def test_missing_feature_defaults_to_no_agreement(self):
        # Missing => falsy => "no agreement signed" => high score (gap).
        assert score_6_5({}) == 1.0


# ──────────────────────────────────────────────────────────────────────────
# Pillar 7
# ──────────────────────────────────────────────────────────────────────────


class TestIndicator7_1:
    """Lack of comprehensive data protection framework."""

    def test_comprehensive_framework_scores_zero(self):
        assert score_7_1({"has_comprehensive_framework": True}) == 0.0

    def test_sectoral_only_scores_half(self):
        assert (
            score_7_1(
                {
                    "has_comprehensive_framework": False,
                    "has_sectoral_framework_only": True,
                }
            )
            == 0.5
        )

    def test_no_framework_scores_1(self):
        assert (
            score_7_1(
                {
                    "has_comprehensive_framework": False,
                    "has_sectoral_framework_only": False,
                }
            )
            == 1.0
        )

    def test_comprehensive_takes_precedence_over_sectoral(self):
        # If both flags are True, comprehensive wins (0).
        assert (
            score_7_1(
                {
                    "has_comprehensive_framework": True,
                    "has_sectoral_framework_only": True,
                }
            )
            == 0.0
        )


class TestIndicator7_2:
    """Lack of dedicated cybersecurity framework."""

    def test_dedicated_law_scores_zero(self):
        assert score_7_2({"has_dedicated_cybersecurity_law": True}) == 0.0

    def test_sectoral_only_scores_half(self):
        assert (
            score_7_2(
                {
                    "has_dedicated_cybersecurity_law": False,
                    "has_sectoral_cybersecurity_only": True,
                }
            )
            == 0.5
        )

    def test_no_law_scores_1(self):
        assert (
            score_7_2(
                {
                    "has_dedicated_cybersecurity_law": False,
                    "has_sectoral_cybersecurity_only": False,
                }
            )
            == 1.0
        )


class TestIndicator7_3:
    """Minimum data retention period."""

    def test_minimum_period_scores_1(self):
        assert score_7_3({"has_minimum_retention_period": True}) == 1.0

    def test_no_minimum_period_scores_zero(self):
        assert score_7_3({"has_minimum_retention_period": False}) == 0.0

    def test_government_data_only_excluded(self):
        assert (
            score_7_3(
                {
                    "applies_to_government_data_only": True,
                    "has_minimum_retention_period": True,
                }
            )
            == 0.0
        )


class TestIndicator7_4:
    """DPIA / DPO requirements."""

    def test_horizontal_dpo_scores_1(self):
        assert (
            score_7_4({"has_dpo_requirement": True, "horizontal_scope": True}) == 1.0
        )

    def test_horizontal_dpo_with_dpia_scores_1(self):
        assert (
            score_7_4(
                {
                    "has_dpo_requirement": True,
                    "has_dpia_requirement": True,
                    "horizontal_scope": True,
                }
            )
            == 1.0
        )

    def test_sectoral_dpo_scores_half(self):
        assert (
            score_7_4({"has_dpo_requirement": True, "horizontal_scope": False}) == 0.5
        )

    def test_sectoral_dpo_with_dpia_scores_half(self):
        assert (
            score_7_4(
                {
                    "has_dpo_requirement": True,
                    "has_dpia_requirement": True,
                    "horizontal_scope": False,
                }
            )
            == 0.5
        )

    def test_only_dpia_scores_quarter(self):
        # Theoretical edge case from the guide.
        assert (
            score_7_4(
                {
                    "has_dpo_requirement": False,
                    "has_dpia_requirement": True,
                }
            )
            == 0.25
        )

    def test_no_requirement_scores_zero(self):
        assert score_7_4({}) == 0.0


class TestIndicator7_5:
    """Government access to personal data without judicial oversight."""

    def test_unrestricted_gov_access_scores_1(self):
        assert (
            score_7_5({"has_government_access_without_judicial_oversight": True})
            == 1.0
        )

    def test_no_unrestricted_access_scores_zero(self):
        assert (
            score_7_5({"has_government_access_without_judicial_oversight": False})
            == 0.0
        )

    def test_empty_features_scores_zero(self):
        assert score_7_5({}) == 0.0


# ──────────────────────────────────────────────────────────────────────────
# Dispatcher wiring
# ──────────────────────────────────────────────────────────────────────────


class TestDispatcher:
    """Sanity check that score_indicator() routes correctly."""

    @pytest.mark.parametrize(
        "indicator_id,features,expected",
        [
            ("6.1", {"personal_data": True, "has_ban": True}, 1.0),
            ("6.2", {"has_local_storage": True, "personal_data": True}, 1.0),
            ("6.3", {"has_infrastructure_req": True}, 1.0),
            ("6.4", {"has_conditional_flow": True, "horizontal_scope": True}, 1.0),
            ("6.5", {"has_binding_agreement": False}, 1.0),
            ("7.1", {"has_comprehensive_framework": True}, 0.0),
            ("7.2", {"has_dedicated_cybersecurity_law": True}, 0.0),
            ("7.3", {"has_minimum_retention_period": True}, 1.0),
            (
                "7.4",
                {"has_dpo_requirement": True, "horizontal_scope": True},
                1.0,
            ),
            (
                "7.5",
                {"has_government_access_without_judicial_oversight": True},
                1.0,
            ),
        ],
    )
    def test_dispatcher_routes_correctly(self, indicator_id, features, expected):
        assert score_indicator(indicator_id, features) == expected

    def test_unsupported_indicator_raises(self):
        with pytest.raises(NotImplementedError):
            score_indicator("99.9", {})
