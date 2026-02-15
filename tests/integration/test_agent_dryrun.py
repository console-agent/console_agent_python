"""Integration tests — dry run mode (no API calls)."""

import pytest

from console_agent import agent, init
from console_agent.core import update_config


class TestDryRun:
    def setup_method(self):
        """Enable dry run mode before each test."""
        update_config(dry_run=True, log_level="silent")

    def teardown_method(self):
        """Reset config after each test."""
        update_config(dry_run=False, log_level="info")

    def test_dry_run_returns_result(self):
        result = agent("analyze this code")
        assert result.success is True
        assert "DRY RUN" in result.summary

    def test_dry_run_no_api_call(self):
        result = agent("debug this error")
        assert result.metadata.tokens_used == 0
        assert result.metadata.latency_ms == 0

    def test_dry_run_with_context(self):
        result = agent("analyze", context={"key": "value"})
        assert result.success is True
        assert result.data.get("dry_run") is True

    def test_dry_run_persona_security(self):
        result = agent.security("audit this")
        assert result.success is True
        assert "DRY RUN" in result.summary

    def test_dry_run_persona_debug(self):
        result = agent.debug("find the bug")
        assert result.success is True
        assert "DRY RUN" in result.summary

    def test_dry_run_persona_architect(self):
        result = agent.architect("review design")
        assert result.success is True
        assert "DRY RUN" in result.summary

    def test_dry_run_confidence_is_1(self):
        result = agent("test")
        assert result.confidence == 1.0

    def test_dry_run_with_google_search_tool(self):
        result = agent("search for latest news", tools=["google_search"])
        assert result.success is True
        assert "DRY RUN" in result.summary

    def test_dry_run_with_url_context_tool(self):
        result = agent("analyze https://example.com", tools=["url_context"])
        assert result.success is True
        assert "DRY RUN" in result.summary

    def test_dry_run_with_multiple_tools(self):
        result = agent(
            "search and analyze",
            tools=["google_search", "url_context", "code_execution"],
        )
        assert result.success is True
        assert "DRY RUN" in result.summary

    def test_dry_run_tools_with_persona(self):
        result = agent.security(
            "audit this endpoint",
            tools=["google_search"],
        )
        assert result.success is True
        assert "DRY RUN" in result.summary
