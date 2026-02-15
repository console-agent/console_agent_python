"""Tests for tool resolution and helpers."""

from console_agent.tools import TOOLS_MIN_TIMEOUT, has_explicit_tools, resolve_tools
from console_agent.types import AgentCallOptions, ToolConfig


class TestResolveTools:
    """Test resolve_tools() converts tool names to Gemini model kwargs."""

    def test_google_search(self):
        result = resolve_tools(["google_search"])
        assert result == {"search": True}

    def test_url_context(self):
        result = resolve_tools(["url_context"])
        assert result == {"url_context": True}

    def test_code_execution(self):
        result = resolve_tools(["code_execution"])
        assert "generative_model_kwargs" in result
        tools = result["generative_model_kwargs"]["tools"]
        assert len(tools) == 1
        assert tools[0].code_execution is not None

    def test_google_search_and_url_context(self):
        result = resolve_tools(["google_search", "url_context"])
        assert result == {"search": True, "url_context": True}

    def test_code_execution_with_search(self):
        """When code_execution is present, all tools go via generative_model_kwargs."""
        result = resolve_tools(["google_search", "code_execution"])
        assert "generative_model_kwargs" in result
        tools = result["generative_model_kwargs"]["tools"]
        assert len(tools) == 2
        # Should NOT have top-level search flag
        assert "search" not in result

    def test_all_three_tools(self):
        result = resolve_tools(["google_search", "url_context", "code_execution"])
        assert "generative_model_kwargs" in result
        tools = result["generative_model_kwargs"]["tools"]
        assert len(tools) == 3
        # Should NOT have top-level flags
        assert "search" not in result
        assert "url_context" not in result

    def test_file_analysis_ignored(self):
        result = resolve_tools(["file_analysis"])
        assert result == {}

    def test_file_analysis_with_search(self):
        result = resolve_tools(["google_search", "file_analysis"])
        assert result == {"search": True}

    def test_empty_tools(self):
        result = resolve_tools([])
        assert result == {}

    def test_tool_config_object(self):
        config = ToolConfig(type="google_search")
        result = resolve_tools([config])
        assert result == {"search": True}

    def test_mixed_string_and_config(self):
        config = ToolConfig(type="url_context")
        result = resolve_tools(["google_search", config])
        assert result == {"search": True, "url_context": True}

    def test_code_execution_alone_has_one_tool(self):
        result = resolve_tools(["code_execution"])
        tools = result["generative_model_kwargs"]["tools"]
        assert len(tools) == 1
        assert tools[0].code_execution is not None
        assert tools[0].google_search is None


class TestHasExplicitTools:
    """Test has_explicit_tools() detection."""

    def test_none_options(self):
        assert has_explicit_tools(None) is False

    def test_no_tools(self):
        options = AgentCallOptions()
        assert has_explicit_tools(options) is False

    def test_empty_tools(self):
        options = AgentCallOptions(tools=[])
        assert has_explicit_tools(options) is False

    def test_with_google_search(self):
        options = AgentCallOptions(tools=["google_search"])
        assert has_explicit_tools(options) is True

    def test_with_url_context(self):
        options = AgentCallOptions(tools=["url_context"])
        assert has_explicit_tools(options) is True

    def test_with_code_execution(self):
        options = AgentCallOptions(tools=["code_execution"])
        assert has_explicit_tools(options) is True

    def test_with_multiple_tools(self):
        options = AgentCallOptions(tools=["google_search", "url_context"])
        assert has_explicit_tools(options) is True

    def test_with_tool_config(self):
        options = AgentCallOptions(tools=[ToolConfig(type="google_search")])
        assert has_explicit_tools(options) is True


class TestToolsMinTimeout:
    """Test TOOLS_MIN_TIMEOUT constant."""

    def test_min_timeout_value(self):
        assert TOOLS_MIN_TIMEOUT == 30_000

    def test_min_timeout_is_int(self):
        assert isinstance(TOOLS_MIN_TIMEOUT, int)
