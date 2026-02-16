"""
Example: Using console-agent with Ollama (local models).

Prerequisites:
1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull llama3.2`
3. Install the optional dependency: `pip install console-agent[ollama]`

Usage:
    python examples/ollama_usage.py
"""

from console_agent import agent, init

# ─── Configure for Ollama ─────────────────────────────────────────────────────

init(
    provider="ollama",
    model="llama3.2",              # Any model from `ollama list`
    ollama_host="http://localhost:11434",  # Default Ollama host
    verbose=True,
    anonymize=False,               # No need to anonymize for local models
)

# ─── Basic Usage ──────────────────────────────────────────────────────────────

# Simple prompt — works exactly the same as with Google
result = agent("What are the main benefits of using Python type hints?")
print(f"Success: {result.success}")
print(f"Summary: {result.summary}")

# ─── With Context ─────────────────────────────────────────────────────────────

code = """
def calculate_total(items, tax_rate):
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total * (1 + tax_rate)
"""

result = agent("Review this code for potential issues", context=code)
print(f"\nCode Review: {result.summary}")

# ─── Persona Shortcuts ───────────────────────────────────────────────────────

# These work identically to the Google provider
result = agent.debug("Why might this function return None unexpectedly?", context=code)
print(f"\nDebug: {result.summary}")

result = agent.security("Check this code for security vulnerabilities", context=code)
print(f"\nSecurity: {result.summary}")

result = agent.architect("Suggest improvements to this function's design", context=code)
print(f"\nArchitect: {result.summary}")

# ─── Note: Tools are NOT supported with Ollama ───────────────────────────────
# The following tools are Google/Gemini-specific and will be ignored:
# - google_search
# - url_context
# - code_execution
#
# If you need these tools, use provider="google" with a GEMINI_API_KEY.
