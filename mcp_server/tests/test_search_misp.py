"""Tests for the search_misp MCP tool.

Uses unittest.mock to mock PyMISP and pytest-asyncio for async tests.
"""

import json
from unittest.mock import patch

import pytest

from src.server import mcp, search_misp

SAMPLE_EVENT = {
    "Event": {
        "id": "1234",
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "info": "APT28 Campaign Targeting Government",
        "threat_level_id": "1",
        "analysis": "2",
        "date": "2025-06-15",
        "org_id": "1",
        "orgc_id": "2",
        "distribution": "1",
        "Orgc": {"id": "2", "name": "CERT-EU"},
        "Tag": [
            {"name": "tlp:green"},
            {"name": "apt28"},
        ],
        "Attribute": [
            {
                "id": "1",
                "type": "ip-dst",
                "category": "Network activity",
                "value": "203.0.113.50",
                "to_ids": True,
                "comment": "C2 server",
            },
            {
                "id": "2",
                "type": "domain",
                "category": "Network activity",
                "value": "evil.example.com",
                "to_ids": True,
                "comment": "",
            },
            {
                "id": "3",
                "type": "sha256",
                "category": "Payload delivery",
                "value": "a" * 64,
                "to_ids": True,
                "comment": "Malware hash",
            },
        ],
    }
}

