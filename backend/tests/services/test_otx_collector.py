"""Tests for the OTXCollector service.

Uses respx to mock httpx requests and pytest-asyncio for async tests.
"""

import time

import httpx
import pytest
import respx

from src.models.enums import DataSource, IOCType, ThreatLevel
from src.models.sources.otx import OTXIndicator
from src.services.otx_collector import OTXCollector

BASE = "https://otx.alienvault.com/api/v1"


@pytest.fixture
def collector(monkeypatch):
    """OTXCollector with a test API key."""
    monkeypatch.setenv("OTX_API_KEY", "test-key-123")
    return OTXCollector()


# ------------------------------------------------------------------
# Init
# ------------------------------------------------------------------


class TestInit:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OTX_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OTX_API_KEY"):
            OTXCollector()

    def test_creates_with_api_key(self, collector):
        assert collector._api_key == "test-key-123"


# ------------------------------------------------------------------
# Rate limiting
# ------------------------------------------------------------------


class TestRateLimiting:
    def test_no_delay_under_limit(self, collector):
        assert collector._enforce_rate_limit() == 0.0

    def test_delay_at_limit(self, collector):
        now = time.monotonic()
        collector._request_timestamps = [now - i for i in range(10)]
        wait = collector._enforce_rate_limit()
        assert wait > 0

    def test_old_timestamps_pruned(self, collector):
        old = time.monotonic() - 120
        collector._request_timestamps = [old] * 15
        wait = collector._enforce_rate_limit()
        assert wait == 0.0
        assert len(collector._request_timestamps) == 0


# ------------------------------------------------------------------
# Backoff
# ------------------------------------------------------------------


class TestBackoff:
    @pytest.mark.asyncio
    @respx.mock
    async def test_retries_on_429(self, collector):
        route = respx.get(f"{BASE}/test").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(200, json={"ok": True}),
            ]
        )
        result = await collector._request("GET", "test")
        assert result == {"ok": True}
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_retries_on_500(self, collector):
        route = respx.get(f"{BASE}/test").mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(200, json={"ok": True}),
            ]
        )
        result = await collector._request("GET", "test")
        assert result == {"ok": True}
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_raises_after_max_retries(self, collector):
        respx.get(f"{BASE}/test").mock(return_value=httpx.Response(429))
        with pytest.raises(httpx.HTTPStatusError):
            await collector._request("GET", "test")

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_retry_on_400(self, collector):
        respx.get(f"{BASE}/test").mock(return_value=httpx.Response(400))
        with pytest.raises(httpx.HTTPStatusError):
            await collector._request("GET", "test")


# ------------------------------------------------------------------
# get_indicator
# ------------------------------------------------------------------


class TestGetIndicator:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_normalized_indicators(self, collector):
        respx.get(f"{BASE}/indicators/IPv4/1.2.3.4/general").mock(
            return_value=httpx.Response(
                200,
                json={
                    "pulse_info": {
                        "pulses": [
                            {
                                "indicators": [
                                    {
                                        "indicator": "1.2.3.4",
                                        "type": "IPv4",
                                        "is_active": True,
                                    }
                                ]
                            }
                        ]
                    }
                },
            )
        )

        results = await collector.get_indicator(IOCType.IPV4, "1.2.3.4")

        assert len(results) == 1
        assert results[0].value == "1.2.3.4"
        assert results[0].type == IOCType.IPV4
        assert results[0].source == DataSource.OTX
        assert results[0].confidence == 70
        assert results[0].threat_level == ThreatLevel.UNKNOWN

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_404(self, collector):
        respx.get(f"{BASE}/indicators/IPv4/9.9.9.9/general").mock(
            return_value=httpx.Response(404)
        )

        results = await collector.get_indicator(IOCType.IPV4, "9.9.9.9")
        assert results == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_skips_unknown_types(self, collector):
        respx.get(f"{BASE}/indicators/IPv4/1.2.3.4/general").mock(
            return_value=httpx.Response(
                200,
                json={
                    "pulse_info": {
                        "pulses": [
                            {
                                "indicators": [
                                    {"indicator": "abc123", "type": "FileHash-SSDEEP"}
                                ]
                            }
                        ]
                    }
                },
            )
        )

        results = await collector.get_indicator(IOCType.IPV4, "1.2.3.4")
        assert results == []

    @pytest.mark.asyncio
    async def test_unsupported_ioc_type(self, collector):
        """IOCType not in IOC_TO_OTX_SECTION returns empty list without HTTP call."""
        # Remove a mapping temporarily to simulate unsupported type
        original = collector.IOC_TO_OTX_SECTION.copy()
        collector.IOC_TO_OTX_SECTION.clear()
        try:
            results = await collector.get_indicator(IOCType.IPV4, "1.2.3.4")
            assert results == []
        finally:
            collector.IOC_TO_OTX_SECTION.update(original)


