import json

import pytest

from src.services.collection_service import CollectionService


@pytest.mark.asyncio
async def test_suggest_sources_does_not_crash_on_plain_text_plan():
    service = CollectionService(mcp_client=None)  # type: ignore[arg-type]

    sources = await service.suggest_sources(
        "Plan:\n1) Use local docs first.\n2) Expand if needed."
    )

    assert sources == ["Internal Knowledge Bank"]


@pytest.mark.asyncio
async def test_suggest_sources_parses_markdown_wrapped_json():
    service = CollectionService(mcp_client=None)  # type: ignore[arg-type]
    raw = """```json
{
  "plan": "Collect indicators from local KB and OTX",
  "suggested_sources": ["Internal Knowledge Bank", "OTX"]
}
```"""

    sources = await service.suggest_sources(raw)

    assert sources == ["Internal Knowledge Bank", "AlienVault OTX"]


def test_coerce_plan_payload_keeps_plan_even_when_not_json():
    raw = "Collect from local KB and correlate findings."

    payload = CollectionService._coerce_plan_payload(raw)

    assert payload["plan"] == raw
    assert payload["suggested_sources"] == []


def test_parse_collected_data_handles_markdown_fenced_json():
    inner = {
        "collected_data": [
            {
                "source": "read_knowledge_base",
                "resource_id": "geopolitical/eu_usa",
                "content": "EU–US relations...",
            },
        ]
    }
    raw = f"```json\n{json.dumps(inner)}\n```"

    result = CollectionService.parse_collected_data(raw)

    assert "source_summary" in result
    assert len(result["collected_data"]) == 1
    assert result["collected_data"][0]["resource_id"] == "geopolitical/eu_usa"


def test_parse_collected_data_happy_path():
    raw = json.dumps(
        {
            "collected_data": [
                {
                    "source": "read_knowledge_base",
                    "resource_id": "geopolitical/eu_usa",
                    "content": "EU–US relations...",
                },
                {
                    "source": "read_knowledge_base",
                    "resource_id": "geopolitical/usa_russia",
                    "content": "US–Russia relations...",
                },
                {
                    "source": "query_otx",
                    "resource_id": None,
                    "content": '{"total_results": 2, "enriched_pulses": [{"name": "APT29"}]}',
                },
            ]
        }
    )

    result = CollectionService.parse_collected_data(raw)

    assert "collected_data" in result
    assert "source_summary" in result
    assert len(result["collected_data"]) == 3

    by_name = {s["display_name"]: s for s in result["source_summary"]}
    assert by_name["Internal Knowledge Bank"]["count"] == 2
    assert by_name["Internal Knowledge Bank"]["has_content"] is True
    assert by_name["AlienVault OTX"]["count"] == 1
    assert by_name["AlienVault OTX"]["has_content"] is True


def test_parse_collected_data_empty_results_marked_as_no_content():
    raw = json.dumps(
        {
            "collected_data": [
                {
                    "source": "query_otx",
                    "resource_id": None,
                    "content": '{"total_results": 0, "enriched_pulses": []}',
                },
                {"source": "search_local_data", "resource_id": None, "content": ""},
            ]
        }
    )

    result = CollectionService.parse_collected_data(raw)

    by_name = {s["display_name"]: s for s in result["source_summary"]}
    # query_otx content is a non-empty JSON string so has_content is True (string is not empty)
    assert by_name["AlienVault OTX"]["has_content"] is True
    # search_local_data content is empty string so has_content is False
    assert by_name["Uploaded Documents"]["has_content"] is False


def test_parse_collected_data_deduplicates_resource_ids():
    raw = json.dumps(
        {
            "collected_data": [
                {
                    "source": "read_knowledge_base",
                    "resource_id": "geopolitical/eu_usa",
                    "content": "first read",
                },
                {
                    "source": "read_knowledge_base",
                    "resource_id": "geopolitical/eu_usa",
                    "content": "second read",
                },
            ]
        }
    )

    result = CollectionService.parse_collected_data(raw)

    kb = next(
        s
        for s in result["source_summary"]
        if s["display_name"] == "Internal Knowledge Bank"
    )
    assert kb["count"] == 2
    assert kb["resource_ids"] == ["geopolitical/eu_usa"]


def test_parse_collected_data_returns_error_payload_on_bad_json():
    raw = "not valid json at all {{{"

    result = CollectionService.parse_collected_data(raw)

    assert "parse_error" in result
    assert result["collected_data"] == []
    assert result["source_summary"] == []


@pytest.mark.asyncio
async def test_suggest_sources_falls_back_on_internal_parser_error(monkeypatch):
    service = CollectionService(mcp_client=None)  # type: ignore[arg-type]

    def boom(_raw):
        raise RuntimeError("unexpected parse failure")

    monkeypatch.setattr(CollectionService, "_coerce_plan_payload", boom)

    sources = await service.suggest_sources("anything")

    assert sources == ["Internal Knowledge Bank"]
