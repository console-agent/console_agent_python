"""Unit tests for the Ollama provider integration."""

from __future__ import annotations

import sys
import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from console_agent.types import (
    AgentCallOptions,
    AgentConfig,
    AgentMetadata,
    AgentResult,
    PersonaDefinition,
)
from console_agent.providers.ollama import (
    call_ollama,
    _parse_response,
    _coerce_data,
    _coerce_actions,
    _build_user_message,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def persona():
    return PersonaDefinition(
        name="general",
        system_prompt="You are a helpful assistant.",
        icon="🤖",
        label="General",
        default_tools=[],
        keywords=[],
    )


@pytest.fixture
def ollama_config():
    return AgentConfig(
        provider="ollama",
        model="llama3.2",
        ollama_host="http://localhost:11434",
        dry_run=False,
        anonymize=False,
    )


# ─── _parse_response tests ──────────────────────────────────────────────────


class TestParseResponse:
    def test_valid_json(self):
        text = '{"success": true, "summary": "test", "data": {}, "actions": [], "confidence": 0.9}'
        result = _parse_response(text)
        assert result is not None
        assert result["success"] is True
        assert result["summary"] == "test"

    def test_json_in_code_fence(self):
        text = '```json\n{"success": true, "summary": "fenced"}\n```'
        result = _parse_response(text)
        assert result is not None
        assert result["summary"] == "fenced"

    def test_json_in_text(self):
        text = 'Here is the result: {"success": false, "summary": "embedded"} end'
        result = _parse_response(text)
        assert result is not None
        assert result["success"] is False

    def test_plain_text_fallback(self):
        text = "Just a plain text response with no JSON"
        result = _parse_response(text)
        assert result is not None
        assert result["success"] is True
        assert "raw" in result["data"]
        assert result["confidence"] == 0.5


# ─── _coerce_data tests ─────────────────────────────────────────────────────


class TestCoerceData:
    def test_dict_passthrough(self):
        assert _coerce_data({"key": "value"}) == {"key": "value"}

    def test_list_to_items(self):
        assert _coerce_data(["a", "b"]) == {"items": ["a", "b"]}

    def test_none_to_empty(self):
        assert _coerce_data(None) == {}

    def test_scalar_to_value(self):
        assert _coerce_data("hello") == {"value": "hello"}


# ─── _coerce_actions tests ──────────────────────────────────────────────────


class TestCoerceActions:
    def test_string_list(self):
        assert _coerce_actions(["a", "b"]) == ["a", "b"]

    def test_dict_items(self):
        result = _coerce_actions([{"action": "do_thing"}, {"name": "other"}])
        assert result == ["do_thing", "other"]

    def test_non_list(self):
        assert _coerce_actions("single") == ["single"]

    def test_empty(self):
        assert _coerce_actions(None) == []


# ─── _build_user_message tests ──────────────────────────────────────────────


class TestBuildUserMessage:
    def test_prompt_only(self):
        msg = _build_user_message("hello", "")
        assert msg == "hello"

    def test_with_context(self):
        msg = _build_user_message("hello", "some context")
        assert "--- Context ---" in msg
        assert "some context" in msg

    def test_with_source_file(self):
        from console_agent.utils.caller_file import SourceFileInfo

        source = SourceFileInfo(
            file_path="/test/file.py",
            file_name="file.py",
            content="print('hello')",
            line=1,
            column=0,
        )
        msg = _build_user_message("hello", "", source)
        assert "file.py" in msg


# ─── Config tests ───────────────────────────────────────────────────────────


class TestOllamaConfig:
    def test_config_accepts_ollama_provider(self):
        config = AgentConfig(provider="ollama", model="llama3.2")
        assert config.provider == "ollama"
        assert config.model == "llama3.2"
        assert config.ollama_host == "http://localhost:11434"

    def test_config_custom_host(self):
        config = AgentConfig(
            provider="ollama",
            ollama_host="http://my-server:11434",
        )
        assert config.ollama_host == "http://my-server:11434"

    def test_default_provider_is_google(self):
        config = AgentConfig()
        assert config.provider == "google"


# ─── call_ollama integration test (mocked) ──────────────────────────────────


def _make_fake_agno_modules():
    """Create fake agno.agent and agno.models.ollama modules for sys.modules injection."""
    MockAgent = MagicMock(name="Agent")
    MockOllamaModel = MagicMock(name="Ollama")

    fake_agent_mod = types.ModuleType("agno.agent")
    fake_agent_mod.Agent = MockAgent

    fake_ollama_mod = types.ModuleType("agno.models.ollama")
    fake_ollama_mod.Ollama = MockOllamaModel

    # Ensure parent modules exist
    fake_models_mod = types.ModuleType("agno.models")

    return MockAgent, MockOllamaModel, {
        "agno.agent": fake_agent_mod,
        "agno.models": fake_models_mod,
        "agno.models.ollama": fake_ollama_mod,
    }


class TestCallOllama:
    @pytest.mark.asyncio
    async def test_gemini_model_defaults_to_llama(self, persona, ollama_config):
        """When model starts with 'gemini', Ollama provider should default to llama3.2."""
        ollama_config_gemini = AgentConfig(
            provider="ollama",
            model="gemini-2.5-flash-lite",
            ollama_host="http://localhost:11434",
        )

        mock_response = MagicMock()
        mock_response.content = {
            "success": True,
            "summary": "test response",
            "data": {"result": "ok"},
            "actions": [],
            "confidence": 0.9,
        }
        mock_response.metrics = None

        MockAgent, MockOllamaModel, fake_mods = _make_fake_agno_modules()
        mock_agent_instance = MagicMock()
        mock_agent_instance.arun = AsyncMock(return_value=mock_response)
        MockAgent.return_value = mock_agent_instance

        with patch.dict(sys.modules, fake_mods):
            result = await call_ollama(
                "test prompt",
                "",
                persona,
                ollama_config_gemini,
            )

        MockOllamaModel.assert_called_once()
        call_kwargs = MockOllamaModel.call_args
        assert call_kwargs[1]["id"] == "llama3.2"
        assert result.success is True
        assert result.metadata.model == "llama3.2"

    @pytest.mark.asyncio
    async def test_tools_warning_ignored(self, persona, ollama_config):
        """Tools should be silently ignored for Ollama provider."""
        options = AgentCallOptions(tools=["google_search"])

        mock_response = MagicMock()
        mock_response.content = {
            "success": True,
            "summary": "no tools used",
            "data": {},
            "actions": [],
            "confidence": 0.8,
        }
        mock_response.metrics = None

        MockAgent, MockOllamaModel, fake_mods = _make_fake_agno_modules()
        mock_agent_instance = MagicMock()
        mock_agent_instance.arun = AsyncMock(return_value=mock_response)
        MockAgent.return_value = mock_agent_instance

        with patch.dict(sys.modules, fake_mods):
            result = await call_ollama(
                "test prompt",
                "",
                persona,
                ollama_config,
                options,
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_structured_output(self, persona, ollama_config):
        """Test the structured output path returns proper AgentResult."""
        mock_response = MagicMock()
        mock_response.content = {
            "success": True,
            "summary": "Analysis complete",
            "reasoning": "Thought about it",
            "data": {"finding": "everything looks good"},
            "actions": ["analyzed"],
            "confidence": 0.95,
        }
        mock_response.metrics = MagicMock()
        mock_response.metrics.total_tokens = 150

        MockAgent, MockOllamaModel, fake_mods = _make_fake_agno_modules()
        mock_agent_instance = MagicMock()
        mock_agent_instance.arun = AsyncMock(return_value=mock_response)
        MockAgent.return_value = mock_agent_instance

        with patch.dict(sys.modules, fake_mods):
            result = await call_ollama(
                "analyze this code",
                "def foo(): pass",
                persona,
                ollama_config,
            )

        assert result.success is True
        assert result.summary == "Analysis complete"
        assert result.confidence == 0.95
        assert result.data["finding"] == "everything looks good"
        assert result.metadata.tokens_used == 150
        assert result.metadata.model == "llama3.2"

    @pytest.mark.asyncio
    async def test_text_fallback(self, persona, ollama_config):
        """Test fallback when Ollama returns plain text instead of JSON."""
        mock_response = MagicMock()
        mock_response.content = "Here is my analysis: the code looks fine overall."
        mock_response.metrics = None

        MockAgent, MockOllamaModel, fake_mods = _make_fake_agno_modules()
        mock_agent_instance = MagicMock()
        mock_agent_instance.arun = AsyncMock(return_value=mock_response)
        MockAgent.return_value = mock_agent_instance

        with patch.dict(sys.modules, fake_mods):
            result = await call_ollama(
                "review code",
                "",
                persona,
                ollama_config,
            )

        assert result.success is True
        assert "raw" in result.data
        assert result.confidence == 0.5
