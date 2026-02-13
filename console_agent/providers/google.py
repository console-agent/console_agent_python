"""
Google AI provider — integrates with Gemini via Agno.
Uses Agno's Agent with Gemini model for multi-step reasoning + structured output.
This is the only provider in v1.0.
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
    PersonaDefinition,
    ToolCall,
)
from ..utils.format import log_debug


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


async def call_google(
    prompt: str,
    context: str,
    persona: PersonaDefinition,
    config: AgentConfig,
    options: Optional[AgentCallOptions] = None,
) -> AgentResult:
    """Call the Google Gemini provider via Agno Agent."""
    # Lazy imports to avoid module-level ImportError when agno/google-genai
    # versions are mismatched (only fails when actually calling the provider).
    from agno.agent import Agent
    from agno.models.google import Gemini

    start_time = time.time()
    model_name = (options.model if options and options.model else None) or config.model

    log_debug(f"Using model: {model_name}")
    log_debug(f"Persona: {persona.name}")

    # Resolve API key
    api_key = config.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get(
        "GOOGLE_GENERATIVE_AI_API_KEY"
    )

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

    # Build the user message with context
    user_message = f"{prompt}\n\n--- Context ---\n{context}" if context else prompt

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

    # Execute the agent
    run_response = await agent.arun(user_message)

    latency_ms = int((time.time() - start_time) * 1000)

    # Extract token usage from response
    tokens_used = 0
    if hasattr(run_response, "metrics") and run_response.metrics:
        metrics = run_response.metrics
        tokens_used = getattr(metrics, "total_tokens", 0) or 0
        if not tokens_used:
            input_tokens = getattr(metrics, "input_tokens", 0) or 0
            output_tokens = getattr(metrics, "output_tokens", 0) or 0
            tokens_used = input_tokens + output_tokens

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