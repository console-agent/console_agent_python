"""
Example: Using native Gemini tools with console-agent.

console-agent supports three native Gemini tools:
- google_search: Real-time web search grounding
- url_context: Fetch and analyze URL content
- code_execution: Execute Python code server-side

Tools are opt-in: specify them via the `tools` parameter.

Requires: GEMINI_API_KEY environment variable set.
"""

from console_agent import agent, init

# Initialize with a capable model
init(model="gemini-2.5-flash", verbose=True)


# ─── Google Search ────────────────────────────────────────────────────────────
# Use Google Search grounding for real-time information

result = agent(
    "What are the latest developments in AI agents in 2025?",
    tools=["google_search"],
)
print(f"Search result: {result.summary}\n")


# ─── URL Context ──────────────────────────────────────────────────────────────
# Analyze content from a specific URL

result = agent(
    "Analyze the content of https://docs.agno.com/introduction",
    tools=["url_context"],
)
print(f"URL analysis: {result.summary}\n")


# ─── Search + URL Context (combined) ─────────────────────────────────────────
# Search the web AND analyze URL content for comprehensive results

result = agent(
    "Analyze https://docs.agno.com/introduction and give me latest updates on AI agents",
    tools=["google_search", "url_context"],
)
print(f"Combined result: {result.summary}\n")


# ─── Code Execution ──────────────────────────────────────────────────────────
# Execute Python code server-side for calculations and data processing

result = agent(
    "Calculate the first 20 Fibonacci numbers and return them as a list",
    tools=["code_execution"],
)
print(f"Code execution result: {result.summary}\n")


# ─── All Three Tools ─────────────────────────────────────────────────────────
# Combine search, URL context, and code execution

result = agent(
    "Search for the current Python version, analyze the Python.org downloads page, "
    "and write a script to verify the version number format is valid",
    tools=["google_search", "url_context", "code_execution"],
)
print(f"Full tool result: {result.summary}\n")


# ─── Tools with Persona ──────────────────────────────────────────────────────
# Tools work with persona shortcuts too (via **kwargs)

result = agent.security(
    "Search for the latest OWASP Top 10 and analyze the security implications",
    tools=["google_search"],
)
print(f"Security analysis: {result.summary}\n")
