import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.collection import collection_service as collection_module
from src.services.collection.collection_service import CollectionService


@pytest.mark.asyncio
async def test_suggest_sources_does_not_crash_on_plain_text_plan():
    service = CollectionService(mcp_client=None)  # type: ignore[arg-type]

    sources = await service.suggest_sources(
        "Plan:\n1) Use local docs first.\n2) Expand if needed."
    )

    assert sources == ["Knowledge Bank"]


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

    assert sources == ["Knowledge Bank", "AlienVault OTX"]


def test_coerce_plan_payload_keeps_plan_even_when_not_json():
    raw = "Collect from local KB and correlate findings."

    payload = CollectionService._coerce_plan_payload(raw)

    assert payload["plan"] == raw
    assert payload["suggested_sources"] == []


def test_coerce_plan_payload_normalizes_step_sources_and_builds_plan_text():
    raw = json.dumps(
        {
            "steps": [
                {
                    "title": "Check local reporting",
                    "description": "Review internal holdings first.",
                    "suggested_sources": ["Internal Knowledge Bank", "OTX"],
                },
                {
                    "title": "Validate externally",
                    "description": "Search current web reporting.",
                    "suggested_sources": ["Knowledge Bank", "Google Search"],
                },
            ],
            "reasoning": "Local-first plan reduces noise.",
        }
    )

    payload = CollectionService._coerce_plan_payload(raw)

    assert payload["suggested_sources"] == [
        "Knowledge Bank",
        "AlienVault OTX",
        "Web Search",
    ]
    assert "1. Check local reporting" in payload["plan"]
    assert payload["steps"][0]["suggested_sources"] == [
        "Knowledge Bank",
        "AlienVault OTX",
    ]
    assert payload["reasoning"] == "Local-first plan reduces noise."


def test_try_parse_json_repairs_trailing_commas():
    raw = '{"plan": "Use OTX", "suggested_sources": ["OTX",],}'

    payload = CollectionService._coerce_plan_payload(raw)

    assert payload["suggested_sources"] == ["AlienVault OTX"]


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
    assert by_name["Knowledge Bank"]["count"] == 2
    assert by_name["Knowledge Bank"]["has_content"] is True
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
        if s["display_name"] == "Knowledge Bank"
    )
    assert kb["count"] == 1
    assert kb["resource_ids"] == ["geopolitical/eu_usa"]


def test_parse_collected_data_merges_attempts_and_keeps_richer_web_duplicate():
    first = json.dumps(
        {
            "collected_data": [
                {
                    "source": "fetch_page",
                    "resource_id": "https://example.com/a?utm=1",
                    "title": "Telecom intrusion report",
                    "content": "short",
                }
            ]
        }
    )
    second = json.dumps(
        {
            "collected_data": [
                {
                    "source": "fetch_page",
                    "resource_id": "https://example.com/a",
                    "title": "Telecom intrusion report",
                    "content": "much richer fetched page summary",
                },
                {
                    "source": "query_otx",
                    "resource_id": "pulse-1",
                    "content": '{"result": "OTX pulse summary"}',
                },
            ]
        }
    )
    raw = f"{first}\n--- NEW COLLECTION ATTEMPT ---\n{second}"

    result = CollectionService.parse_collected_data(raw)

    assert len(result["collected_data"]) == 2
    web_item = next(i for i in result["collected_data"] if i["source"] == "fetch_page")
    otx_item = next(i for i in result["collected_data"] if i["source"] == "query_otx")
    assert web_item["content"] == "much richer fetched page summary"
    assert otx_item["content"] == "OTX pulse summary"


def test_parse_collected_data_returns_error_payload_on_bad_json():
    raw = "not valid json at all {{{"

    result = CollectionService.parse_collected_data(raw)

    assert "parse_error" in result
    assert result["collected_data"] == []
    assert result["source_summary"] == []


def test_extract_search_urls_handles_legacy_and_resource_id_formats():
    raw = """
    URL: https://example.com/report.
    {"resource_id": "https://example.com/other"}
    URL: https://example.com/report)
    """

    urls = collection_module._extract_search_urls(raw)

    assert urls == ["https://example.com/report", "https://example.com/other"]


def test_append_to_collected_data_falls_back_when_base_is_not_json():
    result = collection_module._append_to_collected_data(
        "plain text collection",
        [{"source": "fetch_page", "resource_id": "https://example.com"}],
    )

    assert "plain text collection" in result
    assert "--- NEW COLLECTION ATTEMPT ---" in result
    assert "https://example.com" in result


def test_strip_search_snippet_items_keeps_fetched_page_summaries():
    raw = json.dumps(
        {
            "collected_data": [
                {
                    "source": "google_search",
                    "resource_id": "https://example.com/snippet",
                    "content": "snippet",
                },
                {
                    "source": "fetch_page",
                    "resource_id": "https://example.com/full",
                    "content": "full summary",
                },
            ]
        }
    )

    stripped = collection_module._strip_search_snippet_items(raw)
    result = CollectionService.parse_collected_data(stripped)

    assert len(result["collected_data"]) == 1
    assert result["collected_data"][0]["source"] == "fetch_page"


