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


@pytest.mark.asyncio
async def test_suggest_sources_falls_back_on_internal_parser_error(monkeypatch):
    service = CollectionService(mcp_client=None)  # type: ignore[arg-type]

    def boom(_raw):
        raise RuntimeError("unexpected parse failure")

    monkeypatch.setattr(CollectionService, "_coerce_plan_payload", boom)

    sources = await service.suggest_sources("anything")

    assert sources == ["Internal Knowledge Bank"]
