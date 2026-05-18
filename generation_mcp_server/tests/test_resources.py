"""Tests for knowledge registry and load_knowledge function."""

from unittest.mock import patch

import pytest

from src.resources import load_knowledge, KNOWLEDGE_REGISTRY


class TestLoadKnowledge:
    def test_returns_none_for_empty_string(self):
        # arrange / act
        result = load_knowledge("")

        # assert
        assert result is None

    def test_returns_none_for_whitespace_only(self):
        # arrange / act
        result = load_knowledge("   ")

        # assert
        assert result is None

    def test_returns_none_when_no_keywords_match(self):
        # arrange
        with patch("src.resources._load_knowledge_from_db", return_value=None):
            # act
            result = load_knowledge("completely unrelated text with no matching keywords xyz123")

        # assert
        assert result is None

    def test_returns_db_result_when_db_available(self):
        # arrange
        db_content = "## Background Knowledge\n### Source: geopolitical/norway_russia\nContent."
        with patch("src.resources._load_knowledge_from_db", return_value=db_content):
            # act
            result = load_knowledge("norway russia")

        # assert
        assert result == db_content

    def test_falls_back_to_registry_when_db_unavailable(self, tmp_path, monkeypatch):
        # arrange — DB unavailable, create a real file in tmp_path
        monkeypatch.setattr("src.resources.RESOURCES_DIR", tmp_path)

        resource_path = tmp_path / "geopolitical" / "norway_russia.md"
        resource_path.parent.mkdir(parents=True)
        resource_path.write_text("# Norway Russia Background", encoding="utf-8")

        with patch("src.resources._load_knowledge_from_db", return_value=None):
            # act
            result = load_knowledge("norway russia arctic")

        # assert
        assert result is not None
        assert "Background Knowledge" in result
        assert "geopolitical/norway_russia" in result

    def test_knowledge_registry_contains_expected_keys(self):
        # arrange / act / assert
        assert "geopolitical/norway_russia" in KNOWLEDGE_REGISTRY
        assert "sectors/energy" in KNOWLEDGE_REGISTRY
        assert "threat_actors/russian_state" in KNOWLEDGE_REGISTRY

    def test_each_registry_entry_has_required_fields(self):
        # arrange / act / assert
        for resource_id, entry in KNOWLEDGE_REGISTRY.items():
            assert "keywords" in entry, f"{resource_id} missing 'keywords'"
            assert "priority" in entry, f"{resource_id} missing 'priority'"
            assert isinstance(entry["keywords"], list), f"{resource_id} keywords must be a list"