# ------------------------------------------------------------------
# get_pulse
# ------------------------------------------------------------------


SAMPLE_PULSE = {
    "id": "abc-123",
    "name": "Test Pulse",
    "description": "A test pulse",
    "author_name": "tester",
    "created": "2025-01-01T00:00:00",
    "modified": "2025-01-02T00:00:00",
    "tlp": "green",
    "adversary": "APT29",
    "targeted_countries": ["US", "NO"],
    "malware_families": ["Cobalt Strike"],
    "attack_ids": [{"id": "T1059"}, {"id": "T1071"}],
    "industries": ["government"],
    "tags": ["apt", "russia"],
    "references": ["https://example.com"],
    "indicators": [
        {"indicator": "evil.example.com", "type": "domain", "is_active": True}
    ],
    "revision": 2,
    "public": True,
}


class TestGetPulse:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_pulse_model(self, collector):
        respx.get(f"{BASE}/pulses/abc-123").mock(
            return_value=httpx.Response(200, json=SAMPLE_PULSE)
        )

        pulse = await collector.get_pulse("abc-123")

        assert pulse.id == "abc-123"
        assert pulse.name == "Test Pulse"
        assert pulse.adversary == "APT29"
        assert pulse.tlp == "green"
        assert pulse.targeted_countries == ["US", "NO"]
        assert pulse.malware_families == ["Cobalt Strike"]
        assert pulse.attack_ids == ["T1059", "T1071"]
        assert pulse.tags == ["apt", "russia"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_parses_indicators(self, collector):
        respx.get(f"{BASE}/pulses/abc-123").mock(
            return_value=httpx.Response(200, json=SAMPLE_PULSE)
        )

        pulse = await collector.get_pulse("abc-123")

        assert len(pulse.indicators) == 1
        assert pulse.indicators[0].indicator == "evil.example.com"
        assert pulse.indicators[0].type == "domain"

    @pytest.mark.asyncio
    @respx.mock
    async def test_raises_on_404(self, collector):
        respx.get(f"{BASE}/pulses/nonexistent").mock(return_value=httpx.Response(404))
        with pytest.raises(httpx.HTTPStatusError):
            await collector.get_pulse("nonexistent")


# ------------------------------------------------------------------
# search_pulses
# ------------------------------------------------------------------


class TestSearchPulses:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_matching_pulses(self, collector):
        respx.get(f"{BASE}/search/pulses").mock(
            return_value=httpx.Response(200, json={"results": [SAMPLE_PULSE]})
        )

        pulses = await collector.search_pulses("APT29")

        assert len(pulses) == 1
        assert pulses[0].name == "Test Pulse"

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_no_results(self, collector):
        respx.get(f"{BASE}/search/pulses").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        pulses = await collector.search_pulses("nonexistent-malware")
        assert pulses == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_pagination(self, collector):
        """Two pages of results — second page has fewer items than limit."""
        page1_results = [
            {**SAMPLE_PULSE, "id": f"pulse-{i}", "name": f"Pulse {i}"}
            for i in range(50)
        ]
        page2_results = [{**SAMPLE_PULSE, "id": "pulse-50", "name": "Pulse 50"}]

        route = respx.get(f"{BASE}/search/pulses").mock(
            side_effect=[
                httpx.Response(200, json={"results": page1_results}),
                httpx.Response(200, json={"results": page2_results}),
            ]
        )

        pulses = await collector.search_pulses("APT29")

        assert len(pulses) == 51
        assert route.call_count == 2


# ------------------------------------------------------------------
# Type mapping
# ------------------------------------------------------------------


class TestTypeMapping:
    def test_all_otx_types_map_to_valid_ioc_type(self):
        for otx_type, ioc_type in OTXCollector.OTX_TYPE_MAP.items():
            assert isinstance(otx_type, str)
            assert isinstance(ioc_type, IOCType)

    def test_reverse_map_covers_all_ioc_types(self):
        for ioc_type in IOCType:
            assert ioc_type in OTXCollector.IOC_TO_OTX_SECTION


# ------------------------------------------------------------------
# _normalize_indicator
# ------------------------------------------------------------------


class TestNormalizeIndicator:
    def test_valid_ipv4_normalized(self, collector):
        otx_ind = OTXIndicator(indicator="1.2.3.4", type="IPv4")
        result = collector._normalize_indicator(otx_ind)

        assert result is not None
        assert result.value == "1.2.3.4"
        assert result.type == IOCType.IPV4
        assert result.source == DataSource.OTX

    def test_invalid_value_returns_none(self, collector):
        otx_ind = OTXIndicator(indicator="not-an-ip", type="IPv4")
        result = collector._normalize_indicator(otx_ind)
        assert result is None

    def test_unknown_type_returns_none(self, collector):
        otx_ind = OTXIndicator(indicator="abc", type="FileHash-SSDEEP")
        result = collector._normalize_indicator(otx_ind)
        assert result is None
