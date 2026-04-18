"""MISPCollector — queries a MISP instance for threat intelligence.

This service handles all communication with a MISP instance via PyMISP,
including event retrieval, attribute searches, and tag/date-based queries.
It normalizes MISP responses into internal models (MISPEvent,
NormalizedIndicator) and handles rate limiting and error recovery.

PyMISP is synchronous (uses requests internally), so all calls are
wrapped in asyncio.to_thread() to avoid blocking the event loop.

API Reference: https://www.misp-project.org/documentation/
"""

import asyncio
import logging
import os
import time
import uuid

from pymisp import PyMISP

from src.models.enums import DataSource, IOCType, ThreatLevel
from src.models.indicators import NormalizedIndicator
from src.models.sources.misp import MISPAttribute, MISPEvent

logger = logging.getLogger("app")


class MISPCollector:
    """Async client for a MISP instance via PyMISP.

    Queries MISP for events and attributes, returning
    normalized internal models. Implements rate limiting (10 req/min)
    and wraps synchronous PyMISP calls in asyncio.to_thread().
    """

    MAX_REQUESTS_PER_MINUTE = 10

    # MISP attribute type -> internal IOCType
    MISP_TYPE_MAP: dict[str, IOCType] = {
        "ip-dst": IOCType.IPV4,
        "ip-src": IOCType.IPV4,
        "ip-dst|port": IOCType.IPV4,
        "ip-src|port": IOCType.IPV4,
        "domain": IOCType.DOMAIN,
        "hostname": IOCType.DOMAIN,
        "url": IOCType.URL,
        "md5": IOCType.MD5,
        "sha1": IOCType.SHA1,
        "sha256": IOCType.SHA256,
        "filename|md5": IOCType.MD5,
        "filename|sha1": IOCType.SHA1,
        "filename|sha256": IOCType.SHA256,
        "email-src": IOCType.EMAIL,
        "email-dst": IOCType.EMAIL,
        "vulnerability": IOCType.CVE,
    }

    # MISP threat_level_id (1-4) -> ThreatLevel enum
    THREAT_LEVEL_MAP: dict[int, ThreatLevel] = {
        1: ThreatLevel.HIGH,
        2: ThreatLevel.MEDIUM,
        3: ThreatLevel.LOW,
        4: ThreatLevel.UNKNOWN,
    }

    def __init__(self) -> None:
        self._misp_url = os.getenv("MISP_URL")
        self._misp_key = os.getenv("MISP_API_KEY")
        if not self._misp_url:
            raise ValueError("MISP_URL environment variable is not set")
        if not self._misp_key:
            raise ValueError("MISP_API_KEY environment variable is not set")

        # ssl=False allows self-signed certs common in MISP deployments
        verify_ssl = os.getenv("MISP_VERIFY_SSL", "false").lower() == "true"
        self._client = PyMISP(self._misp_url, self._misp_key, ssl=verify_ssl)
        self._request_timestamps: list[float] = []

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_event(self, event_id: str) -> MISPEvent:
        """Fetch a single MISP event by its ID.

        Args:
            event_id: The MISP event ID.

        Returns:
            Parsed MISPEvent model.

        Raises:
            ValueError: If the event is not found or access is denied.
        """
        results = await self._search(controller="events", eventid=event_id)
        if not results:
            raise ValueError(f"MISP event {event_id} not found")
        return self._parse_event(results[0])

    async def search_by_attribute(
        self, value: str, ioc_type: IOCType | None = None
    ) -> list[NormalizedIndicator]:
        """Search MISP for events containing a specific attribute value.

        Args:
            value: The IOC value to search for (IP, domain, hash, etc.).
            ioc_type: Optional filter by IOC type.

        Returns:
            List of NormalizedIndicator objects. Empty if nothing found.
        """
        kwargs: dict[str, object] = {
            "controller": "attributes",
            "value": value,
        }
        if ioc_type is not None:
            # Find matching MISP types for this IOCType
            misp_types = [mt for mt, it in self.MISP_TYPE_MAP.items() if it == ioc_type]
            if misp_types:
                kwargs["type_attribute"] = misp_types

        response = await self._search_raw(**kwargs)

        # Attribute search returns {"Attribute": [{...}, ...]}
        # where each attribute has a nested "Event" with metadata.
        attr_list = response.get("Attribute", []) if isinstance(response, dict) else []
        if not attr_list:
            return []

        indicators: list[NormalizedIndicator] = []
        for attr_data in attr_list:
            event_info = attr_data.get("Event", {})
            threat_level_id = int(event_info.get("threat_level_id", 4))

            attr = self._parse_attribute(attr_data)
            normalized = self._normalize_attribute(attr, threat_level_id)
            if normalized:
                indicators.append(normalized)

        return indicators

    async def search_by_tag(
        self,
        tags: list[str],
        *,
        distribution: int | None = None,
        threat_level: int | None = None,
    ) -> list[MISPEvent]:
        """Search MISP events by tag(s), with optional filters.

        Args:
            tags: List of tag names to search for.
            distribution: Filter by distribution level (0-4).
            threat_level: Filter by MISP threat_level_id (1-4).

        Returns:
            List of matching MISPEvent objects.
        """
        kwargs: dict[str, object] = {
            "controller": "events",
            "tags": tags,
        }
        if distribution is not None:
            kwargs["distribution"] = distribution
        if threat_level is not None:
            kwargs["threat_level_id"] = threat_level

        results = await self._search(**kwargs)
        return [self._parse_event(r) for r in results]

    async def search_by_date_range(
        self,
        date_from: str,
        date_to: str,
        *,
        distribution: int | None = None,
        threat_level: int | None = None,
    ) -> list[MISPEvent]:
        """Search MISP events within a date range.

        Args:
            date_from: Start date (YYYY-MM-DD).
            date_to: End date (YYYY-MM-DD).
            distribution: Filter by distribution level (0-4).
            threat_level: Filter by MISP threat_level_id (1-4).

        Returns:
            List of matching MISPEvent objects.
        """
        kwargs: dict[str, object] = {
            "controller": "events",
            "date_from": date_from,
            "date_to": date_to,
        }
        if distribution is not None:
            kwargs["distribution"] = distribution
        if threat_level is not None:
            kwargs["threat_level_id"] = threat_level

        results = await self._search(**kwargs)
        return [self._parse_event(r) for r in results]

    def extract_indicators(self, event: MISPEvent) -> list[NormalizedIndicator]:
        """Extract all normalizable indicators from a MISPEvent.

        Args:
            event: A parsed MISPEvent with attributes.

        Returns:
            List of NormalizedIndicator objects for all mappable attributes.
        """
        indicators: list[NormalizedIndicator] = []
        for attr in event.attributes:
            normalized = self._normalize_attribute(attr, event.threat_level_id)
            if normalized:
                indicators.append(normalized)
        return indicators

    # ------------------------------------------------------------------
    # PyMISP wrappers (async via to_thread)
    # ------------------------------------------------------------------

    async def _search_raw(self, **kwargs: object) -> dict | list:
        """Execute a rate-limited PyMISP search and return the raw response.

        Args:
            **kwargs: Keyword arguments passed to PyMISP.search().

        Returns:
            Raw response from PyMISP (dict or list depending on controller).

        Raises:
            ConnectionError: If the MISP instance is unreachable.
            ValueError: If the response indicates an error.
        """
        wait = self._enforce_rate_limit()
        if wait > 0:
            logger.debug(f"[MISPCollector] Rate limit: waiting {wait:.1f}s")
            await asyncio.sleep(wait)

        self._request_timestamps.append(time.monotonic())

        response = await asyncio.to_thread(self._client.search, **kwargs)

        if isinstance(response, dict) and "errors" in response:
            raise ValueError(f"MISP API error: {response['errors']}")

        return response

    async def _search(self, **kwargs: object) -> list[dict]:
        """Execute a rate-limited PyMISP search for events.

        Convenience wrapper around _search_raw that expects a list response
        (used by event-based searches).

        Args:
            **kwargs: Keyword arguments passed to PyMISP.search().

        Returns:
            List of raw event dicts from the MISP response.
        """
        response = await self._search_raw(**kwargs)
        if isinstance(response, list):
            return response
        return []

    def _enforce_rate_limit(self) -> float:
        """Calculate delay needed to stay within rate limit.

        Returns:
            Seconds to wait before making the next request (0 if none needed).
        """
        now = time.monotonic()
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60]
        if len(self._request_timestamps) >= self.MAX_REQUESTS_PER_MINUTE:
            oldest = self._request_timestamps[0]
            wait = 60 - (now - oldest)
            return max(wait, 0)
        return 0.0

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_event(self, data: dict) -> MISPEvent:
        """Parse raw MISP JSON into a MISPEvent model.

        PyMISP returns events wrapped in {"Event": {...}}. This method
        unwraps and normalizes the structure.

        Args:
            data: Raw event dict from PyMISP (may be wrapped or unwrapped).

        Returns:
            Populated MISPEvent instance.
        """
        event_data = data.get("Event", data)

        attributes = [
            self._parse_attribute(attr) for attr in event_data.get("Attribute", [])
        ]

        # Extract tags — MISP tags are [{"name": "tag1"}, ...]
        raw_tags = event_data.get("Tag", [])
        tags = [t["name"] for t in raw_tags if isinstance(t, dict) and "name" in t]

        # Extract org name from nested Orgc object
        orgc = event_data.get("Orgc", {})
        org_name = orgc.get("name") if isinstance(orgc, dict) else None

        return MISPEvent(
            id=event_data.get("id"),
            uuid=event_data.get("uuid"),
            info=event_data.get("info", ""),
            threat_level_id=int(event_data.get("threat_level_id", 4)),
            analysis=int(event_data.get("analysis", 0)),
            date=event_data.get("date"),
            timestamp=event_data.get("timestamp"),
            publish_timestamp=event_data.get("publish_timestamp"),
            org_id=event_data.get("org_id"),
            orgc_id=event_data.get("orgc_id"),
            org_name=org_name,
            distribution=int(event_data.get("distribution", 0)),
            published=event_data.get("published", False),
            attribute_count=int(event_data.get("attribute_count", 0)),
            attributes=attributes,
            tags=tags,
            extends_uuid=event_data.get("extends_uuid"),
        )

    def _parse_attribute(self, data: dict) -> MISPAttribute:
        """Parse raw MISP attribute JSON into a MISPAttribute model.

        Args:
            data: Raw attribute dict from MISP.

        Returns:
            Populated MISPAttribute instance.
        """
        return MISPAttribute(
            id=data.get("id"),
            event_id=data.get("event_id"),
            type=data["type"],
            category=data.get("category", "External analysis"),
            value=data["value"],
            to_ids=data.get("to_ids", True),
            comment=data.get("comment"),
            timestamp=data.get("timestamp"),
            distribution=int(data.get("distribution", 0)),
            first_seen=data.get("first_seen"),
            last_seen=data.get("last_seen"),
            deleted=data.get("deleted", False),
            disable_correlation=data.get("disable_correlation", False),
        )

    def _extract_ioc_value(self, misp_type: str, raw_value: str) -> str:
        """Extract the IOC value from a MISP attribute value.

        MISP composite types use '|' separators (e.g., "filename|sha256"
        has value "malware.exe|abc123..."). This extracts the relevant part.

        Args:
            misp_type: The MISP attribute type string.
            raw_value: The raw attribute value from MISP.

        Returns:
            The cleaned IOC value.
        """
        if "|" in misp_type and "|" in raw_value:
            parts = raw_value.split("|", 1)
            # For ip|port types, take the IP (first part)
            if misp_type in ("ip-dst|port", "ip-src|port"):
                return parts[0]
            # For filename|hash types, take the hash (second part)
            return parts[1]
        return raw_value

    def _normalize_attribute(
        self, attr: MISPAttribute, threat_level_id: int = 4
    ) -> NormalizedIndicator | None:
        """Convert a MISPAttribute to a NormalizedIndicator.

        Args:
            attr: The MISP attribute to normalize.
            threat_level_id: The parent event's threat_level_id (1-4).

        Returns:
            NormalizedIndicator, or None if the type is unmappable or
            the value fails validation.
        """
        ioc_type = self.MISP_TYPE_MAP.get(attr.type)
        if ioc_type is None:
            logger.debug(f"[MISPCollector] Skipping unknown MISP type: {attr.type}")
            return None

        value = self._extract_ioc_value(attr.type, attr.value)

        # MISP uses ip-dst/ip-src for both IPv4 and IPv6
        if ioc_type == IOCType.IPV4 and ":" in value:
            ioc_type = IOCType.IPV6

        threat_level = self.THREAT_LEVEL_MAP.get(threat_level_id, ThreatLevel.UNKNOWN)

        try:
            return NormalizedIndicator(
                id=str(uuid.uuid4()),
                type=ioc_type,
                value=value,
                confidence=70,
                threat_level=threat_level,
                source=DataSource.MISP,
            )
        except ValueError:
            logger.warning(
                f"[MISPCollector] Validation failed for {value} (type={attr.type})"
            )
            return None
