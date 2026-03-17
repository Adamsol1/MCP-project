"""TDD tests for web_search and fetch_page MCP tools.

Run with:
    cd mcp_server && pytest tests/test_web_search.py -v
"""

import pytest

from src.server import mcp
from src.tools import web_search as web_search_module
from src.tools.web_search import fetch_page, web_search


# ------------------------------------------------------------------
# Tool registration
# ------------------------------------------------------------------


class TestToolRegistration:
    def test_web_search_tool_registered(self):
        assert "web_search" in mcp._tool_manager._tools

    def test_fetch_page_tool_registered(self):
        assert "fetch_page" in mcp._tool_manager._tools


# ------------------------------------------------------------------
# web_search — happy path
# ------------------------------------------------------------------


class TestWebSearch:
    def _make_ddg_result(self):
        return [
            {
                "title": "APT29 Phishing Campaign",
                "href": "https://example.com/apt29",
                "body": "Details about the APT29 phishing campaign targeting EU entities.",
            }
        ]

    def test_returns_string(self, mocker):
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.return_value = self._make_ddg_result()
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        result = web_search("APT29 phishing")

        assert isinstance(result, str)

    def test_result_contains_required_fields(self, mocker):
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.return_value = self._make_ddg_result()
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        result = web_search("APT29 phishing")

        assert "APT29 Phishing Campaign" in result
        assert "https://example.com/apt29" in result
        assert "Details about the APT29" in result
        assert "web_search" in result

    def test_passes_max_results_to_ddg(self, mocker):
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.return_value = []
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        web_search("APT29", max_results=3)

        call_kwargs = mock_ddgs.__enter__.return_value.text.call_args
        assert call_kwargs.kwargs.get("max_results") == 3 or call_kwargs.args[1] == 3

    def test_passes_timelimit_to_ddg(self, mocker):
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.return_value = []
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        web_search("CVE-2024-1234", timelimit="w")

        call_kwargs = mock_ddgs.__enter__.return_value.text.call_args
        assert call_kwargs.kwargs.get("timelimit") == "w"

    def test_passes_region_to_ddg(self, mocker):
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.return_value = []
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        web_search("Sandworm", region="wt-wt")

        call_kwargs = mock_ddgs.__enter__.return_value.text.call_args
        assert call_kwargs.kwargs.get("region") == "wt-wt"

    def test_empty_results_returns_no_results_message(self, mocker):
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.return_value = None
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        result = web_search("APT29")

        assert isinstance(result, str)
        assert "No results found" in result

    def test_multiple_results_all_in_output(self, mocker):
        raw = [
            {"title": f"Result {i}", "href": f"https://example.com/{i}", "body": f"Body {i}"}
            for i in range(3)
        ]
        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.return_value = raw
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        result = web_search("Lazarus")

        assert isinstance(result, str)
        for i in range(3):
            assert f"Result {i}" in result
            assert f"https://example.com/{i}" in result


# ------------------------------------------------------------------
# web_search — error handling
# ------------------------------------------------------------------


class TestWebSearchErrors:
    def test_handles_rate_limit_exception(self, mocker):
        from duckduckgo_search.exceptions import RatelimitException

        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.side_effect = RatelimitException("rate limit")
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        result = web_search("APT29")

        assert isinstance(result, str)
        assert "rate limit" in result.lower() or "Error" in result

    def test_handles_ddg_search_exception(self, mocker):
        from duckduckgo_search.exceptions import DuckDuckGoSearchException

        mock_ddgs = mocker.MagicMock()
        mock_ddgs.__enter__.return_value.text.side_effect = DuckDuckGoSearchException("search error")
        mocker.patch.object(web_search_module, "DDGS", return_value=mock_ddgs)

        result = web_search("APT29")

        assert isinstance(result, str)
        assert "Error" in result or "error" in result


# ------------------------------------------------------------------
# fetch_page — happy path
# ------------------------------------------------------------------


class TestFetchPage:
    _FAKE_HTML = """
    <html>
      <head><title>Threat Report</title></head>
      <body>
        <nav>Navigation links</nav>
        <script>alert('xss')</script>
        <style>.foo { color: red; }</style>
        <main>
          <h1>APT29 Infrastructure Analysis</h1>
          <p>This report details the command-and-control infrastructure used by APT29.</p>
        </main>
        <footer>Copyright 2024</footer>
      </body>
    </html>
    """

    @pytest.mark.asyncio
    async def test_returns_url_and_content(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.text = self._FAKE_HTML
        mock_response.raise_for_status = mocker.MagicMock()

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(return_value=mock_response)
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com/report")

        assert result["url"] == "https://example.com/report"
        assert "content" in result
        assert result["source"] == "web_fetch"
        assert result["provider"] == "duckduckgo"

    @pytest.mark.asyncio
    async def test_strips_script_and_style_tags(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.text = self._FAKE_HTML
        mock_response.raise_for_status = mocker.MagicMock()

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(return_value=mock_response)
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com/report")

        assert "alert" not in result["content"]
        assert "color: red" not in result["content"]

    @pytest.mark.asyncio
    async def test_strips_nav_and_footer(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.text = self._FAKE_HTML
        mock_response.raise_for_status = mocker.MagicMock()

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(return_value=mock_response)
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com/report")

        assert "Navigation links" not in result["content"]
        assert "Copyright 2024" not in result["content"]

    @pytest.mark.asyncio
    async def test_keeps_main_article_text(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.text = self._FAKE_HTML
        mock_response.raise_for_status = mocker.MagicMock()

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(return_value=mock_response)
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com/report")

        assert "APT29 Infrastructure Analysis" in result["content"]
        assert "command-and-control" in result["content"]

    @pytest.mark.asyncio
    async def test_truncates_to_max_chars(self, mocker):
        long_html = "<html><body><p>" + ("A" * 5000) + "</p></body></html>"
        mock_response = mocker.MagicMock()
        mock_response.text = long_html
        mock_response.raise_for_status = mocker.MagicMock()

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(return_value=mock_response)
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com/long", max_chars=100)

        assert len(result["content"]) <= 100
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_truncated_false_when_content_fits(self, mocker):
        short_html = "<html><body><p>Short content.</p></body></html>"
        mock_response = mocker.MagicMock()
        mock_response.text = short_html
        mock_response.raise_for_status = mocker.MagicMock()

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(return_value=mock_response)
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com/short", max_chars=4000)

        assert result["truncated"] is False


# ------------------------------------------------------------------
# fetch_page — error handling
# ------------------------------------------------------------------


class TestFetchPageErrors:
    @pytest.mark.asyncio
    async def test_handles_timeout(self, mocker):
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(
            side_effect=web_search_module.httpx.TimeoutException("timeout")
        )
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com")

        assert result["url"] == "https://example.com"
        assert "error" in result
        assert result["source"] == "web_fetch"

    @pytest.mark.asyncio
    async def test_handles_http_error(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.status_code = 404
        http_error = web_search_module.httpx.HTTPStatusError(
            "Not Found", request=mocker.MagicMock(), response=mock_response
        )

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(side_effect=http_error)
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com")

        assert "error" in result
        assert "404" in result["error"]
        assert result["source"] == "web_fetch"

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self, mocker):
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value.get = mocker.AsyncMock(
            side_effect=Exception("unexpected error")
        )
        mocker.patch.object(web_search_module.httpx, "AsyncClient", return_value=mock_client)

        result = await fetch_page("https://example.com")

        assert "error" in result
        assert result["source"] == "web_fetch"
