"""Tests for app perspective to council persona mapping."""

import pytest

from src.models.dialogue import Perspective
from src.services.council_personas import (
    CouncilPersonaConfig,
    get_council_persona,
    list_council_personas,
)


class TestCouncilPersonas:
    """Test council persona mapping coverage and prompt content."""

    def test_full_mapping_coverage(self):
        """Every supported app perspective should have a council persona config."""
        personas = list_council_personas()

        assert set(personas) == {
            "us",
            "norway",
            "china",
            "eu",
            "russia",
            "neutral",
        }
        assert all(isinstance(config, CouncilPersonaConfig) for config in personas.values())

    @pytest.mark.parametrize(
        ("perspective", "display_name", "prompt_fragment"),
        [
            ("us", "US Strategic Analyst", "US strategic perspective"),
            ("norway", "Norway Security Analyst", "Norwegian national-security perspective"),
            ("china", "China Strategic Analyst", "China-focused strategic perspective"),
            ("eu", "EU Policy Analyst", "EU strategic policy perspective"),
            ("russia", "Russia Strategic Analyst", "Russia-focused strategic perspective"),
            ("neutral", "Neutral Evidence Analyst", "evidence quality"),
        ],
    )
    def test_correct_prompt_returned_for_each_supported_perspective(
        self, perspective: str, display_name: str, prompt_fragment: str
    ):
        """Each supported perspective should return the expected persona config."""
        config = get_council_persona(perspective)

        assert config.display_name == display_name
        assert prompt_fragment in config.persona_prompt

    def test_accepts_perspective_enum(self):
        """The helper should accept the canonical Perspective enum directly."""
        config = get_council_persona(Perspective.NEUTRAL)

        assert config.display_name == "Neutral Evidence Analyst"
        assert "alternative explanations" in config.persona_prompt
