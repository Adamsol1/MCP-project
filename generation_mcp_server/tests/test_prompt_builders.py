"""Tests for generation MCP server prompt builders."""

import json
import re
from datetime import UTC, datetime

from prompts._shared import _language_instruction
from prompts.direction import (
    build_direction_dialogue_prompt,
    build_direction_summary_prompt,
    build_pir_generation_prompt,
    direction_gathering,
    direction_pir,
    direction_summary,
)
from prompts.collection import (
    _code_to_date,
    _is_future_timeframe,
    build_collection_plan_prompt,
    build_collection_collect_prompt,
)
from prompts.processing import (
    build_processing_modify_prompt,
    build_processing_prompt,
    processing_process,
)
from prompts.analysis import build_analysis_generate_prompt
from prompts import register_prompts


# ── Shared ────────────────────────────────────────────────────────────────────

class TestLanguageInstruction:
    def test_english_language_instruction(self):
        # arrange / act
        result = _language_instruction("en", "all output")

        # assert
        assert "English" in result

    def test_norwegian_language_instruction(self):
        # arrange / act
        result = _language_instruction("no", "the summary")

        # assert
        assert "Norwegian" in result

    def test_unknown_language_falls_back_to_english(self):
        # arrange / act
        result = _language_instruction("zz", "all output")

        # assert
        assert "English" in result


# ── Direction ─────────────────────────────────────────────────────────────────

class TestDirectionDialoguePrompt:
    def test_user_message_appears_in_prompt(self):
        # arrange
        user_message = "Investigate APT29 targeting Norwegian telecom"

        # act
        result = build_direction_dialogue_prompt(user_message, [], ["neutral"], {})

        # assert
        assert user_message in result

    def test_missing_fields_appear_in_prompt(self):
        # arrange / act
        result = build_direction_dialogue_prompt("msg", ["scope", "timeframe"], ["neutral"], {})

        # assert
        assert "scope" in result
        assert "timeframe" in result

    def test_language_instruction_prepended(self):
        # arrange / act
        result = build_direction_dialogue_prompt("msg", [], ["neutral"], {}, language="no")

        # assert
        assert "Norwegian" in result


class TestPirGenerationPrompt:
    def test_scope_appears_in_prompt(self):
        # arrange / act
        result = build_pir_generation_prompt(
            scope="cyber threats to telecom",
            timeframe="last 6 months",
            target_entities=["Norway"],
            perspectives=["neutral"],
            threat_actors=["APT29"],
            priority_focus="attack vectors",
        )

        # assert
        assert "cyber threats to telecom" in result

    def test_modifications_section_included_when_provided(self):
        # arrange / act
        result = build_pir_generation_prompt(
            scope="test",
            timeframe="last 6 months",
            target_entities=["Norway"],
            perspectives=["neutral"],
            threat_actors=[],
            priority_focus="test",
            modifications="Focus only on ransomware",
        )

        # assert
        assert "Focus only on ransomware" in result

    def test_modifications_defaults_to_none_label_when_not_provided(self):
        # arrange / act
        result = build_pir_generation_prompt(
            scope="test",
            timeframe="last 6 months",
            target_entities=["Norway"],
            perspectives=["neutral"],
            threat_actors=[],
            priority_focus="test",
        )

        # assert — label is always present, value should be None
        assert "MODIFICATIONS: None" in result

    def test_background_knowledge_included_when_provided(self):
        # arrange / act
        result = build_pir_generation_prompt(
            scope="test",
            timeframe="last 6 months",
            target_entities=["Norway"],
            perspectives=["neutral"],
            threat_actors=[],
            priority_focus="test",
            background_knowledge="### Source: geopolitical/norway_russia\nContent here.",
        )

        # assert
        assert "geopolitical/norway_russia" in result


class TestDirectionSummaryPrompt:
    def test_scope_appears_in_prompt(self):
        # arrange / act
        result = build_direction_summary_prompt(
            scope="critical infrastructure threats",
            timeframe="last 6 months",
            target_entities=["Norway"],
            threat_actors=["APT29"],
            priority_focus="attack vectors",
            perspectives=["neutral"],
        )

        # assert
        assert "critical infrastructure threats" in result

    def test_modifications_included_when_provided(self):
        # arrange / act
        result = build_direction_summary_prompt(
            scope="test",
            timeframe="last 6 months",
            target_entities=[],
            threat_actors=[],
            priority_focus="test",
            perspectives=["neutral"],
            modifications="Add focus on energy sector",
        )

        # assert
        assert "Add focus on energy sector" in result


