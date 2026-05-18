"""Tests for google_search and google_news_search tools."""

import httpx
import pytest
import respx

from src.tools.google_search import (
    _build_serper_payload,
    _handle_serper_error,
    google_search,
    google_news_search,
)

_SEARCH_URL = "https://google.serper.dev/search"
_NEWS_URL = "https://google.serper.dev/news"


class TestBuildSerperPayload:
    def test_query_includes_site_exclusions(self):
        # arrange / act
        payload = _build_serper_payload("APT29 Norway", 5, None, None, None)

        # assert
        assert "APT29 Norway" in payload["q"]
        assert "-site:reddit.com" in payload["q"]

    def test_num_results_clamped_to_max_ten(self):
        # arrange / act
        payload = _build_serper_payload("query", 99, None, None, None)

        # assert
        assert payload["num"] == 10

    def test_num_results_clamped_to_min_one(self):
        # arrange / act
        payload = _build_serper_payload("query", 0, None, None, None)

        # assert
        assert payload["num"] == 1

    def test_language_always_english(self):
        # arrange / act
        payload = _build_serper_payload("query", 5, None, None, None)

        # assert
        assert payload["lr"] == "lang_en"

    def test_date_restrict_included_when_provided(self):
        # arrange / act
        payload = _build_serper_payload("query", 5, "m3", None, None)

        # assert
        assert payload["tbs"] == "qdr:m3"

    def test_region_and_language_included_when_provided(self):
        # arrange / act
        payload = _build_serper_payload("query", 5, None, "no", "no")

        # assert
        assert payload["gl"] == "no"
        assert payload["hl"] == "no"

    def test_optional_fields_absent_when_not_provided(self):
        # arrange / act
        payload = _build_serper_payload("query", 5, None, None, None)

        # assert
        assert "tbs" not in payload
        assert "gl" not in payload
        assert "hl" not in payload


class TestHandleSerperError:
    def test_403_returns_quota_message(self):
        # arrange
        response = httpx.Response(403)
        exc = httpx.HTTPStatusError("", request=httpx.Request("POST", "http://x"), response=response)

        # act
        result = _handle_serper_error(exc)

        # assert
        assert "403" in result or "quota" in result.lower() or "invalid" in result.lower()

    def test_429_returns_rate_limit_message(self):
        # arrange
        response = httpx.Response(429)
        exc = httpx.HTTPStatusError("", request=httpx.Request("POST", "http://x"), response=response)

        # act
        result = _handle_serper_error(exc)

        # assert
        assert "429" in result or "rate limit" in result.lower()

    def test_timeout_returns_timeout_message(self):
        # arrange
        exc = httpx.TimeoutException("timed out")

        # act
        result = _handle_serper_error(exc)

        # assert
        assert "timed out" in result.lower() or "timeout" in result.lower()

    def test_generic_exception_returns_error_string(self):
        # arrange
        exc = RuntimeError("something broke")

        # act
        result = _handle_serper_error(exc)

        # assert
        assert result is not None


class TestGoogleSearch:
    def test_returns_error_when_api_key_not_set(self, monkeypatch):
        # arrange
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        # act
        result = google_search("APT29")

        # assert
        assert "Error" in result or "not configured" in result.lower()

    @respx.mock
    def test_returns_formatted_results_on_success(self, monkeypatch):
        # arrange
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        respx.post(_SEARCH_URL).mock(return_value=httpx.Response(200, json={
            "organic": [
                {"title": "APT29 Analysis", "link": "https://example.com", "snippet": "Key findings"}
            ]
        }))

        # act
        result = google_search("APT29")

        # assert
        assert "APT29 Analysis" in result
        assert "https://example.com" in result

    @respx.mock
    def test_returns_no_results_message_when_empty(self, monkeypatch):
        # arrange
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        respx.post(_SEARCH_URL).mock(return_value=httpx.Response(200, json={"organic": []}))

        # act
        result = google_search("obscure-query-xyz")

        # assert
        assert "No results" in result

    @respx.mock
    def test_returns_error_on_403(self, monkeypatch):
        # arrange
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        respx.post(_SEARCH_URL).mock(return_value=httpx.Response(403))

        # act
        result = google_search("APT29")

        # assert
        assert "Error" in result or "403" in result


class TestGoogleNewsSearch:
    def test_returns_error_when_api_key_not_set(self, monkeypatch):
        # arrange
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        # act
        result = google_news_search("APT29")

        # assert
        assert "Error" in result or "not configured" in result.lower()

    @respx.mock
    def test_returns_formatted_news_results(self, monkeypatch):
        # arrange
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        respx.post(_NEWS_URL).mock(return_value=httpx.Response(200, json={
            "news": [
                {
                    "title": "Cyber Attack Reported",
                    "link": "https://news.example.com",
                    "source": "Reuters",
                    "date": "2026-01-01",
                    "snippet": "Details here",
                }
            ]
        }))

        # act
        result = google_news_search("cyber attack")

        # assert
        assert "Cyber Attack Reported" in result
        assert "Reuters" in result

    @respx.mock
    def test_returns_no_results_message_when_empty(self, monkeypatch):
        # arrange
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        respx.post(_NEWS_URL).mock(return_value=httpx.Response(200, json={"news": []}))

        # act
        result = google_news_search("obscure-query-xyz")

        # assert
        assert "No results" in result
