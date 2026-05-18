"""Tests for the query_otx MCP tool."""

import json

import httpx
import pytest
import respx

from src.server import mcp
from src.tools.otx_tools import query_otx

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
        # arrange / act / assert
        assert "query_otx" in mcp._tool_manager._tools


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


class TestValidation:
    def test_raises_on_empty_search_term(self):
        with pytest.raises(ValueError, match="search_term"):
            query_otx("", "")

    def test_raises_on_whitespace_search_term(self):
        with pytest.raises(ValueError, match="search_term"):
            query_otx("   ", "")


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

        raw = query_otx("1.2.3.4", "ipv4")
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

        raw = query_otx("evil.com", "domain")
        data = json.loads(raw)

        assert data["total_results"] == 1
        assert data["results"][0]["pulse_name"] == "Phishing Domain"

    @respx.mock
    def test_returns_empty_on_404(self):
        respx.get(f"{OTX_BASE}/indicators/IPv4/9.9.9.9/general").mock(
            return_value=httpx.Response(404)
        )

        raw = query_otx("9.9.9.9", "ipv4")
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

        raw = query_otx("8.8.8.8", "ipv4")
        data = json.loads(raw)

        assert data["total_results"] == 0

    def test_unsupported_indicator_type_returns_empty(self):
        raw = query_otx("something", "unsupported_type")
        data = json.loads(raw)

        assert data["total_results"] == 0

    @respx.mock
    def test_returns_empty_on_timeout(self):
        respx.get(f"{OTX_BASE}/indicators/IPv4/1.2.3.4/general").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )

        raw = query_otx("1.2.3.4", "ipv4")
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
        # arrange — mock pulse search and detail fetch (top 3 are enriched)
        respx.get(f"{OTX_BASE}/search/pulses").mock(
            return_value=httpx.Response(200, json={"results": [SAMPLE_PULSE]})
        )
        respx.get(f"{OTX_BASE}/pulses/abc-123").mock(
            return_value=httpx.Response(200, json={**SAMPLE_PULSE, "indicators": [], "description": "", "references": []})
        )

        # act
        raw = query_otx("APT29")
        data = json.loads(raw)

        # assert
        assert data["total_results"] == 1
        assert data["indicator_type"] == "keyword"
        r = data["enriched_pulses"][0]
        assert r["pulse_name"] == "APT29 Campaign"
        assert r["adversary"] == "APT29"
        assert "apt29" in r["tags"]
        assert r["malware_families"] == ["Cobalt Strike"]
        assert r["targeted_countries"] == ["US", "NO"]

    @respx.mock
    def test_returns_empty_on_no_results(self):
        # arrange
        respx.get(f"{OTX_BASE}/search/pulses").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        # act
        raw = query_otx("nonexistent-malware-xyz")
        data = json.loads(raw)

        # assert
        assert data["total_results"] == 0
        assert data["enriched_pulses"] == []

    @respx.mock
    def test_fetches_single_page_of_results(self):
        # arrange — new implementation fetches a single page (max 10)
        page = [{**SAMPLE_PULSE, "id": f"p-{i}", "name": f"Pulse {i}"} for i in range(5)]
        route = respx.get(f"{OTX_BASE}/search/pulses").mock(
            return_value=httpx.Response(200, json={"results": page})
        )
        for i in range(3):  # top 3 are enriched with detail fetches
            respx.get(f"{OTX_BASE}/pulses/p-{i}").mock(
                return_value=httpx.Response(200, json={**SAMPLE_PULSE, "indicators": [], "description": "", "references": []})
            )

        # act
        raw = query_otx("APT29")
        data = json.loads(raw)

        # assert
        assert data["total_results"] == 5
        assert route.call_count == 1  # single page fetch

    @respx.mock
    def test_returns_empty_on_api_error(self):
        # arrange
        respx.get(f"{OTX_BASE}/search/pulses").mock(return_value=httpx.Response(403))

        # act
        raw = query_otx("APT29")
        data = json.loads(raw)

        # assert
        assert data["total_results"] == 0


# ------------------------------------------------------------------
# Missing API key
# ------------------------------------------------------------------


class TestMissingApiKey:
    def test_returns_empty_without_api_key(self, monkeypatch):
        # arrange
        monkeypatch.delenv("OTX_API_KEY", raising=False)

        # act
        raw = query_otx("APT29")
        data = json.loads(raw)

        # assert
        assert data["total_results"] == 0
        assert data["enriched_pulses"] == []
