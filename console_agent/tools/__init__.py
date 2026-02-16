"""
Tools index — resolves tool configurations for Agno agents.

Tools are opt-in only: they are passed to the AI model ONLY when the user
explicitly specifies `tools=[...]` in their agent() call options.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ..types import ToolConfig, ToolName
from .file_analysis import detect_mime_type, prepare_file_content

__all__ = [
    "prepare_file_content",
    "detect_mime_type",
    "resolve_tools",
    "has_explicit_tools",
    "TOOLS_MIN_TIMEOUT",
]

# Minimum timeout (ms) when tools are active.
# Tools like google_search, url_context, and code_execution add latency.
TOOLS_MIN_TIMEOUT = 30_000


def resolve_tools(
    tools: List[Union[ToolName, ToolConfig]],
) -> Dict[str, Any]:
    """Resolve tool names/configs into Agno Gemini model kwargs.

    In Agno's Python SDK, native Gemini tools are exposed as flags on the
    Gemini model constructor:
      - google_search  → Gemini(search=True)
      - url_context    → Gemini(url_context=True)
      - code_execution → Requires google.genai.types.Tool(code_execution={})
                          injected via generative_model_kwargs

    When code_execution is requested (alone or combined), ALL tools are
    injected via generative_model_kwargs to avoid Agno's builtin_tools
    overwriting the code_execution tool.

    Args:
        tools: Array of tool names or tool configs from user's options.

    Returns:
        Dict of kwargs to pass to the Gemini() model constructor.
    """
    # Collect which tools are requested
    has_search = False
    has_url_context = False
    has_code_execution = False

    for tool in tools:
        name: ToolName = tool if isinstance(tool, str) else tool.type

        if name == "google_search":
            has_search = True
        elif name == "url_context":
            has_url_context = True
        elif name == "code_execution":
            has_code_execution = True
        # file_analysis is handled via multimodal content, not as a model tool

    gemini_kwargs: Dict[str, Any] = {}

    if has_code_execution:
        # When code_execution is involved, we must inject ALL tools via
        # generative_model_kwargs because Agno's builtin_tools (from search=True,
        # url_context=True flags) would overwrite code_execution in the config.
        # We import google.genai.types lazily to avoid import errors.
        from google.genai.types import (
            GoogleSearch,
            Tool,
            ToolCodeExecution,
            UrlContext,
        )

        tool_objects: list[Any] = []
        if has_search:
            tool_objects.append(Tool(google_search=GoogleSearch()))
        if has_url_context:
            tool_objects.append(Tool(url_context=UrlContext()))
        tool_objects.append(Tool(code_execution=ToolCodeExecution()))

        gemini_kwargs["generative_model_kwargs"] = {"tools": tool_objects}
    else:
        # Without code_execution, use Agno's native flags (cleaner)
        if has_search:
            gemini_kwargs["search"] = True
        if has_url_context:
            gemini_kwargs["url_context"] = True

    return gemini_kwargs


def has_explicit_tools(
    options: Optional[Any] = None,
) -> bool:
    """Check if any tools were explicitly requested.

    Args:
        options: AgentCallOptions or any object with a `tools` attribute.

    Returns:
        True if tools were explicitly specified and the list is non-empty.
    """
    if options is None:
        return False
    tools = getattr(options, "tools", None)
    return bool(tools and len(tools) > 0)


# ─── Provider compatibility guards ──────────────────────────────────────────

# Tools that are only available with the Google/Gemini provider.
GOOGLE_ONLY_TOOLS = {"google_search", "url_context", "code_execution"}


def validate_tools_for_provider(
    tools: List[Union[ToolName, "ToolConfig"]],
    provider: str,
) -> List[Union[ToolName, "ToolConfig"]]:
    """Filter out tools that are incompatible with the given provider.

    For non-Google providers, Gemini-specific tools are removed with a warning.

    Args:
        tools: The requested tool list.
        provider: The active provider name (e.g. "google", "ollama").

    Returns:
        Filtered list of compatible tools.
    """
    if provider == "google":
        return tools

    from ..utils.format import log_debug

    compatible: List[Union[ToolName, "ToolConfig"]] = []
    for tool in tools:
        name: str = tool if isinstance(tool, str) else tool.type
        if name in GOOGLE_ONLY_TOOLS:
            log_debug(
                f"WARNING: Tool '{name}' is only available with the Google provider. "
                f"Skipping for provider '{provider}'."
            )
        else:
            compatible.append(tool)
    return compatible