class TestDirectionAdapterFunctions:
    def test_direction_gathering_passes_perspectives_from_context(self):
        # arrange
        context = json.dumps({"perspectives": ["norway", "eu"], "scope": ""})

        # act
        result = direction_gathering("user msg", "[]", context)

        # assert
        assert "norway" in result
        assert "eu" in result

    def test_direction_pir_treats_empty_modifications_as_none(self):
        # arrange / act
        result_no_mod = direction_pir(
            scope="test",
            timeframe="6 months",
            target_entities="[]",
            threat_actors="[]",
            priority_focus="test",
            perspectives='["neutral"]',
            modifications="",
        )
        result_with_mod = direction_pir(
            scope="test",
            timeframe="6 months",
            target_entities="[]",
            threat_actors="[]",
            priority_focus="test",
            perspectives='["neutral"]',
            modifications="Focus on ransomware",
        )

        # assert
        assert "Focus on ransomware" not in result_no_mod
        assert "Focus on ransomware" in result_with_mod

    def test_direction_summary_parses_json_arrays(self):
        # arrange / act
        result = direction_summary(
            scope="telecom threats",
            timeframe="6 months",
            target_entities='["Norway", "Sweden"]',
            threat_actors='["APT29"]',
            priority_focus="attack vectors",
            perspectives='["neutral"]',
        )

        # assert
        assert "Norway" in result
        assert "Sweden" in result


# ── Collection ────────────────────────────────────────────────────────────────

class TestIsFutureTimeframe:
    def test_next_keyword_returns_true(self):
        assert _is_future_timeframe("next 3 months") is True

    def test_upcoming_keyword_returns_true(self):
        assert _is_future_timeframe("upcoming quarter") is True

    def test_past_timeframe_returns_false(self):
        assert _is_future_timeframe("last 6 months") is False

    def test_empty_string_returns_false(self):
        assert _is_future_timeframe("") is False


class TestCodeToDate:
    def test_returns_date_in_yyyy_mm_dd_format(self):
        # arrange / act
        result = _code_to_date("m6")

        # assert
        assert re.match(r"\d{4}-\d{2}-\d{2}", result)

    def test_day_code_returns_recent_date(self):
        # arrange
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # act
        result = _code_to_date("d7")

        # assert
        assert result < today

    def test_year_code_returns_past_date(self):
        # arrange
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # act
        result = _code_to_date("y1")

        # assert
        assert result < today

    def test_empty_code_returns_fallback(self):
        # arrange
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # act
        result = _code_to_date("")

        # assert — fallback is 3 years ago
        assert result < today

    def test_invalid_unit_returns_fallback(self):
        # arrange
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # act
        result = _code_to_date("z5")

        # assert
        assert result < today


class TestCollectionPlanPrompt:
    def test_pir_appears_in_prompt(self):
        # arrange / act
        result = build_collection_plan_prompt(pir="What is the APT29 threat level?")

        # assert
        assert "What is the APT29 threat level?" in result

    def test_modifications_section_included_when_provided(self):
        # arrange / act
        result = build_collection_plan_prompt(
            pir="Test PIR",
            modifications="Add a step for MISP",
        )

        # assert
        assert "Add a step for MISP" in result

    def test_modifications_section_absent_when_not_provided(self):
        # arrange / act
        result = build_collection_plan_prompt(pir="Test PIR")

        # assert
        assert "Modification Request" not in result


