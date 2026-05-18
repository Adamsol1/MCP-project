import json

from prompts.analysis import build_analysis_review_prompt
from prompts.collection import build_collection_review_prompt
from prompts.direction import build_direction_review_prompt
from prompts.processing import build_processing_review_prompt
from prompts import register_prompts


class TestDirectionReviewPrompt:
    def test_content_appears_in_prompt(self):
        # arrange
        content = "PIR: Identify APT29 activity in Norwegian telecom sector"
        context = '{"scope": "telecom threats"}'

        # act
        result = build_direction_review_prompt(content, context)

        # assert
        assert content in result

    def test_context_appears_in_prompt(self):
        # arrange
        content = "PIR: Identify APT29 activity"
        context = '{"scope": "telecom threats", "timeframe": "last 6 months"}'

        # act
        result = build_direction_review_prompt(content, context)

        # assert
        assert context in result

    def test_prompt_includes_todays_date(self):
        # arrange
        from datetime import UTC, datetime
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # act
        result = build_direction_review_prompt("content", "{}")

        # assert
        assert today in result


class TestCollectionReviewPrompt:
    def test_normal_mode_does_not_include_supplemental_header(self):
        # arrange
        context = json.dumps({"scope": "telecom threats", "pirs": []})

        # act
        result = build_collection_review_prompt("collected data", context)

        # assert
        assert "SUPPLEMENTAL COLLECTION MODE" not in result

    def test_supplemental_mode_activated_by_gather_more_feedback(self):
        # arrange
        context = json.dumps({
            "scope": "telecom threats",
            "gather_more_feedback": "Need more data on APT29 tools",
        })

        # act
        result = build_collection_review_prompt("collected data", context)

        # assert
        assert "SUPPLEMENTAL COLLECTION MODE" in result
        assert "Need more data on APT29 tools" in result

    def test_invalid_context_json_falls_back_to_normal_mode(self):
        # arrange / act
        result = build_collection_review_prompt("collected data", "not valid json")

        # assert
        assert "SUPPLEMENTAL COLLECTION MODE" not in result


class TestProcessingReviewPrompt:
    def test_normal_mode_does_not_include_revision_header(self):
        # arrange
        context = json.dumps({"pir": "Identify APT29", "is_revision": False})

        # act
        result = build_processing_review_prompt("processing result", context)

        # assert
        assert "RE-PROCESSING MODE" not in result

    def test_revision_mode_activated_when_is_revision_is_true(self):
        # arrange
        context = json.dumps({"pir": "Identify APT29", "is_revision": True})

        # act
        result = build_processing_review_prompt("processing result", context)

        # assert
        assert "RE-PROCESSING MODE" in result

    def test_invalid_context_json_falls_back_to_normal_mode(self):
        # arrange / act
        result = build_processing_review_prompt("processing result", "not valid json")

        # assert
        assert "RE-PROCESSING MODE" not in result


class TestAnalysisReviewPrompt:
    def test_content_appears_in_prompt(self):
        # arrange
        content = "Analysis draft: Volt Typhoon pre-positioning campaign"
        context = '{"pir": "Identify state-sponsored threats"}'

        # act
        result = build_analysis_review_prompt(content, context)

        # assert
        assert content in result

    def test_context_appears_in_prompt(self):
        # arrange
        content = "Analysis draft"
        context = '{"pir": "Identify state-sponsored threats", "processing_result": {}}'

        # act
        result = build_analysis_review_prompt(content, context)

        # assert
        assert context in result


class TestRegisterPrompts:
    def test_all_four_phases_are_registered(self):
        # arrange
        registered = []

        class FakeMCP:
            def prompt(self, fn):
                registered.append(fn.__name__)

        # act
        register_prompts(FakeMCP())

        # assert
        assert set(registered) == {
            "direction_review",
            "collection_review",
            "processing_review",
            "analysis_review",
        }
