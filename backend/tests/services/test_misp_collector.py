"""Tests for the MISPCollector service.

Uses unittest.mock to mock PyMISP methods and pytest-asyncio for async tests.
"""

import time
from unittest.mock import patch

import pytest

from src.models.enums import DataSource, IOCType, ThreatLevel
from src.models.sources.misp import MISPAttribute
from src.services.misp_collector import MISPCollector

SAMPLE_EVENT = {
    "Event": {
        "id": "1234",
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "info": "APT28 Campaign Targeting Government",
        "threat_level_id": "1",
        "analysis": "2",
        "date": "2025-06-15",
        "timestamp": "1718467200",
        "publish_timestamp": "1718467200",
        "org_id": "1",
        "orgc_id": "2",
        "distribution": "1",
        "published": True,
        "attribute_count": "3",
        "Orgc": {"id": "2", "name": "CERT-EU"},
        "Tag": [
            {"name": "tlp:green"},
            {"name": "apt28"},
        ],
        "Attribute": [
            {
                "id": "1",
                "event_id": "1234",
                "type": "ip-dst",
                "category": "Network activity",
                "value": "192.168.1.1",
                "to_ids": True,
            },
            {
                "id": "2",
                "event_id": "1234",
                "type": "domain",
                "category": "Network activity",
                "value": "evil.example.com",
                "to_ids": True,
            },
            {
                "id": "3",
                "event_id": "1234",
                "type": "sha256",
                "category": "Payload delivery",
                "value": "a" * 64,
                "to_ids": True,
            },
        ],
    }
}


@pytest.fixture
def collector(monkeypatch):
    """MISPCollector with test credentials, PyMISP constructor mocked."""
    monkeypatch.setenv("MISP_URL", "https://misp.test.local")
    monkeypatch.setenv("MISP_API_KEY", "test-misp-key-123")
    with patch("src.services.misp_collector.PyMISP"):
        return MISPCollector()


# ------------------------------------------------------------------
# Init
# ------------------------------------------------------------------


class TestInit:
    def test_raises_without_url(self, monkeypatch):
        monkeypatch.delenv("MISP_URL", raising=False)
        monkeypatch.setenv("MISP_API_KEY", "key")
        with pytest.raises(ValueError, match="MISP_URL"):
            MISPCollector()

    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.setenv("MISP_URL", "https://misp.test.local")
        monkeypatch.delenv("MISP_API_KEY", raising=False)
        with pytest.raises(ValueError, match="MISP_API_KEY"):
            MISPCollector()

    def test_creates_with_credentials(self, collector):
        assert collector._misp_url == "https://misp.test.local"
        assert collector._misp_key == "test-misp-key-123"


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
# get_event
# ------------------------------------------------------------------


class TestGetEvent:
    @pytest.mark.asyncio
    async def test_returns_event_model(self, collector):
        collector._client.search.return_value = [SAMPLE_EVENT]

        event = await collector.get_event("1234")

        assert event.id == "1234"
        assert event.info == "APT28 Campaign Targeting Government"
        assert event.org_name == "CERT-EU"
        assert event.threat_level_id == 1
        assert event.analysis == 2
        assert event.tags == ["tlp:green", "apt28"]
        assert len(event.attributes) == 3

    @pytest.mark.asyncio
    async def test_raises_on_not_found(self, collector):
        collector._client.search.return_value = []

        with pytest.raises(ValueError, match="not found"):
            await collector.get_event("nonexistent")


# ------------------------------------------------------------------
# search_by_attribute
# ------------------------------------------------------------------


SAMPLE_ATTRIBUTE_RESPONSE = {
    "Attribute": [
        {
            "id": "1",
            "event_id": "1234",
            "type": "ip-dst",
            "category": "Network activity",
            "value": "192.168.1.1",
            "to_ids": True,
            "Event": {
                "id": "1234",
                "info": "APT28 Campaign",
                "threat_level_id": "1",
                "org_id": "1",
                "orgc_id": "2",
                "distribution": "1",
            },
        }
    ]
}


