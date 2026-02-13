"""
Persona registry — auto-detection and lookup.
"""

from __future__ import annotations

from typing import Dict

from ..types import PersonaDefinition, PersonaName
from .architect import architect_persona
from .debugger import debugger_persona
from .general import general_persona
from .security import security_persona

personas: Dict[PersonaName, PersonaDefinition] = {
    "debugger": debugger_persona,
    "security": security_persona,
    "architect": architect_persona,
    "general": general_persona,
}


def detect_persona(prompt: str, default_persona: PersonaName) -> PersonaDefinition:
    """Auto-detect the best persona based on keywords in the prompt.

    Returns the explicitly set persona if no keywords match.
    """
    lower = prompt.lower()

    # Check specific personas in priority order: security > debugger > architect
    for name in ("security", "debugger", "architect"):
        persona = personas[name]  # type: ignore[index]
        if any(kw in lower for kw in persona.keywords):
            return persona

    return personas[default_persona]


def get_persona(name: PersonaName) -> PersonaDefinition:
    """Get a persona by name."""
    return personas[name]