class TestCollectionCollectPrompt:
    def test_approved_tools_derived_from_selected_sources(self):
        # arrange / act
        result = build_collection_collect_prompt(
            pir="Test PIR",
            selected_sources=["AlienVault OTX"],
            plan="Use OTX for IoC lookups.",
        )

        # assert
        assert "query_otx" in result

    def test_session_note_included_when_upload_tools_selected(self):
        # arrange / act
        result = build_collection_collect_prompt(
            pir="Test PIR",
            selected_sources=["Uploaded Documents"],
            plan="Check uploaded files.",
            session_id="session-abc",
        )

        # assert
        assert "session-abc" in result

    def test_unmapped_source_noted_and_skipped(self):
        # arrange / act
        result = build_collection_collect_prompt(
            pir="Test PIR",
            selected_sources=["UnknownSource"],
            plan="Test plan.",
        )

        # assert
        assert "UnknownSource" in result


# ── Processing ────────────────────────────────────────────────────────────────

class TestProcessingPrompt:
    def test_pir_and_collected_data_appear_in_prompt(self):
        # arrange / act
        result = build_processing_prompt(
            pir="PIR-1: Identify APT29 activity",
            collected_data='{"summary": "OTX data found"}',
        )

        # assert
        assert "PIR-1: Identify APT29 activity" in result
        assert '{"summary": "OTX data found"}' in result

    def test_includes_todays_date(self):
        # arrange
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # act
        result = build_processing_prompt(pir="PIR", collected_data="data")

        # assert
        assert today in result

    def test_feedback_section_included_when_provided(self):
        # arrange / act
        result = build_processing_prompt(
            pir="PIR",
            collected_data="data",
            feedback="Confidence scores are too high",
        )

        # assert
        assert "Confidence scores are too high" in result

    def test_feedback_section_absent_when_not_provided(self):
        # arrange / act
        result = build_processing_prompt(pir="PIR", collected_data="data")

        # assert
        assert "Analyst Feedback" not in result

    def test_previous_result_section_included_when_provided(self):
        # arrange / act
        result = build_processing_prompt(
            pir="PIR",
            collected_data="data",
            previous_result='{"findings": []}',
        )

        # assert
        assert "Previous Processing Result" in result

    def test_processing_process_empty_feedback_produces_no_feedback_section(self):
        # arrange / act
        result = processing_process(pir="PIR", collected_data="data", feedback="")

        # assert
        assert "Analyst Feedback" not in result


class TestProcessingModifyPrompt:
    def test_modifications_and_existing_result_appear_in_prompt(self):
        # arrange / act
        result = build_processing_modify_prompt(
            existing_result='{"findings": []}',
            modifications="Remove low-confidence findings",
        )

        # assert
        assert "Remove low-confidence findings" in result
        assert '{"findings": []}' in result


# ── Analysis ──────────────────────────────────────────────────────────────────

class TestAnalysisGeneratePrompt:
    def test_pir_and_findings_appear_in_prompt(self):
        # arrange / act
        result = build_analysis_generate_prompt(
            pir="PIR-1: Assess APT29 capability",
            findings='{"findings": [{"id": "F-001"}]}',
        )

        # assert
        assert "PIR-1: Assess APT29 capability" in result
        assert '"id": "F-001"' in result

    def test_includes_todays_date(self):
        # arrange
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # act
        result = build_analysis_generate_prompt(pir="PIR", findings="{}")

        # assert
        assert today in result

    def test_all_six_default_perspectives_included(self):
        # arrange / act
        result = build_analysis_generate_prompt(pir="PIR", findings="{}")

        # assert
        for perspective in ["us", "norway", "china", "eu", "russia", "neutral"]:
            assert perspective in result

    def test_single_perspective_produces_only_that_perspective(self):
        # arrange / act
        result = build_analysis_generate_prompt(
            pir="PIR",
            findings="{}",
            perspectives="neutral",
        )

        # assert
        assert "neutral" in result
        assert "china" not in result


# ── Register prompts ──────────────────────────────────────────────────────────

class TestRegisterPrompts:
    def test_all_ten_prompts_are_registered(self):
        # arrange
        registered = []

        class FakeMCP:
            def prompt(self, fn):
                registered.append(fn.__name__)

        # act
        register_prompts(FakeMCP())

        # assert
        assert set(registered) == {
            "direction_gathering",
            "direction_summary",
            "direction_pir",
            "collection_plan",
            "collection_collect",
            "collection_summarize",
            "collection_modify",
            "processing_process",
            "processing_modify",
            "analysis_generate",
        }
