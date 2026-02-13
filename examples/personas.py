"""
Persona shortcuts — security, debug, architect

Each persona has a specialized system prompt tuned for its domain.
Auto-detection also works: mention "SQL injection" and security kicks in.

Run with:
    GEMINI_API_KEY=your-key python examples/personas.py
"""

import os

from console_agent import agent, init

init(
    api_key=os.environ.get("GEMINI_API_KEY"),
    model="gemini-2.5-flash-lite",
    mode="blocking",
    log_level="info",
)

# ═══════════════════════════════════════════════════════════════
# 1. Security persona — SQL injection audit
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Security Persona ━━━")
result = agent.security(
    "Check this input for SQL injection vulnerabilities",
    context="admin' OR '1'='1; DROP TABLE users; --",
)
print(f"Summary: {result.summary}")
print(f"Success: {result.success}")
print(f"Confidence: {result.confidence}")

# ═══════════════════════════════════════════════════════════════
# 2. Debug persona — analyze a crash
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Debug Persona ━━━")
try:
    1 / 0
except ZeroDivisionError as e:
    result = agent.debug("Why did this fail?", context=str(e))
    print(f"Summary: {result.summary}")
    print(f"Actions: {result.actions}")

# ═══════════════════════════════════════════════════════════════
# 3. Architect persona — API design review
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Architect Persona ━━━")
result = agent.architect(
    "Review this REST API design",
    context={
        "endpoints": [
            "GET /users/:id",
            "POST /users",
            "DELETE /users/:id",
        ],
        "concern": "Missing PATCH for updates?",
    },
)
print(f"Summary: {result.summary}")

# ═══════════════════════════════════════════════════════════════
# 4. Auto-detect persona from keywords
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Auto-detect Persona ━━━")
# Mentions "XSS" → security persona auto-selected
result = agent(
    "Is this code vulnerable to XSS attacks?",
    context='<div dangerouslySetInnerHTML={{ __html: userInput }} />',
)
print(f"Summary: {result.summary}")

print("\n✅ Persona examples completed!")
