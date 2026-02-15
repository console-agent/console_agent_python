"""
Google AI provider — integrates with Gemini via Agno.

Two execution paths (mirroring the TypeScript SDK):
1. WITHOUT tools → Agno Agent with structured output (use_json_mode=True)
2. WITH tools → Agno Agent with provider tools (google_search, url_context,
   code_execution). Tools are incompatible with structured JSON output at
   the Gemini API level, so we instruct the model via prompt and parse the
   text response.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from ..tools import TOOLS_MIN_TIMEOUT, has_explicit_tools, resolve_tools
from ..types import (
    AgentCallOptions,
    AgentConfig,
    AgentMetadata,
    AgentOutputSchema,
    AgentResult,
    FileAttachment,
    PersonaDefinition,
    ToolCall,
)
from ..utils.caller_file import SourceFileInfo, format_source_for_context
from ..utils.format import log_debug


# ─── JSON prompt suffix for tool-mode (no structured output available) ───────

JSON_RESPONSE_INSTRUCTION = (
    "\n\nIMPORTANT: You MUST respond with ONLY a valid JSON object "
    "(no markdown, no code fences, no extra text).\n"
    'Use this exact format:\n'
    '{"success": true, "summary": "one-line conclusion", '
    '"reasoning": "your thought process", '
    '"data": {"result": "primary finding"}, '
    '"actions": ["tools/steps used"], "confidence": 0.95}'
)


def _coerce_data(raw: Any) -> Dict[str, Any]:
    """Ensure the data field is always a dict (LLM sometimes returns a list)."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {"items": raw}
    if raw is None:
        return {}
    return {"value": raw}


