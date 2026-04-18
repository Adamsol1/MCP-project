"""Tests for the generic agent builder."""

import pytest

from src.models.dialogue import Perspective
from src.services.agent_builder import _DISPLAY_NAMES, get_display_name


class TestGetDisplayName:
    """Display name lookup for all supported perspectives."""

    def test_all_perspectives_have_display_name(self):
        for perspective in Perspective:
            name = get_display_name(perspective)
            assert isinstance(name, str) and name

    @pytest.mark.parametrize(
        ("perspective", "expected"),
        [
            (Perspective.US, "US Strategic Analyst"),
            (Perspective.NORWAY, "Norway Security Analyst"),
            (Perspective.CHINA, "China Strategic Analyst"),
            (Perspective.EU, "EU Policy Analyst"),
            (Perspective.RUSSIA, "Russia Strategic Analyst"),
            (Perspective.NEUTRAL, "Neutral Evidence Analyst"),
        ],
    )
    def test_correct_display_name_per_perspective(self, perspective, expected):
        assert get_display_name(perspective) == expected

    def test_display_names_covers_all_perspectives(self):
        assert set(_DISPLAY_NAMES.keys()) == set(Perspective)
