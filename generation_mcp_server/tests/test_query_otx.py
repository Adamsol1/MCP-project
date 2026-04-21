"""Tests for the query_otx MCP tool."""

import json

import httpx
import pytest
import respx

from src import server
from src.server import query_otx

OTX_BASE = "https://otx.alienvault.com/api/v1"


@pytest.fixture(autouse=True)
def _set_otx_key(monkeypatch):
    """Ensure OTX_API_KEY is set for all tests."""
    monkeypatch.setenv("OTX_API_KEY", "test-key-123")


# ------------------------------------------------------------------
# Tool registration
# ------------------------------------------------------------------


class TestRegistration:
    def test_query_otx_tool_registered(self):
        tools = server.mcp._tool_manager._tools
        assert "query_otx" in tools


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


class TestValidation:
    def test_raises_on_empty_search_term(self):
        with pytest.raises(ValueError, match="search_term"):
            query_otx.fn("", "")

    def test_raises_on_whitespace_search_term(self):
        with pytest.raises(ValueError, match="search_term"):
            query_otx.fn("   ", "")


# ------------------------------------------------------------------
# Indicator search
# ------------------------------------------------------------------


class TestIndicatorSearch:
    @respx.mock
    def test_returns_results_for_ipv4(self):
        respx.get(f"{OTX_BASE}/indicators/IPv4/1.2.3.4/general").mock(
            return_value=httpx.Response(
                200,
                json={
                    "pulse_info": {
                        "count": 1,
                        "pulses": [
                            {
                                "name": "Malicious IP Pulse",
                                "tags": ["malware", "c2"],
                                "created": "2025-01-01T00:00:00",
                                "modified": "2025-01-15T00:00:00",
                            }
                        ],
                    }
                },
            )
        )

        raw = query_otx.fn("1.2.3.4", "ipv4")
        data = json.loads(raw)

        assert data["total_results"] == 1
        assert data["results"][0]["indicator"] == "1.2.3.4"
        assert data["results"][0]["type"] == "ipv4"
        assert data["results"][0]["pulse_name"] == "Malicious IP Pulse"
        assert "malware" in data["results"][0]["tags"]

    @respx.mock
    def test_returns_results_for_domain(self):
        respx.get(f"{OTX_BASE}/indicators/domain/evil.com/general").mock(
            return_value=httpx.Response(
                200,
                json={
                    "pulse_info": {
                        "count": 1,
                        "pulses": [
                            {
                                "name": "Phishing Domain",
                                "tags": ["phishing"],
                                "created": "2025-03-01T00:00:00",
                                "modified": "2025-03-02T00:00:00",
                            }
                        ],
                    }
                },
            )
        )

        raw = query_otx.fn("evil.com", "domain")
        data = json.loads(raw)

        assert data["total_results"] == 1
        assert data["results"][0]["pulse_name"] == "Phishing Domain"

    @respx.mock
    def test_returns_empty_on_404(self):
        respx.get(f"{OTX_BASE}/indicators/IPv4/9.9.9.9/general").mock(
            return_value=httpx.Response(404)
        )

        raw = query_otx.fn("9.9.9.9", "ipv4")
        data = json.loads(raw)

        assert data["total_results"] == 0
        assert data["results"] == []

    @respx.mock
    def test_returns_empty_on_no_pulses(self):
        respx.get(f"{OTX_BASE}/indicators/IPv4/8.8.8.8/general").mock(
            return_value=httpx.Response(
                200, json={"pulse_info": {"count": 0, "pulses": []}}
            )
        )

        raw = query_otx.fn("8.8.8.8", "ipv4")
        data = json.loads(raw)

        assert data["total_results"] == 0

    def test_unsupported_indicator_type_returns_empty(self):
        raw = query_otx.fn("something", "unsupported_type")
        data = json.loads(raw)

        assert data["total_results"] == 0

    @respx.mock
    def test_returns_empty_on_timeout(self):
        respx.get(f"{OTX_BASE}/indicators/IPv4/1.2.3.4/general").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )

        raw = query_otx.fn("1.2.3.4", "ipv4")
        data = json.loads(raw)

        assert data["total_results"] == 0


# ------------------------------------------------------------------
# Pulse search (keyword)
# ------------------------------------------------------------------


SAMPLE_PULSE = {
    "id": "abc-123",
    "name": "APT29 Campaign",
    "tags": ["apt29", "cozy bear"],
    "adversary": "APT29",
    "malware_families": ["Cobalt Strike"],
    "targeted_countries": ["US", "NO"],
    "created": "2025-01-01T00:00:00",
    "modified": "2025-02-01T00:00:00",
}


class TestPulseSearch:
    @respx.mock
    def test_returns_pulse_results(self):
        respx.get(f"{OTX_BASE}/search/pulses").mock(
            return_value=httpx.Response(200, json={"results": [SAMPLE_PULSE]})
        )

        raw = query_otx.fn("APT29")
        data = json.loads(raw)

        assert data["total_results"] == 1
        assert data["indicator_type"] == "keyword"
        r = data["results"][0]
        assert r["pulse_name"] == "APT29 Campaign"
        assert r["adversary"] == "APT29"
        assert "apt29" in r["tags"]
        assert r["malware_families"] == ["Cobalt Strike"]
        assert r["targeted_countries"] == ["US", "NO"]

    @respx.mock
    def test_returns_empty_on_no_results(self):
        respx.get(f"{OTX_BASE}/search/pulses").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        raw = query_otx.fn("nonexistent-malware-xyz")
        data = json.loads(raw)

        assert data["total_results"] == 0
        assert data["results"] == []

    @respx.mock
    def test_handles_pagination(self):
        page1 = [
            {**SAMPLE_PULSE, "id": f"p-{i}", "name": f"Pulse {i}"} for i in range(50)
        ]
        page2 = [{**SAMPLE_PULSE, "id": "p-50", "name": "Pulse 50"}]

        route = respx.get(f"{OTX_BASE}/search/pulses").mock(
            side_effect=[
                httpx.Response(200, json={"results": page1}),
                httpx.Response(200, json={"results": page2}),
            ]
        )

        raw = query_otx.fn("APT29")
        data = json.loads(raw)

        assert data["total_results"] == 51
        assert route.call_count == 2

    @respx.mock
    def test_returns_empty_on_api_error(self):
        respx.get(f"{OTX_BASE}/search/pulses").mock(return_value=httpx.Response(403))

        raw = query_otx.fn("APT29")
        data = json.loads(raw)

        assert data["total_results"] == 0


# ------------------------------------------------------------------
# Missing API key
# ------------------------------------------------------------------


class TestMissingApiKey:
    def test_returns_empty_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OTX_API_KEY", raising=False)

        raw = query_otx.fn("APT29")
        data = json.loads(raw)

        assert data["total_results"] == 0
        assert data["results"] == []
