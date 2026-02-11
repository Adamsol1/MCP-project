"""Tests for Perspective enum and its integration with DialogueContext."""

import pytest
from pydantic import ValidationError

from src.models.dialogue import DialogueContext, Perspective

# ---------- Perspective enum ----------


class TestPerspectiveEnum:
    """The Perspective enum defines the geopolitical viewpoints available for analysis."""

    def test_has_all_six_perspectives(self):
        """We need exactly these 6 perspectives: US, Norway, China, EU, Russia, Neutral."""
        expected = {"US", "NORWAY", "CHINA", "EU", "RUSSIA", "NEUTRAL"}
        actual = {p.name for p in Perspective}

        assert actual == expected

    def test_values_are_lowercase_strings(self):
        """Enum values should be lowercase strings, matching the project convention
        (see enums.py — IOCType, ThreatLevel, etc. all use lowercase)."""
        for perspective in Perspective:
            assert perspective.value == perspective.value.lower()
            assert isinstance(perspective.value, str)

    def test_perspective_is_string_enum(self):
        """Perspective should inherit from str so it serializes cleanly in JSON/Pydantic."""
        assert isinstance(Perspective.US, str)
        assert Perspective.US == "us"

    def test_each_perspective_value(self):
        """Verify the exact string value for each perspective."""
        assert Perspective.US.value == "us"
        assert Perspective.NORWAY.value == "norway"
        assert Perspective.CHINA.value == "china"
        assert Perspective.EU.value == "eu"
        assert Perspective.RUSSIA.value == "russia"
        assert Perspective.NEUTRAL.value == "neutral"


# ---------- DialogueContext with perspectives ----------


class TestDialogueContextPerspectives:
    """DialogueContext should track which perspectives the user selected."""

    def test_default_perspectives_is_neutral(self):
        """When no perspectives are provided, default to [NEUTRAL].
        This ensures analysis always has at least one viewpoint."""
        context = DialogueContext()

        assert context.perspectives == [Perspective.NEUTRAL]

    def test_accepts_single_perspective(self):
        """User might only care about one country's viewpoint."""
        context = DialogueContext(perspectives=[Perspective.US])

        assert context.perspectives == [Perspective.US]

    def test_accepts_multiple_perspectives(self):
        """Core requirement: user can select multiple perspectives at once."""
        selected = [Perspective.US, Perspective.EU, Perspective.NORWAY]
        context = DialogueContext(perspectives=selected)

        assert context.perspectives == selected
        assert len(context.perspectives) == 3

    def test_accepts_all_perspectives(self):
        """Edge case: user selects every available perspective."""
        all_perspectives = list(Perspective)
        context = DialogueContext(perspectives=all_perspectives)

        assert len(context.perspectives) == 6

    def test_rejects_invalid_perspective_string(self):
        """Pydantic should reject strings that aren't valid Perspective values."""
        with pytest.raises(ValidationError):
            DialogueContext(perspectives=["invalid_country"])

    def test_perspectives_coexist_with_other_fields(self):
        """Perspectives should work alongside existing DialogueContext fields."""
        context = DialogueContext(
            initial_query="Analyze APT29 activity",
            scope="network intrusion",
            perspectives=[Perspective.US, Perspective.RUSSIA],
        )

        assert context.initial_query == "Analyze APT29 activity"
        assert context.scope == "network intrusion"
        assert context.perspectives == [Perspective.US, Perspective.RUSSIA]
