"""
End-to-end tests — makes real API calls to a local Ollama server.

Requires Ollama running locally with a model pulled (e.g., ollama pull llama3.2).
Run with: pytest tests/e2e/test_ollama_real.py -v
"""

import json
import os
import subprocess

import pytest

from console_agent import agent, init
from console_agent.types import AgentResult

# ─── Skip if Ollama is not running ───────────────────────────────────────────


def _ollama_is_running() -> bool:
    """Check if Ollama server is reachable."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_is_running(),
    reason="Ollama server not running at localhost:11434 — skipping e2e tests",
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def assert_valid_result(result: AgentResult) -> None:
    """Validate that a result has the correct AgentResult structure."""
    assert result is not None

    # Core fields
    assert isinstance(result.success, bool)
    assert isinstance(result.summary, str)
    assert len(result.summary) > 0
    assert isinstance(result.data, dict)
    assert isinstance(result.actions, list)
    assert isinstance(result.confidence, (int, float))
    assert 0 <= result.confidence <= 1

    # Metadata
    assert result.metadata is not None
    assert isinstance(result.metadata.model, str)
    assert isinstance(result.metadata.latency_ms, int)
    assert result.metadata.latency_ms > 0


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestOllamaRealAgent:
    """E2E: Real Ollama API calls against a local server."""

    def setup_method(self):
        init(
            provider="ollama",
            model="llama3.2",
            ollama_host="http://localhost:11434",
            mode="blocking",
            log_level="info",
            anonymize=False,
            timeout=60000,
            verbose=True,
        )

    def test_basic_prompt_returns_valid_result(self):
        """basic prompt — returns valid structured result from Ollama"""
        result = agent("What is 2 + 2? Answer concisely in one sentence.")

        assert_valid_result(result)
        assert result.success is True
        assert result.metadata.model == "llama3.2"
        full_text = json.dumps(result.model_dump(), default=str).lower()
        assert "4" in full_text
        print("Basic result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_security_persona_detects_risk(self):
        """security persona — detects SQL injection risk via Ollama"""
        result = agent(
            "Check this input for SQL injection vulnerabilities",
            context="admin' OR '1'='1; DROP TABLE users; --",
            persona="security",
        )

        assert_valid_result(result)
        full_text = json.dumps(result.model_dump(), default=str).lower()
        assert any(
            kw in full_text for kw in ["sql", "injection", "risk", "dangerous", "attack"]
        ), f"Expected security-related content, got: {full_text[:300]}"
        print("Security result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_debug_persona_analyzes_error(self):
        """debug persona — analyzes an error via Ollama"""
        result = agent(
            "Debug this error and suggest a fix",
            context={
                "error": "TypeError: Cannot read properties of undefined (reading 'map')",
                "code": "const items = data.users.map(u => u.name)",
            },
            persona="debugger",
        )

        assert_valid_result(result)
        print("Debug result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_architect_persona_reviews_design(self):
        """architect persona — reviews API design via Ollama"""
        result = agent(
            "Review this REST API endpoint design",
            context={
                "endpoint": "POST /api/users/search",
                "handler": "Accepts JSON body with filters, returns paginated user list",
            },
            persona="architect",
        )

        assert_valid_result(result)
        print("Architect result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_tools_are_silently_ignored(self):
        """tools param — silently ignored (not supported for Ollama)"""
        result = agent(
            "What is the capital of France?",
            tools=["google_search"],
        )

        assert_valid_result(result)
        assert result.success is True
        print("Tools-ignored result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_persona_shortcut_security(self):
        """persona shortcut — agent.security() via Ollama"""
        result = agent.security(
            "Is this safe?",
            context='query = f"SELECT * FROM users WHERE id = {user_input}"',
        )

        assert_valid_result(result)
        print("Security shortcut:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_persona_shortcut_debug(self):
        """persona shortcut — agent.debug() via Ollama"""
        try:
            1 / 0
        except ZeroDivisionError as e:
            result = agent.debug("Why did this fail?", context=str(e))

        assert_valid_result(result)
        print("Debug shortcut:", json.dumps(result.model_dump(), indent=2, default=str))


class TestOllamaAsyncAgent:
    """E2E: Async Ollama calls."""

    def setup_method(self):
        init(
            provider="ollama",
            model="llama3.2",
            ollama_host="http://localhost:11434",
            mode="blocking",
            log_level="info",
            anonymize=False,
            timeout=60000,
            verbose=True,
        )

    @pytest.mark.asyncio
    async def test_async_basic_prompt(self):
        """async agent.arun() — returns valid result from Ollama"""
        result = await agent.arun("What is 3 + 3? Answer concisely.")

        assert_valid_result(result)
        assert result.success is True
        print("Async result:", json.dumps(result.model_dump(), indent=2, default=str))

    @pytest.mark.asyncio
    async def test_async_with_persona(self):
        """async with persona override via Ollama"""
        result = await agent.arun(
            "Is this code safe?",
            context="os.system(user_input)",
            persona="security",
        )

        assert_valid_result(result)
        print("Async persona:", json.dumps(result.model_dump(), indent=2, default=str))
