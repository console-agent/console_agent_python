"""Tests for agent configuration."""

from console_agent.core import DEFAULT_CONFIG, get_config, update_config
from console_agent.types import AgentConfig


class TestDefaultConfig:
    def test_default_provider(self):
        assert DEFAULT_CONFIG.provider == "google"

    def test_default_model(self):
        assert DEFAULT_CONFIG.model == "gemini-2.5-flash-lite"

    def test_default_persona(self):
        assert DEFAULT_CONFIG.persona == "general"

    def test_default_mode(self):
        assert DEFAULT_CONFIG.mode == "fire-and-forget"

    def test_default_timeout(self):
        assert DEFAULT_CONFIG.timeout == 10000

    def test_default_anonymize(self):
        assert DEFAULT_CONFIG.anonymize is True

    def test_default_dry_run(self):
        assert DEFAULT_CONFIG.dry_run is False

    def test_default_log_level(self):
        assert DEFAULT_CONFIG.log_level == "info"

    def test_default_budget(self):
        assert DEFAULT_CONFIG.budget.max_calls_per_day == 100
        assert DEFAULT_CONFIG.budget.max_tokens_per_call == 8000
        assert DEFAULT_CONFIG.budget.cost_cap_daily == 1.0


class TestUpdateConfig:
    def setup_method(self):
        """Reset config to defaults before each test."""
        update_config(
            provider="google",
            model="gemini-2.5-flash-lite",
            persona="general",
            mode="fire-and-forget",
            timeout=10000,
            anonymize=True,
            dry_run=False,
            log_level="info",
        )

    def test_update_model(self):
        update_config(model="gemini-3-flash-preview")
        config = get_config()
        assert config.model == "gemini-3-flash-preview"

    def test_update_persona(self):
        update_config(persona="debugger")
        config = get_config()
        assert config.persona == "debugger"

    def test_update_mode(self):
        update_config(mode="blocking")
        config = get_config()
        assert config.mode == "blocking"

    def test_update_dry_run(self):
        update_config(dry_run=True)
        config = get_config()
        assert config.dry_run is True

    def test_update_budget(self):
        update_config(budget={"max_calls_per_day": 200})
        config = get_config()
        assert config.budget.max_calls_per_day == 200
        # Other budget fields should retain defaults
        assert config.budget.max_tokens_per_call == 8000

    def test_get_config_returns_copy(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is not c2
        assert c1.model == c2.model
