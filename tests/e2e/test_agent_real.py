"""
End-to-end tests — makes real API calls to Gemini.

Ported from the Node.js version (tests/e2e/agent-real.test.ts).
Requires GEMINI_API_KEY in environment.
Run with: pytest tests/e2e/ -v
"""

import json
import os

import pytest
from pydantic import BaseModel, Field
from typing import List

from console_agent import agent, init
from console_agent.types import AgentResult

# Skip all tests if no API key
API_KEY = os.environ.get("GEMINI_API_KEY")

pytestmark = pytest.mark.skipif(
    not API_KEY or API_KEY == "your-gemini-api-key-here",
    reason="GEMINI_API_KEY not set — skipping e2e tests",
)


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
    assert isinstance(result.metadata.tokens_used, int)
    assert result.metadata.tokens_used > 0
    assert isinstance(result.metadata.latency_ms, int)
    assert result.metadata.latency_ms > 0
    assert isinstance(result.metadata.tool_calls, list)
    assert isinstance(result.metadata.cached, bool)


class TestRealAgent:
    """E2E: Real Gemini API calls."""

    def setup_method(self):
        init(
            api_key=API_KEY,
            model="gemini-2.5-flash-lite",
            mode="blocking",
            log_level="info",
            anonymize=False,
            timeout=25000,
        )

    def test_basic_prompt_returns_valid_structured_result(self):
        """basic prompt — returns valid structured result"""
        result = agent("What is 2 + 2? Answer concisely.")

        assert_valid_result(result)
        assert result.success is True
        assert result.metadata.model == "gemini-2.5-flash-lite"
        print("Basic result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_security_persona_detects_sql_injection(self):
        """security persona — detects SQL injection risk"""
        result = agent(
            "Check this input for SQL injection vulnerabilities",
            context="admin' OR '1'='1; DROP TABLE users; --",
            persona="security",
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        # Should mention SQL injection or risk
        full_text = json.dumps(result.model_dump(), default=str).lower()
        assert any(
            kw in full_text for kw in ["sql", "injection", "risk"]
        ), f"Expected SQL/injection/risk in output, got: {full_text[:200]}"
        print("Security result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_debug_persona_analyzes_error(self):
        """debug persona — analyzes an error"""
        result = agent(
            "Debug this error and suggest a fix",
            context={
                "error": "TypeError: Cannot read properties of undefined (reading 'map')",
                "code": "const items = data.users.map(u => u.name)",
                "context": "data.users is undefined when API returns empty response",
            },
            persona="debugger",
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print("Debug result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_architect_persona_reviews_api_design(self):
        """architect persona — reviews API design"""
        result = agent(
            "Review this REST API endpoint design",
            context={
                "endpoint": "POST /api/users/search",
                "handler": "Accepts JSON body with filters, returns paginated user list",
                "concerns": "Should this be GET with query params instead?",
            },
            persona="architect",
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print("Architect result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_auto_detects_persona_from_keywords(self):
        """auto-detects persona from keywords"""
        result = agent(
            "Is this code vulnerable to XSS attacks?",
            context='<div dangerouslySetInnerHTML={{ __html: userInput }} />',
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print("Auto-detect result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_handles_context_as_complex_object(self):
        """handles context as complex object"""
        result = agent(
            "Analyze these performance metrics and suggest optimizations",
            context={
                "avgResponseTime": "3200ms",
                "p99ResponseTime": "8500ms",
                "errorRate": 0.02,
                "requestsPerSecond": 150,
                "databaseQueries": 12,
                "cacheHitRate": 0.35,
            },
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print(
            "Complex context result:",
            json.dumps(result.model_dump(), indent=2, default=str),
        )

    def test_persona_shortcut_security(self):
        """persona shortcut — agent.security()"""
        result = agent.security(
            "Is this safe?",
            context='query = f"SELECT * FROM users WHERE id = {user_input}"',
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print("Security shortcut result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_persona_shortcut_debug(self):
        """persona shortcut — agent.debug()"""
        try:
            1 / 0
        except ZeroDivisionError as e:
            result = agent.debug("Why did this fail?", context=str(e))

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print("Debug shortcut result:", json.dumps(result.model_dump(), indent=2, default=str))

    def test_persona_shortcut_architect(self):
        """persona shortcut — agent.architect()"""
        result = agent.architect(
            "Review this API design",
            context="GET /users/:id, POST /users, DELETE /users/:id",
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print("Architect shortcut result:", json.dumps(result.model_dump(), indent=2, default=str))


class TestCustomStructuredOutput:
    """E2E: Custom Structured Output (schema_model & response_format)."""

    def setup_method(self):
        init(
            api_key=API_KEY,
            model="gemini-2.5-flash-lite",
            mode="blocking",
            log_level="info",
            anonymize=False,
            timeout=25000,
        )

    def test_pydantic_schema_returns_typed_structured_output(self):
        """Pydantic schema — returns typed structured output"""

        class EmailValidation(BaseModel):
            is_valid: bool = Field(description="Whether the email is valid")
            reason: str = Field(description="Why the email is or is not valid")
            suggestions: List[str] = Field(
                default_factory=list,
                description="Suggestions for fixing the email",
            )

        result = agent(
            "Validate this email address and explain why it is or is not valid",
            context="not-a-real-email@",
            schema_model=EmailValidation,
        )

        assert_valid_result(result)
        assert result.success is True
        assert "is_valid" in result.data
        assert isinstance(result.data["is_valid"], bool)
        assert isinstance(result.data["reason"], str)
        assert isinstance(result.data["suggestions"], list)
        print(
            "Pydantic schema result:",
            json.dumps(result.model_dump(), indent=2, default=str),
        )

    def test_response_format_json_schema(self):
        """responseFormat JSON schema — returns structured output"""
        result = agent(
            "Analyze this code for potential security issues. "
            "Return a JSON object with exactly these keys: severity, issue, fix.",
            context="x = eval(user_input)",
            response_format={
                "type": "json_object",
                "schema": {
                    "type": "object",
                    "properties": {
                        "severity": {
                            "type": "string",
                            "description": "One of: low, medium, high, critical",
                        },
                        "issue": {
                            "type": "string",
                            "description": "Description of the issue",
                        },
                        "fix": {
                            "type": "string",
                            "description": "Suggested fix",
                        },
                    },
                    "required": ["severity", "issue", "fix"],
                },
            },
        )

        assert result is not None
        assert result.success is True
        assert isinstance(result.data, dict)
        assert len(result.data) > 0
        # The custom schema response should contain security-related content
        full_text = json.dumps(result.data, default=str).lower()
        assert any(
            kw in full_text for kw in ["eval", "injection", "code execution", "critical", "severity"]
        ), f"Expected security-related content in output, got: {full_text[:200]}"
        print(
            "responseFormat result:",
            json.dumps(result.model_dump(), indent=2, default=str),
        )

    def test_no_custom_schema_returns_default_format(self):
        """no custom schema — returns default AgentResult format"""
        result = agent("What is 1 + 1? Answer concisely.")

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        assert isinstance(result.summary, str)
        assert isinstance(result.confidence, (int, float))
        assert isinstance(result.actions, list)
        print(
            "Default schema result:",
            json.dumps(result.model_dump(), indent=2, default=str),
        )


class TestAsyncAgent:
    """E2E: Async agent calls."""

    def setup_method(self):
        init(
            api_key=API_KEY,
            model="gemini-2.5-flash-lite",
            mode="blocking",
            log_level="info",
            anonymize=False,
            timeout=25000,
        )

    @pytest.mark.asyncio
    async def test_async_basic_prompt(self):
        """async agent.arun() — returns valid result"""
        result = await agent.arun("What is 3 + 3? Answer concisely.")

        assert_valid_result(result)
        assert result.success is True
        print("Async result:", json.dumps(result.model_dump(), indent=2, default=str))

    @pytest.mark.asyncio
    async def test_async_with_persona(self):
        """async with persona override"""
        result = await agent.arun(
            "Is this code safe?",
            context="os.system(user_input)",
            persona="security",
        )

        assert_valid_result(result)
        assert isinstance(result.success, bool)
        print(
            "Async persona result:",
            json.dumps(result.model_dump(), indent=2, default=str),
        )