def _coerce_actions(raw: Any) -> List[str]:
    """Ensure actions is always a list of strings (LLM sometimes returns dicts)."""
    if not isinstance(raw, list):
        return [str(raw)] if raw else []
    result: List[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # Extract a meaningful string from the dict
            result.append(
                item.get("recommendation")
                or item.get("action")
                or item.get("description")
                or item.get("name")
                or json.dumps(item, default=str)
            )
        else:
            result.append(str(item))
    return result


def _parse_response(text: str) -> Optional[Dict[str, Any]]:
    """Fallback parser for unstructured text responses."""
    # Try direct JSON parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try extracting JSON from markdown code fences
    match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # Try finding JSON object in text
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    # Return as raw fallback
    return {
        "success": True,
        "summary": text[:200],
        "data": {"raw": text},
        "actions": [],
        "confidence": 0.5,
    }


def _extract_tokens(run_response: Any) -> int:
    """Extract token usage from an Agno run response."""
    tokens_used = 0
    if hasattr(run_response, "metrics") and run_response.metrics:
        metrics = run_response.metrics
        tokens_used = getattr(metrics, "total_tokens", 0) or 0
        if not tokens_used:
            input_tokens = getattr(metrics, "input_tokens", 0) or 0
            output_tokens = getattr(metrics, "output_tokens", 0) or 0
            tokens_used = input_tokens + output_tokens
    return tokens_used


# ─── Main Entry Point ────────────────────────────────────────────────────────


def _build_user_message(
    prompt: str,
    context: str,
    source_file: Optional[SourceFileInfo] = None,
) -> str:
    """Build the user message combining prompt, context, and auto-detected source."""
    parts: list[str] = [prompt]

    if context:
        parts.append(f"\n--- Context ---\n{context}")

    if source_file:
        formatted = format_source_for_context(source_file)
        parts.append(f"\n{formatted}")

    return "\n".join(parts)


def _build_agno_files(
    files: Optional[List[FileAttachment]],
) -> Optional[List[Any]]:
    """Convert FileAttachment list to Agno File objects."""
    if not files:
        return None

    from pathlib import Path

    from agno.media import File

    agno_files: List[Any] = []
    for fa in files:
        file_path = Path(fa.filepath)
        log_debug(f"Attaching file: {file_path.name}")
        agno_files.append(File(filepath=file_path))

    return agno_files if agno_files else None


async def call_google(
    prompt: str,
    context: str,
    persona: PersonaDefinition,
    config: AgentConfig,
    options: Optional[AgentCallOptions] = None,
    source_file: Optional[SourceFileInfo] = None,
    files: Optional[List[FileAttachment]] = None,
) -> AgentResult:
    """Call the Google Gemini provider via Agno Agent.

    Routes to one of two paths:
    1. WITH tools → _call_with_tools (provider native tools, text response)
    2. WITHOUT tools → _call_with_structured_output (JSON mode)
    """
    start_time = time.time()
    model_name = (options.model if options and options.model else None) or config.model

    log_debug(f"Using model: {model_name}")
    log_debug(f"Persona: {persona.name}")

    # Resolve API key
    api_key = config.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get(
        "GOOGLE_GENERATIVE_AI_API_KEY"
    )

    # Route: tools or structured output?
    use_tools = has_explicit_tools(options) and not config.local_only

    if use_tools:
        log_debug("Tools requested — using tools path (no structured output)")
        return await _call_with_tools(
            prompt, context, persona, config, options, api_key, model_name, start_time,
            source_file, files,
        )

    log_debug("No tools — using structured output path")
    return await _call_with_structured_output(
        prompt, context, persona, config, options, api_key, model_name, start_time,
        source_file, files,
    )


# ─── Path 1: WITH TOOLS (native Gemini tools, text response) ────────────────


async def _call_with_tools(
    prompt: str,
    context: str,
    persona: PersonaDefinition,
    config: AgentConfig,
    options: Optional[AgentCallOptions],
    api_key: Optional[str],
    model_name: str,
    start_time: float,
    source_file: Optional[SourceFileInfo] = None,
    files: Optional[List[FileAttachment]] = None,
) -> AgentResult:
    """Execute with native Gemini tools (google_search, url_context, code_execution).

    Provider tools are incompatible with structured JSON output at the Gemini
    API level, so we instruct the model via prompt and parse the text response.
    """
    from agno.agent import Agent
    from agno.models.google import Gemini

    # Resolve tool names into Gemini model kwargs
    tool_kwargs = resolve_tools(options.tools) if options and options.tools else {}
    tool_names = [
        (t if isinstance(t, str) else t.type)
        for t in (options.tools if options and options.tools else [])
    ]
    log_debug(f"Tools enabled: {', '.join(tool_names)}")

    # Apply minimum timeout for tools
    effective_timeout = max(config.timeout, TOOLS_MIN_TIMEOUT)
    log_debug(f"Effective timeout: {effective_timeout}ms (tools active)")

    # Build user message (includes source file context)
    user_message = _build_user_message(prompt, context, source_file)

    # Build Agno File objects for explicit file attachments
    agno_files = _build_agno_files(files)

    # Build instructions with JSON response instruction
    instructions = persona.system_prompt + JSON_RESPONSE_INSTRUCTION

    # Create Gemini model with tool flags
    gemini_model = Gemini(id=model_name, api_key=api_key, **tool_kwargs)

    # Create Agno Agent — no use_json_mode (incompatible with provider tools)
    agent = Agent(
        model=gemini_model,
        instructions=instructions,
        markdown=False,
    )

    # Execute the agent (with optional file attachments)
    arun_kwargs: Dict[str, Any] = {}
    if agno_files:
        arun_kwargs["files"] = agno_files
    run_response = await agent.arun(user_message, **arun_kwargs)

    latency_ms = int((time.time() - start_time) * 1000)
    tokens_used = _extract_tokens(run_response)

    log_debug(f"Response received (tools path): {latency_ms}ms, {tokens_used} tokens")

    # Collect tool calls from response metadata
    collected_tool_calls: List[ToolCall] = []
    # Agno may expose tool calls in response messages
    if hasattr(run_response, "messages") and run_response.messages:
        for msg in run_response.messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_name = getattr(tc, "name", None) or getattr(
                        tc, "function", {}).get("name", "unknown"
                    )
                    tc_args = getattr(tc, "arguments", {}) or getattr(
                        tc, "function", {}).get("arguments", {}
                    )
                    collected_tool_calls.append(
                        ToolCall(name=str(tc_name), args=tc_args if isinstance(tc_args, dict) else {})
                    )

    log_debug(f"Tool calls collected: {len(collected_tool_calls)}")

    # Parse text response (no structured output in tools mode)
    content = run_response.content
    text = str(content) if content else ""
    parsed = _parse_response(text)

    return AgentResult(
        success=parsed.get("success", True) if parsed else True,
        summary=parsed.get("summary", text[:200]) if parsed else text[:200],
        reasoning=parsed.get("reasoning") if parsed else None,
        data=_coerce_data(parsed.get("data", {"raw": text}) if parsed else {"raw": text}),
        actions=_coerce_actions(
            parsed.get("actions", []) if parsed else []
        ) or [tc.name for tc in collected_tool_calls],
        confidence=parsed.get("confidence", 0.5) if parsed else 0.5,
        metadata=AgentMetadata(
            model=model_name,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            tool_calls=collected_tool_calls,
            cached=False,
        ),
    )


# ─── Path 2: WITHOUT TOOLS (structured output) ──────────────────────────────


async def _call_with_structured_output(
    prompt: str,
    context: str,
    persona: PersonaDefinition,
    config: AgentConfig,
    options: Optional[AgentCallOptions],
    api_key: Optional[str],
    model_name: str,
    start_time: float,
    source_file: Optional[SourceFileInfo] = None,
    files: Optional[List[FileAttachment]] = None,
) -> AgentResult:
    """Execute without tools — uses structured JSON output via Agno Agent."""
    from agno.agent import Agent
    from agno.models.google import Gemini

    # Determine if we're using a custom schema
    use_custom_schema = bool(
        options and (options.schema_model or options.response_format)
    )

    # Build instructions
    if use_custom_schema:
        instructions = (
            f"{persona.system_prompt}\n\n"
            "IMPORTANT: You must respond with structured data matching the requested "
            "output schema. Do not include AgentResult wrapper fields — just return "
            "the data matching the schema."
        )
    else:
        instructions = persona.system_prompt

    # Build the user message (includes source file context)
    user_message = _build_user_message(prompt, context, source_file)

    # Build Agno File objects for explicit file attachments
    agno_files = _build_agno_files(files)

    # Determine response model
    use_pydantic_schema = bool(options and options.schema_model)
    if use_pydantic_schema:
        log_debug("Using custom Pydantic schema for structured output")
        response_model = options.schema_model
    else:
        response_model = None

    # Build JSON schema instructions for the default case
    if not use_pydantic_schema and not use_custom_schema:
        instructions += (
            "\n\nYou MUST respond with a valid JSON object in this exact format:\n"
            '{"success": true/false, "summary": "one-line conclusion", '
            '"reasoning": "your thought process or null", '
            '"data": {"key": "value pairs with findings"}, '
            '"actions": ["list of steps used"], '
            '"confidence": 0.0-1.0}'
        )

    # Create Agno Agent with Gemini
    agent_kwargs: Dict[str, Any] = {
        "model": Gemini(id=model_name, api_key=api_key),
        "instructions": instructions,
        "markdown": False,
    }
    if use_pydantic_schema:
        agent_kwargs["output_schema"] = response_model
    else:
        agent_kwargs["use_json_mode"] = True

    agent = Agent(**agent_kwargs)

    # Execute the agent (with optional file attachments)
    arun_kwargs: Dict[str, Any] = {}
    if agno_files:
        arun_kwargs["files"] = agno_files
    run_response = await agent.arun(user_message, **arun_kwargs)

    latency_ms = int((time.time() - start_time) * 1000)
    tokens_used = _extract_tokens(run_response)

    log_debug(f"Response received: {latency_ms}ms, {tokens_used} tokens")

    collected_tool_calls: List[ToolCall] = []

    # Handle custom schema output
    if use_custom_schema and run_response.content:
        custom_data: Dict[str, Any] = {}
        if isinstance(run_response.content, dict):
            custom_data = run_response.content
        elif hasattr(run_response.content, "model_dump"):
            custom_data = run_response.content.model_dump()
        else:
            # Try to parse text as JSON (may be markdown-wrapped)
            text_content = str(run_response.content)
            parsed_custom = _parse_response(text_content)
            if parsed_custom and not parsed_custom.get("raw"):
                custom_data = parsed_custom
            else:
                custom_data = {"result": text_content}

        log_debug("Custom schema output received, wrapping in AgentResult")
        return AgentResult(
            success=True,
            summary=f"Structured output returned ({len(custom_data)} fields)",
            data=_coerce_data(custom_data),
            actions=[tc.name for tc in collected_tool_calls],
            confidence=1.0,
            metadata=AgentMetadata(
                model=model_name,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                tool_calls=collected_tool_calls,
                cached=False,
            ),
        )

    # Default schema: use AgentOutputSchema fields directly
    content = run_response.content
    if content is not None:
        # Agno with response_model returns a Pydantic instance
        if isinstance(content, AgentOutputSchema):
            return AgentResult(
                success=content.success,
                summary=content.summary,
                reasoning=content.reasoning,
                data=_coerce_data(content.data),
                actions=content.actions,
                confidence=content.confidence,
                metadata=AgentMetadata(
                    model=model_name,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    tool_calls=collected_tool_calls,
                    cached=False,
                ),
            )

        # It might come back as a dict
        if isinstance(content, dict):
            output = content
            return AgentResult(
                success=output.get("success", True),
                summary=output.get("summary", ""),
                reasoning=output.get("reasoning"),
                data=_coerce_data(output.get("data", {})),
                actions=_coerce_actions(output.get("actions", [])),
                confidence=output.get("confidence", 0.5),
                metadata=AgentMetadata(
                    model=model_name,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    tool_calls=collected_tool_calls,
                    cached=False,
                ),
            )

    # Fallback: parse text response
    text = str(content) if content else ""
    parsed = _parse_response(text)

    return AgentResult(
        success=parsed.get("success", True) if parsed else True,
        summary=parsed.get("summary", text[:200]) if parsed else text[:200],
        reasoning=parsed.get("reasoning") if parsed else None,
        data=_coerce_data(parsed.get("data", {"raw": text}) if parsed else {"raw": text}),
        actions=_coerce_actions(parsed.get("actions", []) if parsed else []),
        confidence=parsed.get("confidence", 0.5) if parsed else 0.5,
        metadata=AgentMetadata(
            model=model_name,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            tool_calls=collected_tool_calls,
            cached=False,
        ),
    )