class TestSearchByAttribute:
    @pytest.mark.asyncio
    async def test_returns_normalized_indicators(self, collector):
        collector._client.search.return_value = SAMPLE_ATTRIBUTE_RESPONSE

        results = await collector.search_by_attribute("192.168.1.1")

        assert len(results) == 1
        assert results[0].value == "192.168.1.1"
        assert results[0].type == IOCType.IPV4
        assert results[0].source == DataSource.MISP
        assert results[0].confidence == 70
        assert results[0].threat_level == ThreatLevel.HIGH

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self, collector):
        collector._client.search.return_value = {"Attribute": []}

        results = await collector.search_by_attribute("9.9.9.9")
        assert results == []

    @pytest.mark.asyncio
    async def test_filters_by_ioc_type(self, collector):
        collector._client.search.return_value = SAMPLE_ATTRIBUTE_RESPONSE

        await collector.search_by_attribute("192.168.1.1", ioc_type=IOCType.IPV4)

        call_kwargs = collector._client.search.call_args
        assert "type_attribute" in call_kwargs.kwargs


# ------------------------------------------------------------------
# search_by_tag
# ------------------------------------------------------------------


class TestSearchByTag:
    @pytest.mark.asyncio
    async def test_returns_events(self, collector):
        collector._client.search.return_value = [SAMPLE_EVENT]

        events = await collector.search_by_tag(["apt28"])

        assert len(events) == 1
        assert events[0].id == "1234"

    @pytest.mark.asyncio
    async def test_passes_distribution_filter(self, collector):
        collector._client.search.return_value = [SAMPLE_EVENT]

        await collector.search_by_tag(["apt28"], distribution=1)

        call_kwargs = collector._client.search.call_args.kwargs
        assert call_kwargs["distribution"] == 1

    @pytest.mark.asyncio
    async def test_passes_threat_level_filter(self, collector):
        collector._client.search.return_value = [SAMPLE_EVENT]

        await collector.search_by_tag(["apt28"], threat_level=1)

        call_kwargs = collector._client.search.call_args.kwargs
        assert call_kwargs["threat_level_id"] == 1

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self, collector):
        collector._client.search.return_value = []

        events = await collector.search_by_tag(["nonexistent"])
        assert events == []


# ------------------------------------------------------------------
# search_by_date_range
# ------------------------------------------------------------------


class TestSearchByDateRange:
    @pytest.mark.asyncio
    async def test_returns_events_in_range(self, collector):
        collector._client.search.return_value = [SAMPLE_EVENT]

        events = await collector.search_by_date_range("2025-06-01", "2025-06-30")

        assert len(events) == 1
        assert events[0].id == "1234"

    @pytest.mark.asyncio
    async def test_passes_filters(self, collector):
        collector._client.search.return_value = [SAMPLE_EVENT]

        await collector.search_by_date_range(
            "2025-06-01", "2025-06-30", distribution=2, threat_level=1
        )

        call_kwargs = collector._client.search.call_args.kwargs
        assert call_kwargs["distribution"] == 2
        assert call_kwargs["threat_level_id"] == 1

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self, collector):
        collector._client.search.return_value = []

        events = await collector.search_by_date_range("2020-01-01", "2020-01-31")
        assert events == []


# ------------------------------------------------------------------
# Type mapping
# ------------------------------------------------------------------


class TestTypeMapping:
    def test_all_misp_types_map_to_valid_ioc_type(self):
        for misp_type, ioc_type in MISPCollector.MISP_TYPE_MAP.items():
            assert isinstance(misp_type, str)
            assert isinstance(ioc_type, IOCType)

    def test_threat_levels_map_to_valid_enum(self):
        for misp_level, threat_level in MISPCollector.THREAT_LEVEL_MAP.items():
            assert isinstance(misp_level, int)
            assert isinstance(threat_level, ThreatLevel)


# ------------------------------------------------------------------
# _extract_ioc_value
# ------------------------------------------------------------------