@pytest.mark.asyncio
async def test_suggest_sources_falls_back_on_internal_parser_error(monkeypatch):
    service = CollectionService(mcp_client=None)  # type: ignore[arg-type]

    def boom(cls_or_self, _raw):
        raise RuntimeError("unexpected parse failure")

    monkeypatch.setattr(CollectionService, "_coerce_plan_payload", boom)

    sources = await service.suggest_sources("anything")

    assert sources == ["Knowledge Bank"]


@pytest.mark.asyncio
async def test_generate_collection_plan_adds_thought_reasoning_and_infers_sources():
    mock_client = MagicMock()

    @asynccontextmanager
    async def mock_connect():
        yield mock_client

    mock_client.connect = mock_connect
    mock_client.get_prompt = AsyncMock(return_value="collection prompt")

    with pytest.MonkeyPatch().context() as mp:
        mock_agent = MagicMock()
        mock_agent.last_thought_text = "Use local holdings before expanding."
        mock_agent.run = AsyncMock(
            return_value=json.dumps(
                {
                    "plan": "Use the local knowledge bank for initial coverage.",
                    "suggested_sources": [],
                }
            )
        )
        mp.setattr(collection_module, "GeminiAgent", MagicMock(return_value=mock_agent))

        service = CollectionService(mcp_client=mock_client)
        raw_plan = await service.generate_collection_plan(
            "What access is being developed?",
            language="en",
        )

    payload = json.loads(raw_plan)
    assert payload["suggested_sources"] == ["Knowledge Bank"]
    assert payload["reasoning"] == "Use local holdings before expanding."


@pytest.mark.asyncio
async def test_collect_fetches_web_pages_and_removes_search_snippets():
    mock_client = MagicMock()

    @asynccontextmanager
    async def mock_connect():
        yield mock_client

    mock_client.connect = mock_connect
    mock_client.get_prompt = AsyncMock(return_value="collect prompt")
    collect_agent = MagicMock()
    collect_agent.run = AsyncMock(
        return_value=json.dumps(
            {
                "collected_data": [
                    {
                        "source": "google_search",
                        "resource_id": "https://example.com/report",
                        "content": "search snippet",
                    }
                ]
            }
        )
    )
    url_agent = MagicMock()
    url_agent.fetch_url_summaries = AsyncMock(
        return_value=[
            {
                "source": "fetch_page",
                "resource_id": "https://example.com/report",
                "title": "Report",
                "content": "full page summary",
            }
        ]
    )

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            collection_module,
            "GeminiAgent",
            MagicMock(side_effect=[collect_agent, url_agent]),
        )

        service = CollectionService(mcp_client=mock_client)
        raw = await service.collect(
            selected_sources=["Web Search"],
            pir="What access is being developed?",
            plan=json.dumps(
                {
                    "steps": [
                        {
                            "title": "Search current reporting",
                            "description": "Find recent reporting.",
                            "suggested_sources": ["Web Search"],
                        }
                    ]
                }
            ),
            source_timeframes={"Web Search": "last 30 days"},
            perspectives=["norway"],
        )

    parsed = CollectionService.parse_collected_data(raw)
    assert [item["source"] for item in parsed["collected_data"]] == ["fetch_page"]
    assert parsed["collected_data"][0]["content"] == "full page summary"
    assert collect_agent.run.await_args.kwargs["allowed_tool_names"] == {"google_search"}
    prompt_args = mock_client.get_prompt.await_args.args[1]
    assert "Per-Step Source Guidance" in prompt_args["step_source_guidance"]
    assert json.loads(prompt_args["source_timeframes"]) == {"Web Search": "last 30 days"}


@pytest.mark.asyncio
async def test_summarize_and_modify_summary_use_dedicated_prompts():
    mock_client = MagicMock()

    @asynccontextmanager
    async def mock_connect():
        yield mock_client

    mock_client.connect = mock_connect
    mock_client.get_prompt = AsyncMock(side_effect=["summarize prompt", "modify prompt"])

    summarize_agent = MagicMock()
    summarize_agent.run = AsyncMock(return_value='{"summary": "ok"}')
    modify_agent = MagicMock()
    modify_agent.run = AsyncMock(return_value="modified summary")

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            collection_module,
            "GeminiAgent",
            MagicMock(side_effect=[summarize_agent, modify_agent]),
        )

        service = CollectionService(mcp_client=mock_client)
        summary = await service.summarize("pir", "raw data", language="no")
        modified = await service.modify_summary("summary", "make shorter", language="no")

    assert summary == '{"summary": "ok"}'
    assert modified == "modified summary"
    assert mock_client.get_prompt.await_args_list[0].args[0] == "collection_summarize"
    assert mock_client.get_prompt.await_args_list[1].args[0] == "collection_modify"
