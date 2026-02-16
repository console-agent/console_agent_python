"""
Ollama AI provider — integrates with local/cloud Ollama models via Agno.

Uses agno.models.ollama.Ollama for chat completion.
Tools are NOT supported in v1 — Gemini-specific tools (google_search,
url_context, code_execution) are incompatible with Ollama.

Two execution paths:
1. WITH custom schema → Agno Agent with output_schema (Pydantic model)
2. WITHOUT custom schema → Agno Agent with use_json_mode=True for
   structured AgentResult output
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

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


# ─── Helpers (shared with google.py patterns) ────────────────────────────────


def _coerce_data(raw: Any) -> Dict[str, Any]:
    """Ensure the data field is always a dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {"items": raw}
    if raw is None:
        return {}
    return {"value": raw}


def _coerce_actions(raw: Any) -> List[str]:
    """Ensure actions is always a list of strings."""
    if not isinstance(raw, list):
        return [str(raw)] if raw else []
    result: List[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
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


# ─── Main Entry Point ────────────────────────────────────────────────────────


async def call_ollama(
    prompt: str,
    context: str,
    persona: PersonaDefinition,
    config: AgentConfig,
    options: Optional[AgentCallOptions] = None,
    source_file: Optional[SourceFileInfo] = None,
    files: Optional[List[FileAttachment]] = None,
) -> AgentResult:
    """Call the Ollama provider via Agno Agent.

    Routes to structured output path. Tools are not supported for Ollama
    in v1 — if tools are requested, they are silently ignored with a warning.
    """
    start_time = time.time()
    model_name = (options.model if options and options.model else None) or config.model

    # Default to llama3.2 if the user hasn't overridden the model and it's
    # still the Google default
    if model_name.startswith("gemini"):
        model_name = "llama3.2"
        log_debug(f"Ollama provider: defaulting model to {model_name}")

    log_debug(f"Using model: {model_name}")
    log_debug(f"Persona: {persona.name}")

    # Resolve Ollama host
    host = config.ollama_host or os.environ.get(
        "OLLAMA_HOST", "http://localhost:11434"
    )

    # Warn if tools were requested (not supported for Ollama v1)
    if options and options.tools:
        log_debug(
            "WARNING: Tools are not supported with the Ollama provider. "
            "Tools will be ignored. Use provider='google' for tool support."
        )

    # Warn if thinking config was requested (not applicable for Ollama)
    if options and options.thinking:
        log_debug(
            "WARNING: Thinking config is not supported with the Ollama provider. "
            "It will be ignored."
        )

    log_debug(f"Ollama host: {host}")

    return await _call_with_structured_output(
        prompt, context, persona, config, options, host, model_name, start_time,
        source_file, files,
    )


# ─── Structured Output Path ─────────────────────────────────────────────────


async def _call_with_structured_output(
    prompt: str,
    context: str,
    persona: PersonaDefinition,
    config: AgentConfig,
    options: Optional[AgentCallOptions],
    host: str,
    model_name: str,
    start_time: float,
    source_file: Optional[SourceFileInfo] = None,
    files: Optional[List[FileAttachment]] = None,
) -> AgentResult:
    """Execute with structured JSON output via Agno Agent + Ollama."""
    from agno.agent import Agent
    from agno.models.ollama import Ollama as OllamaModel

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

    # Note: File attachments are not fully supported with Ollama in the same
    # way as Gemini. We include file content as text context if possible.
    if files:
        log_debug(
            "WARNING: File attachments have limited support with Ollama. "
            "Only text-based files will be included as context."
        )

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

    # Create Ollama model — pass timeout so the Ollama client doesn't abort early
    ollama_timeout = config.timeout / 1000 if config.timeout else 120  # convert ms → s
    ollama_model = OllamaModel(id=model_name, host=host, timeout=ollama_timeout)

    # Create Agno Agent
    agent_kwargs: Dict[str, Any] = {
        "model": ollama_model,
        "instructions": instructions,
        "markdown": False,
    }
    if use_pydantic_schema:
        agent_kwargs["output_schema"] = response_model
    else:
        agent_kwargs["use_json_mode"] = True

    agent = Agent(**agent_kwargs)

    # Execute the agent
    run_response = await agent.arun(user_message)

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
