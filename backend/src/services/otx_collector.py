"""OTXCollector — queries AlienVault OTX for threat intelligence.

This service handles all communication with the OTX REST API v1,
including indicator lookups, pulse retrieval, and keyword searches.
It normalizes OTX responses into internal models (OTXPulse,
NormalizedIndicator) and handles rate limiting, pagination, and
error recovery.

API Reference: https://otx.alienvault.com/api
"""

import asyncio
import logging
import os
import time
import uuid

import httpx

from src.models.enums import DataSource, IOCType, ThreatLevel
from src.models.indicators import NormalizedIndicator
from src.models.sources.otx import OTXIndicator, OTXPulse

logger = logging.getLogger("app")


class OTXCollector:
    """Async client for the AlienVault OTX REST API.

    Queries OTX for pulses, indicators, and IOCs, returning
    normalized internal models. Implements rate limiting (10 req/min)
    and exponential backoff on 429/5xx errors.
    """

    BASE_URL = "https://otx.alienvault.com/api/v1"
    MAX_REQUESTS_PER_MINUTE = 10
    DEFAULT_PAGE_LIMIT = 50

    # OTX type string -> internal IOCType
    OTX_TYPE_MAP: dict[str, IOCType] = {
        "IPv4": IOCType.IPV4,
        "IPv6": IOCType.IPV6,
        "domain": IOCType.DOMAIN,
        "URL": IOCType.URL,
        "FileHash-MD5": IOCType.MD5,
        "FileHash-SHA1": IOCType.SHA1,
        "FileHash-SHA256": IOCType.SHA256,
        "email": IOCType.EMAIL,
        "CVE": IOCType.CVE,
    }

    # IOCType -> OTX API path segment for indicator lookups
    IOC_TO_OTX_SECTION: dict[IOCType, str] = {
        IOCType.IPV4: "IPv4",
        IOCType.IPV6: "IPv6",
        IOCType.DOMAIN: "domain",
        IOCType.URL: "url",
        IOCType.MD5: "file",
        IOCType.SHA1: "file",
        IOCType.SHA256: "file",
        IOCType.EMAIL: "email",
        IOCType.CVE: "cve",
    }

    def __init__(self) -> None:
        self._api_key = os.getenv("OTX_API_KEY")
        if not self._api_key:
            raise ValueError("OTX_API_KEY environment variable is not set")
        self._request_timestamps: list[float] = []

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_indicator(
        self, ioc_type: IOCType, value: str
    ) -> list[NormalizedIndicator]:
        """Look up an indicator on OTX and return normalized results.

        Args:
            ioc_type: The type of IOC (IPv4, domain, hash, etc.).
            value: The indicator value to look up.

        Returns:
            List of NormalizedIndicator objects. Empty list if nothing found.
        """
        section = self.IOC_TO_OTX_SECTION.get(ioc_type)
        if section is None:
            logger.warning(f"[OTXCollector] Unsupported IOC type: {ioc_type}")
            return []

        path = f"indicators/{section}/{value}/general"
        try:
            data = await self._request("GET", path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

        pulse_info = data.get("pulse_info", {})
        pulses_data = pulse_info.get("pulses", [])

        results: list[NormalizedIndicator] = []
        for pulse_data in pulses_data:
            for ind_data in pulse_data.get("indicators", []):
                otx_ind = self._parse_indicator(ind_data)
                normalized = self._normalize_indicator(otx_ind)
                if normalized:
                    results.append(normalized)

        return results

    async def get_pulse(self, pulse_id: str) -> OTXPulse:
        """Fetch a single OTX pulse by its ID.

        Args:
            pulse_id: The OTX pulse identifier.

        Returns:
            Parsed OTXPulse model.

        Raises:
            httpx.HTTPStatusError: If the pulse is not found or other error.
        """
        data = await self._request("GET", f"pulses/{pulse_id}")
        return self._parse_pulse(data)

    async def search_pulses(self, query: str) -> list[OTXPulse]:
        """Search OTX pulses by keyword (adversary name, malware family, etc.).

        Args:
            query: Search string.

        Returns:
            List of matching OTXPulse objects. Empty list if nothing found.
        """
        results_data = await self._paginate("search/pulses", params={"q": query})
        return [self._parse_pulse(d) for d in results_data]

    # ------------------------------------------------------------------
    # HTTP infrastructure
    # ------------------------------------------------------------------

    async def _request(
        self, method: str, path: str, params: dict | None = None
    ) -> dict:
        """Make a rate-limited request to the OTX API.

        Args:
            method: HTTP method.
            path: API path (appended to BASE_URL).
            params: Query parameters.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP errors.
        """
        wait = self._enforce_rate_limit()
        if wait > 0:
            logger.debug(f"[OTXCollector] Rate limit: waiting {wait:.1f}s")
            await asyncio.sleep(wait)

        self._request_timestamps.append(time.monotonic())
        url = f"{self.BASE_URL}/{path.lstrip('/')}"
        headers = {"X-OTX-API-KEY": self._api_key}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await self._backoff_request(
                client, method, url, headers=headers, params=params
            )

        return response.json()

    async def _paginate(
        self, path: str, params: dict | None = None, max_pages: int = 10
    ) -> list[dict]:
        """Fetch all pages from a paginated OTX endpoint.

        Args:
            path: API path (appended to BASE_URL).
            params: Query parameters. 'page' and 'limit' are managed internally.
            max_pages: Maximum number of pages to fetch.

        Returns:
            Combined list of results from all pages.
        """
        params = dict(params or {})
        params.setdefault("limit", self.DEFAULT_PAGE_LIMIT)
        all_results: list[dict] = []

        for page in range(1, max_pages + 1):
            params["page"] = page
            data = await self._request("GET", path, params=params)

            results = data.get("results", [])
            all_results.extend(results)

            if len(results) < params["limit"]:
                break

        return all_results

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

    async def _backoff_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        """Make an HTTP request with exponential backoff on 429/5xx.

        Args:
            client: The httpx async client to use.
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            **kwargs: Additional arguments passed to client.request.

        Returns:
            The successful httpx.Response.

        Raises:
            httpx.HTTPStatusError: After max retries are exhausted.
        """
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries + 1):
            response = await client.request(method, url, **kwargs)

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == max_retries:
                    response.raise_for_status()
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"[OTXCollector] {response.status_code} on attempt "
                    f"{attempt + 1}, retrying in {delay}s"
                )
                await asyncio.sleep(delay)
                continue

            response.raise_for_status()
            return response

        # Unreachable, but satisfies type checker
        response.raise_for_status()
        return response  # pragma: no cover

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_pulse(self, data: dict) -> OTXPulse:
        """Parse raw OTX JSON into an OTXPulse model.

        Args:
            data: Raw pulse dict from OTX API.

        Returns:
            Populated OTXPulse instance.
        """
        indicators = [self._parse_indicator(ind) for ind in data.get("indicators", [])]

        # attack_ids can be a list of dicts with an "id" key
        raw_attack_ids = data.get("attack_ids", [])
        attack_ids = []
        if raw_attack_ids:
            for entry in raw_attack_ids:
                if isinstance(entry, dict):
                    attack_ids.append(entry.get("id", ""))
                else:
                    attack_ids.append(str(entry))

        return OTXPulse(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            author_name=data.get("author_name"),
            created=data.get("created"),
            modified=data.get("modified"),
            tlp=data.get("tlp") or data.get("TLP"),
            adversary=data.get("adversary"),
            targeted_countries=data.get("targeted_countries", []),
            malware_families=data.get("malware_families", []),
            attack_ids=attack_ids,
            industries=data.get("industries", []),
            tags=data.get("tags", []),
            references=data.get("references", []),
            indicators=indicators,
            revision=data.get("revision", 1),
            public=data.get("public", True),
        )

    def _parse_indicator(self, data: dict) -> OTXIndicator:
        """Parse raw OTX indicator JSON into an OTXIndicator model.

        Args:
            data: Raw indicator dict from OTX API.

        Returns:
            Populated OTXIndicator instance.
        """
        return OTXIndicator(
            indicator=data["indicator"],
            type=data["type"],
            created=data.get("created"),
            is_active=data.get("is_active", True),
            role=data.get("role"),
            title=data.get("title"),
            description=data.get("description"),
            expiration=data.get("expiration"),
            content=data.get("content"),
        )

    def _normalize_indicator(self, otx_ind: OTXIndicator) -> NormalizedIndicator | None:
        """Convert an OTXIndicator to a NormalizedIndicator.

        Args:
            otx_ind: The OTX indicator to normalize.

        Returns:
            NormalizedIndicator, or None if the type is unmappable or
            the value fails validation.
        """
        ioc_type = self.OTX_TYPE_MAP.get(otx_ind.type)
        if ioc_type is None:
            logger.debug(f"[OTXCollector] Skipping unknown OTX type: {otx_ind.type}")
            return None

        try:
            return NormalizedIndicator(
                id=str(uuid.uuid4()),
                type=ioc_type,
                value=otx_ind.indicator,
                confidence=70,
                threat_level=ThreatLevel.UNKNOWN,
                source=DataSource.OTX,
            )
        except ValueError:
            logger.warning(
                f"[OTXCollector] Validation failed for {otx_ind.indicator} "
                f"(type={otx_ind.type})"
            )
            return None