SAMPLE_ATTRIBUTE_RESPONSE = {
    "Attribute": [
        {
            "id": "1",
            "type": "ip-dst",
            "category": "Network activity",
            "value": "203.0.113.50",
            "to_ids": True,
            "comment": "C2 server",
            "Event": {
                "id": "1234",
                "info": "APT28 Campaign",
                "threat_level_id": "1",
                "analysis": "2",
                "date": "2025-06-15",
                "Orgc": {"name": "CERT-EU"},
            },
        }
    ]
}


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set MISP env vars for all tests."""
    monkeypatch.setenv("MISP_URL", "https://misp.test.local")
    monkeypatch.setenv("MISP_API_KEY", "test-key")


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------


class TestSearchMispRegistered:
    def test_tool_registered(self):
        tools = mcp._tool_manager._tools
        assert "search_misp" in tools


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


class TestSearchMispValidation:
    @pytest.mark.asyncio
    async def test_empty_search_term_raises(self):
        with pytest.raises(ValueError, match="search_term cannot be empty"):
            await search_misp.fn("", search_type="attribute")

    @pytest.mark.asyncio
    async def test_invalid_search_type_raises(self):
        with pytest.raises(ValueError, match="search_type must be"):
            await search_misp.fn("test", search_type="invalid")

    @pytest.mark.asyncio
    async def test_missing_env_vars_raises(self, monkeypatch):
        monkeypatch.delenv("MISP_URL", raising=False)
        monkeypatch.delenv("MISP_API_KEY", raising=False)
        with pytest.raises(ValueError, match="MISP is not configured"):
            await search_misp.fn("test", search_type="attribute")


# ------------------------------------------------------------------
# Attribute search
# ------------------------------------------------------------------


class TestSearchMispAttributeSearch:
    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_returns_normalized_indicators(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = SAMPLE_ATTRIBUTE_RESPONSE

        raw = await search_misp.fn("203.0.113.50", search_type="attribute")
        data = json.loads(raw)

        assert data["source"] == "misp"
        assert data["search_term"] == "203.0.113.50"
        assert data["search_type"] == "attribute"
        assert data["total_results"] == 1

        event = data["events"][0]
        assert event["event_id"] == "1234"
        assert event["title"] == "APT28 Campaign"
        assert event["threat_level"] == "high"
        assert event["analysis_status"] == "complete"
        assert len(event["indicators"]) == 1
        assert event["indicators"][0]["type"] == "ipv4"
        assert event["indicators"][0]["value"] == "203.0.113.50"

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_returns_empty_on_no_results(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = {"Attribute": []}

        raw = await search_misp.fn("9.9.9.9", search_type="attribute")
        data = json.loads(raw)

        assert data["total_results"] == 0
        assert data["events"] == []

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_groups_attributes_by_event(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = {
            "Attribute": [
                {
                    "type": "ip-dst",
                    "value": "1.2.3.4",
                    "Event": {"id": "1", "info": "Event A", "threat_level_id": "2"},
                },
                {
                    "type": "domain",
                    "value": "evil.com",
                    "Event": {"id": "1", "info": "Event A", "threat_level_id": "2"},
                },
                {
                    "type": "ip-dst",
                    "value": "5.6.7.8",
                    "Event": {"id": "2", "info": "Event B", "threat_level_id": "3"},
                },
            ]
        }

        raw = await search_misp.fn("1.2.3.4", search_type="attribute")
        data = json.loads(raw)

        assert data["total_results"] == 2
        event_ids = [e["event_id"] for e in data["events"]]
        assert "1" in event_ids
        assert "2" in event_ids

        event_a = next(e for e in data["events"] if e["event_id"] == "1")
        assert len(event_a["indicators"]) == 2


# ------------------------------------------------------------------
# Tag search
# ------------------------------------------------------------------


class TestSearchMispTagSearch:
    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_returns_events(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        raw = await search_misp.fn("apt28", search_type="tag")
        data = json.loads(raw)

        assert data["source"] == "misp"
        assert data["search_type"] == "tag"
        assert data["total_results"] == 1

        event = data["events"][0]
        assert event["event_id"] == "1234"
        assert event["org_name"] == "CERT-EU"
        assert event["tags"] == ["tlp:green", "apt28"]
        assert len(event["indicators"]) == 3

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_returns_empty_on_no_results(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = []

        raw = await search_misp.fn("nonexistent", search_type="tag")
        data = json.loads(raw)

        assert data["total_results"] == 0
        assert data["events"] == []


# ------------------------------------------------------------------
# Event ID search
# ------------------------------------------------------------------


class TestSearchMispEventIdSearch:
    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_returns_single_event(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        raw = await search_misp.fn("1234", search_type="event_id")
        data = json.loads(raw)

        assert data["total_results"] == 1
        assert data["events"][0]["event_id"] == "1234"


# ------------------------------------------------------------------
# Filters
# ------------------------------------------------------------------


class TestSearchMispFilters:
    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_passes_date_range(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        await search_misp.fn(
            "apt28",
            search_type="tag",
            date_from="2025-01-01",
            date_to="2025-12-31",
        )

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["date_from"] == "2025-01-01"
        assert call_kwargs["date_to"] == "2025-12-31"

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_passes_threat_level(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        await search_misp.fn("apt28", search_type="tag", threat_level=1)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["threat_level_id"] == 1

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_passes_distribution(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        await search_misp.fn("apt28", search_type="tag", distribution=1)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["distribution"] == 1


# ------------------------------------------------------------------
# Return format
# ------------------------------------------------------------------


class TestSearchMispReturnFormat:
    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_has_required_top_level_keys(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        raw = await search_misp.fn("apt28", search_type="tag")
        data = json.loads(raw)

        assert "source" in data
        assert "search_term" in data
        assert "search_type" in data
        assert "total_results" in data
        assert "events" in data

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_event_has_required_keys(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        raw = await search_misp.fn("apt28", search_type="tag")
        data = json.loads(raw)

        event = data["events"][0]
        required = [
            "event_id", "title", "org_name", "threat_level",
            "analysis_status", "date", "tags", "indicators",
        ]
        for key in required:
            assert key in event, f"Missing key: {key}"

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_indicator_has_required_keys(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = [SAMPLE_EVENT]

        raw = await search_misp.fn("apt28", search_type="tag")
        data = json.loads(raw)

        indicator = data["events"][0]["indicators"][0]
        required = ["type", "value", "category", "comment", "to_ids"]
        for key in required:
            assert key in indicator, f"Missing key: {key}"


# ------------------------------------------------------------------
# Composite types
# ------------------------------------------------------------------


class TestSearchMispCompositeTypes:
    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_ip_port_extracts_ip(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = {
            "Attribute": [
                {
                    "type": "ip-dst|port",
                    "value": "1.2.3.4|443",
                    "Event": {"id": "1", "info": "Test"},
                }
            ]
        }

        raw = await search_misp.fn("1.2.3.4", search_type="attribute")
        data = json.loads(raw)

        assert data["events"][0]["indicators"][0]["value"] == "1.2.3.4"
        assert data["events"][0]["indicators"][0]["type"] == "ipv4"

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_filename_hash_extracts_hash(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        hash_val = "a" * 64
        mock_client.search.return_value = {
            "Attribute": [
                {
                    "type": "filename|sha256",
                    "value": f"mal.exe|{hash_val}",
                    "Event": {"id": "1", "info": "Test"},
                }
            ]
        }

        raw = await search_misp.fn("mal.exe", search_type="attribute")
        data = json.loads(raw)

        assert data["events"][0]["indicators"][0]["value"] == hash_val
        assert data["events"][0]["indicators"][0]["type"] == "sha256"

    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_ipv6_auto_detected(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = {
            "Attribute": [
                {
                    "type": "ip-dst",
                    "value": "2001:db8::1",
                    "Event": {"id": "1", "info": "Test"},
                }
            ]
        }

        raw = await search_misp.fn("2001:db8::1", search_type="attribute")
        data = json.loads(raw)

        assert data["events"][0]["indicators"][0]["type"] == "ipv6"


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------


class TestSearchMispErrorHandling:
    @pytest.mark.asyncio
    @patch("src.server.PyMISP")
    async def test_raises_on_misp_api_error(self, mock_pymisp_cls):
        mock_client = mock_pymisp_cls.return_value
        mock_client.search.return_value = {"errors": ["Auth failed"]}

        with pytest.raises(ValueError, match="MISP API error"):
            await search_misp.fn("test", search_type="attribute")
