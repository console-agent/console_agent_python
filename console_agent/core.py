"""
Core agent engine — orchestrates persona selection, budget checks,
anonymization, provider calls, and console output.
"""

from __future__ import annotations

import asyncio
import json
import traceback
from copy import deepcopy
from typing import Any, Optional

from .personas import detect_persona, get_persona
from .providers.google import call_google
from .types import (
    AgentCallOptions,
    AgentConfig,
    AgentMetadata,
    AgentResult,
    BudgetConfig,
    PersonaName,
)
from .utils.anonymize import anonymize_value
from .utils.budget import BudgetTracker
from .utils.format import (
    format_budget_warning,
    format_dry_run,
    format_error,
    format_rate_limit_warning,
    format_result,
    log_debug,
    set_log_level,
    start_spinner,
    stop_spinner,
)
from .utils.rate_limit import RateLimiter

# ─── Default Config ──────────────────────────────────────────────────────────

DEFAULT_CONFIG = AgentConfig()

# ─── Singleton State ─────────────────────────────────────────────────────────

_config: AgentConfig = deepcopy(DEFAULT_CONFIG)
_rate_limiter = RateLimiter(_config.budget.max_calls_per_day)
_budget_tracker = BudgetTracker(_config.budget)


def update_config(new_config: dict[str, Any] | None = None, **kwargs: Any) -> None:
    """Update the global configuration. Reinitializes rate limiter and budget tracker."""
    global _config, _rate_limiter, _budget_tracker

    merged = _config.model_dump()

    if new_config:
        # Merge budget separately
        if "budget" in new_config and isinstance(new_config["budget"], dict):
            merged_budget = merged.get("budget", {})
            merged_budget.update(new_config["budget"])
            new_config = {**new_config, "budget": merged_budget}
        merged.update(new_config)

    if kwargs:
        if "budget" in kwargs and isinstance(kwargs["budget"], dict):
            merged_budget = merged.get("budget", {})
            merged_budget.update(kwargs["budget"])
            kwargs = {**kwargs, "budget": merged_budget}
        merged.update(kwargs)

    _config = AgentConfig(**merged)
    _rate_limiter = RateLimiter(_config.budget.max_calls_per_day)
    _budget_tracker = BudgetTracker(_config.budget)


def get_config() -> AgentConfig:
    """Get the current config (for testing/inspection)."""
    return deepcopy(_config)


# ─── Core Execution ──────────────────────────────────────────────────────────


def _create_error_result(message: str) -> AgentResult:
    return AgentResult(
        success=False,
        summary=message,
        data={},
        actions=[],
        confidence=0,
        metadata=AgentMetadata(
            model=_config.model,
            tokens_used=0,
            latency_ms=0,
            tool_calls=[],
            cached=False,
        ),
    )


def _create_dry_run_result(persona_name: str) -> AgentResult:
    return AgentResult(
        success=True,
        summary=f"[DRY RUN] Would have executed with {persona_name} persona",
        data={"dry_run": True},
        actions=[],
        confidence=1,
        metadata=AgentMetadata(
            model=_config.model,
            tokens_used=0,
            latency_ms=0,
            tool_calls=[],
            cached=False,
        ),
    )


def _estimate_cost(tokens: int, model: str) -> float:
    """Rough cost estimation based on model and token count."""
    cost_per_1m = {
        "gemini-2.5-flash-lite": 0.01,
        "gemini-3-flash-preview": 0.03,
    }
    rate = cost_per_1m.get(model, 0.01)
    return (tokens / 1_000_000) * rate


async def execute_agent(
    prompt: str,
    context: Any = None,
    options: Optional[AgentCallOptions] = None,
) -> AgentResult:
    """Execute an agent call. This is the core function behind agent()."""

    # Resolve verbose flag: per-call option > global config
    verbose = (
        options.verbose
        if (options and options.verbose is not None)
        else _config.verbose
    )

    # Determine persona
    persona_name: PersonaName = (
        options.persona if options and options.persona else _config.persona
    )
    persona = (
        get_persona(options.persona)
        if options and options.persona
        else detect_persona(prompt, persona_name)
    )

    log_debug(f"Selected persona: {persona.name} ({persona.icon})")

    # Dry run — log without calling API
    if _config.dry_run:
        format_dry_run(prompt, persona, context, verbose=verbose)
        return _create_dry_run_result(persona.name)

    # Check rate limits
    if not _rate_limiter.try_consume():
        format_rate_limit_warning(verbose=verbose)
        return _create_error_result("Rate limited — too many calls. Try again later.")

    # Check budget
    budget_check = _budget_tracker.can_make_call()
    if not budget_check.allowed:
        format_budget_warning(budget_check.reason or "Budget exceeded", verbose=verbose)
        return _create_error_result(budget_check.reason or "Budget exceeded")

    # Anonymize context if enabled
    context_str = ""
    if context is not None:
        processed = anonymize_value(context) if _config.anonymize else context

        # Handle Exception objects specially
        if isinstance(context, Exception):
            err_obj = {
                "type": type(context).__name__,
                "message": str(context),
                "traceback": traceback.format_exception(
                    type(context), context, context.__traceback__
                ),
            }
            processed2 = anonymize_value(err_obj) if _config.anonymize else err_obj
            context_str = (
                processed2
                if isinstance(processed2, str)
                else json.dumps(processed2, indent=2, default=str)
            )
        elif isinstance(processed, str):
            context_str = processed
        else:
            context_str = json.dumps(processed, indent=2, default=str)

    # Anonymize prompt if enabled
    processed_prompt = (
        anonymize_value(prompt) if _config.anonymize else prompt
    )
    if not isinstance(processed_prompt, str):
        processed_prompt = str(processed_prompt)

    # Start spinner
    spinner = start_spinner(persona, processed_prompt, verbose=verbose)

    try:
        # Execute with timeout (convert ms to seconds)
        timeout_sec = _config.timeout / 1000.0
        result = await asyncio.wait_for(
            call_google(processed_prompt, context_str, persona, _config, options),
            timeout=timeout_sec,
        )

        # Record usage
        _budget_tracker.record_usage(
            result.metadata.tokens_used,
            _estimate_cost(result.metadata.tokens_used, result.metadata.model),
        )

        # Stop spinner and format output
        stop_spinner(spinner, result.success)
        format_result(result, persona, verbose=verbose)

        return result

    except asyncio.TimeoutError:
        stop_spinner(spinner, False)
        err = TimeoutError(f"Agent timed out after {_config.timeout}ms")
        format_error(err, persona, verbose=verbose)
        return _create_error_result(str(err))

    except Exception as err:
        stop_spinner(spinner, False)
        format_error(err, persona, verbose=verbose)
        return _create_error_result(str(err))
