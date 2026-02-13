"""Tests for persona detection and lookup."""

from console_agent.personas import detect_persona, get_persona, personas


class TestGetPersona:
    def test_get_debugger(self):
        p = get_persona("debugger")
        assert p.name == "debugger"
        assert p.icon == "🐛"

    def test_get_security(self):
        p = get_persona("security")
        assert p.name == "security"
        assert p.icon == "🛡️"

    def test_get_architect(self):
        p = get_persona("architect")
        assert p.name == "architect"
        assert p.icon == "🏗️"

    def test_get_general(self):
        p = get_persona("general")
        assert p.name == "general"
        assert p.icon == "🔍"


class TestDetectPersona:
    def test_detects_security_from_keywords(self):
        p = detect_persona("audit this for SQL injection vulnerabilities", "general")
        assert p.name == "security"

    def test_detects_debugger_from_keywords(self):
        p = detect_persona("debug this error in my code", "general")
        assert p.name == "debugger"

    def test_detects_architect_from_keywords(self):
        p = detect_persona("review this system design", "general")
        assert p.name == "architect"

    def test_falls_back_to_default(self):
        p = detect_persona("tell me a joke", "general")
        assert p.name == "general"

    def test_security_has_priority_over_debugger(self):
        # "security" keyword should win over "debug"
        p = detect_persona("debug this security vulnerability", "general")
        assert p.name == "security"

    def test_uses_explicit_default(self):
        p = detect_persona("do something random", "debugger")
        assert p.name == "debugger"

    def test_performance_keyword_triggers_debugger(self):
        p = detect_persona("optimize this slow function", "general")
        assert p.name == "debugger"

    def test_architecture_keyword_triggers_architect(self):
        p = detect_persona("refactor this module", "general")
        assert p.name == "architect"


class TestPersonaDefinitions:
    def test_all_personas_have_system_prompts(self):
        for name, persona in personas.items():
            assert persona.system_prompt, f"{name} has empty system prompt"

    def test_all_personas_have_icons(self):
        for name, persona in personas.items():
            assert persona.icon, f"{name} has no icon"

    def test_all_personas_have_labels(self):
        for name, persona in personas.items():
            assert persona.label, f"{name} has no label"

    def test_general_has_no_keywords(self):
        assert get_persona("general").keywords == []

    def test_specific_personas_have_keywords(self):
        for name in ("debugger", "security", "architect"):
            p = get_persona(name)  # type: ignore
            assert len(p.keywords) > 0, f"{name} has no keywords"
