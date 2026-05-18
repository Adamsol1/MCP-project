"""Tests for MCP generation server initialization and tool registration."""

from src.server import greet, mcp


class TestServerInitialization:
    def test_server_has_correct_name(self):
        # arrange / act / assert
        assert mcp.name == "ThreatIntelligence"

    def test_greet_tool_returns_running_message(self):
        # arrange / act
        result = greet.fn()

        # assert
        assert "running" in result.lower()

    def test_greet_tool_is_registered(self):
        # arrange / act / assert
        assert "greet" in mcp._tool_manager._tools


class TestToolRegistration:
    def test_knowledge_tools_registered(self):
        tools = mcp._tool_manager._tools
        assert "read_knowledge_base" in tools
        assert "list_knowledge_base" in tools

    def test_upload_tools_registered(self):
        tools = mcp._tool_manager._tools
        assert "upload_file" in tools
        assert "list_uploads" in tools
        assert "read_upload" in tools
        assert "delete_upload" in tools

    def test_otx_tool_registered(self):
        # arrange / act / assert
        assert "query_otx" in mcp._tool_manager._tools

    def test_local_search_tool_registered(self):
        # arrange / act / assert
        assert "search_local_data" in mcp._tool_manager._tools
