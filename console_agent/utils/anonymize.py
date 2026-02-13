"""
Content anonymization — strips secrets, PII, and sensitive data
before sending to the AI provider.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union

# ─── Patterns for sensitive content ──────────────────────────────────────────

_PATTERNS = {
    # Private keys (must run first — multiline)
    "private_key": re.compile(
        r"-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----"
    ),
    # Connection strings
    "connection_string": re.compile(
        r"(?:mongodb|postgres|mysql|redis|amqp)://[^\s'\"]+", re.IGNORECASE
    ),
    # AWS keys
    "aws_key": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    # Bearer tokens
    "bearer": re.compile(r"Bearer\s+[A-Za-z0-9_\-/.+]{20,}", re.IGNORECASE),
    # API keys and tokens (long alphanumeric strings near sensitive keywords)
    "api_key": re.compile(
        r"(?:api[_\-]?key|token|secret|password|credential|auth)['\"\:\s=]+['\"]?"
        r"([A-Za-z0-9_\-/.]{20,})['\"]?",
        re.IGNORECASE,
    ),
    # .env style secrets
    "env_secret": re.compile(
        r"^(?:DATABASE_URL|DB_PASSWORD|SECRET_KEY|PRIVATE_KEY|AWS_SECRET|STRIPE_KEY|SENDGRID_KEY)[=:].+$",
        re.MULTILINE,
    ),
    # Email addresses
    "email": re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    # IPv4 addresses
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    # IPv6 addresses (simplified)
    "ipv6": re.compile(r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"),
}


def anonymize(content: str) -> str:
    """Anonymize sensitive content in a string.

    Replaces detected secrets/PII with safe placeholders.
    """
    result = content

    result = _PATTERNS["private_key"].sub("[REDACTED_PRIVATE_KEY]", result)
    result = _PATTERNS["connection_string"].sub("[REDACTED_CONNECTION_STRING]", result)
    result = _PATTERNS["aws_key"].sub("[REDACTED_AWS_KEY]", result)
    result = _PATTERNS["bearer"].sub("Bearer [REDACTED_TOKEN]", result)

    def _redact_api_key(match: re.Match) -> str:
        full = match.group(0)
        # Find the separator position
        for i, ch in enumerate(full):
            if ch in ("'", '"', ":", " ", "="):
                return full[:i] + ": [REDACTED]"
        return "[REDACTED]"

    result = _PATTERNS["api_key"].sub(_redact_api_key, result)

    def _redact_env(match: re.Match) -> str:
        full = match.group(0)
        for i, ch in enumerate(full):
            if ch in ("=", ":"):
                return full[:i] + "=[REDACTED]"
        return "[REDACTED]"

    result = _PATTERNS["env_secret"].sub(_redact_env, result)
    result = _PATTERNS["email"].sub("[EMAIL]", result)
    result = _PATTERNS["ipv4"].sub("[IP]", result)
    result = _PATTERNS["ipv6"].sub("[IP]", result)

    return result


def anonymize_value(value: Any) -> Any:
    """Anonymize any value — handles strings, dicts, lists, and primitives."""
    if isinstance(value, str):
        return anonymize(value)
    if isinstance(value, list):
        return [anonymize_value(item) for item in value]
    if isinstance(value, dict):
        return {k: anonymize_value(v) for k, v in value.items()}
    return value
