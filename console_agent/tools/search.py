"""
Google Search tool wrapper.
Uses Google's built-in search grounding for real-time information retrieval.

In Agno/Gemini, Google Search grounding is enabled via:
    Gemini(id="...", search=True)

This allows the model to search the web for up-to-date information
and ground its responses in real search results.
"""

GOOGLE_SEARCH_TOOL = "google_search"