class TestExtractIocValue:
    def test_simple_value_passthrough(self, collector):
        assert collector._extract_ioc_value("ip-dst", "1.2.3.4") == "1.2.3.4"

    def test_ip_port_extracts_ip(self, collector):
        assert collector._extract_ioc_value("ip-dst|port", "1.2.3.4|443") == "1.2.3.4"

    def test_filename_hash_extracts_hash(self, collector):
        hash_val = "a" * 64
        result = collector._extract_ioc_value("filename|sha256", f"mal.exe|{hash_val}")
        assert result == hash_val

    def test_filename_md5_extracts_hash(self, collector):
        hash_val = "b" * 32
        result = collector._extract_ioc_value("filename|md5", f"trojan.exe|{hash_val}")
        assert result == hash_val


# ------------------------------------------------------------------
# _normalize_attribute
# ------------------------------------------------------------------


class TestNormalizeAttribute:
    def test_valid_ipv4_normalized(self, collector):
        attr = MISPAttribute(type="ip-dst", value="1.2.3.4")
        result = collector._normalize_attribute(attr, threat_level_id=1)

        assert result is not None
        assert result.value == "1.2.3.4"
        assert result.type == IOCType.IPV4
        assert result.source == DataSource.MISP
        assert result.threat_level == ThreatLevel.HIGH

    def test_ipv6_auto_detected(self, collector):
        attr = MISPAttribute(type="ip-dst", value="2001:db8::1")
        result = collector._normalize_attribute(attr)

        assert result is not None
        assert result.type == IOCType.IPV6

    def test_invalid_value_returns_none(self, collector):
        attr = MISPAttribute(type="ip-dst", value="not-an-ip")
        result = collector._normalize_attribute(attr)
        assert result is None

    def test_unknown_type_returns_none(self, collector):
        attr = MISPAttribute(type="ssdeep", value="abc")
        result = collector._normalize_attribute(attr)
        assert result is None

    def test_composite_type_extracts_hash(self, collector):
        attr = MISPAttribute(type="filename|sha256", value=f"mal.exe|{'a' * 64}")
        result = collector._normalize_attribute(attr)

        assert result is not None
        assert result.value == "a" * 64
        assert result.type == IOCType.SHA256

    def test_default_threat_level_is_unknown(self, collector):
        attr = MISPAttribute(type="domain", value="evil.example.com")
        result = collector._normalize_attribute(attr)

        assert result is not None
        assert result.threat_level == ThreatLevel.UNKNOWN


# ------------------------------------------------------------------
# extract_indicators
# ------------------------------------------------------------------


class TestExtractIndicators:
    def test_extracts_all_mappable_attributes(self, collector):
        event = collector._parse_event(SAMPLE_EVENT)
        indicators = collector.extract_indicators(event)

        assert len(indicators) == 3
        types = {ind.type for ind in indicators}
        assert IOCType.IPV4 in types
        assert IOCType.DOMAIN in types
        assert IOCType.SHA256 in types

    def test_skips_unmappable_attributes(self, collector):
        event_data = {
            "Event": {
                "id": "5",
                "info": "Test",
                "Attribute": [
                    {"type": "ssdeep", "value": "abc"},
                    {"type": "ip-dst", "value": "10.0.0.1"},
                ],
            }
        }
        event = collector._parse_event(event_data)
        indicators = collector.extract_indicators(event)

        assert len(indicators) == 1
        assert indicators[0].value == "10.0.0.1"

    def test_empty_event_returns_empty_list(self, collector):
        event_data = {
            "Event": {
                "id": "6",
                "info": "Empty event",
                "Attribute": [],
            }
        }
        event = collector._parse_event(event_data)
        indicators = collector.extract_indicators(event)
        assert indicators == []


# ------------------------------------------------------------------
# _search error handling
# ------------------------------------------------------------------


class TestSearchErrorHandling:
    @pytest.mark.asyncio
    async def test_raises_on_misp_error_response(self, collector):
        collector._client.search.return_value = {"errors": ["Authentication failed"]}

        with pytest.raises(ValueError, match="MISP API error"):
            await collector._search(controller="events")

    @pytest.mark.asyncio
    async def test_returns_empty_on_dict_without_errors(self, collector):
        collector._client.search.return_value = {"response": []}

        result = await collector._search(controller="events")
        assert result == []
