"""
URL Context tool wrapper.
Uses Gemini's built-in URL context grounding for analyzing web page content.

In Agno/Gemini, URL context is enabled via:
    Gemini(id="...", url_context=True)

This allows the model to fetch and analyze content from URLs provided in prompts.
"""

URL_CONTEXT_TOOL = "url_context"
