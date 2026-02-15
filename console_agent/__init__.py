"""
console-agent — as easy as print()

Drop agent() anywhere in your Python code to execute agentic AI workflows.
Powered by Google Gemini via Agno.

Usage::

    from console_agent import agent, init

    # Optional configuration (works with sensible defaults + GEMINI_API_KEY env)
    init(api_key="...", model="gemini-2.5-flash-lite")

    # Fire-and-forget (default)
    agent("analyze this error", context=error)

    # Blocking mode — get result
    result = agent("validate email format", context=email, mode="blocking")

    # Persona shortcuts
    agent.security("audit SQL query", context=query)
    agent.debug("investigate slow query", context={"duration": dur, "sql": sql})
    agent.architect("review API design", context=endpoint)

    # Async
    result = await agent.arun("analyze this", context=data)

    # Verbose output (full [AGENT] tree, spinners, metadata)
    init(verbose=True)
    # or per-call:
    agent("analyze this", verbose=True)
"""

from __future__ import annotations

__version__ = "1.0.0"

import asyncio
import threading
from typing import Any, Optional

from .core import DEFAULT_CONFIG, execute_agent, get_config, update_config
from .types import (
    AgentCallOptions,
    AgentConfig,
    AgentResult,
    BudgetConfig,
    LogLevel,
    PersonaName,
    ResponseFormat,
    ThinkingConfig,
    ToolCall,
    ToolName,
)
from .utils.format import set_log_level


# ─── Re-exports ──────────────────────────────────────────────────────────────

__all__ = [
    "agent",
    "init",
    "AgentConfig",
    "AgentCallOptions",
    "AgentResult",
    "BudgetConfig",
    "LogLevel",
    "PersonaName",
    "ResponseFormat",
    "ThinkingConfig",
    "ToolCall",
    "ToolName",
    "DEFAULT_CONFIG",
]


# ─── Init ────────────────────────────────────────────────────────────────────


def init(**kwargs: Any) -> None:
    """Initialize console-agent with custom configuration.

    Call this once at app startup. Works with sensible defaults if not called.

    Example::

        init(
            api_key=os.environ["GEMINI_API_KEY"],
            model="gemini-2.5-flash-lite",
            persona="debugger",
            budget={"max_calls_per_day": 200},
            verbose=True,
        )
    """
    update_config(**kwargs)
    full_config = get_config()
    set_log_level(full_config.log_level)


# ─── Helper: run async from sync ─────────────────────────────────────────────


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from sync context.

    Handles the case where an event loop is already running
    (e.g. in Jupyter notebooks) by running in a background thread.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're inside an already-running event loop (Jupyter, etc.)
        # Run in a background thread with its own loop
        result_container: list[Any] = [None]
        exception_container: list[Optional[Exception]] = [None]

        def _run() -> None:
            try:
                result_container[0] = asyncio.run(coro)
            except Exception as exc:
                exception_container[0] = exc

        thread = threading.Thread(target=_run)
        thread.start()
        thread.join()

        if exception_container[0] is not None:
            raise exception_container[0]
        return result_container[0]
    else:
        return asyncio.run(coro)


# ─── Agent Callable ──────────────────────────────────────────────────────────


class _AgentCallable:
    """Makes agent() callable with persona shortcut methods.

    This is the Python equivalent of the TypeScript Proxy-based console.agent.
    """

    def __call__(
        self,
        prompt: str,
        context: Any = None,
        *,
        model: Optional[str] = None,
        tools: Optional[list[Any]] = None,
        persona: Optional[PersonaName] = None,
        mode: Optional[str] = None,
        thinking: Optional[dict[str, Any]] = None,
        schema_model: Any = None,
        response_format: Optional[dict[str, Any]] = None,
        verbose: Optional[bool] = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Execute an agent call synchronously.

        Args:
            prompt: The task or question for the agent.
            context: Additional context (error objects, data, code, etc.).
            model: Override model for this call.
            tools: Native Gemini tools to enable. Accepts tool names like
                ``["google_search"]``, ``["google_search", "url_context"]``,
                ``["code_execution"]``, or ToolConfig objects.
            persona: Force persona for this call.
            mode: Override execution mode ('fire-and-forget' or 'blocking').
            thinking: Thinking/reasoning config dict.
            schema_model: Pydantic model class for typed structured output.
            response_format: Plain JSON Schema for structured output.
            verbose: Override verbose output for this call.
        """
        options = self._build_options(
            model=model,
            tools=tools,
            persona=persona,
            mode=mode,
            thinking=thinking,
            schema_model=schema_model,
            response_format=response_format,
            verbose=verbose,
        )

        config = get_config()

        if config.mode == "fire-and-forget" and not (options and options.mode):
            # Fire-and-forget: run but still return result for compatibility
            result = _run_async(execute_agent(prompt, context, options))
            return result

        return _run_async(execute_agent(prompt, context, options))

    async def arun(
        self,
        prompt: str,
        context: Any = None,
        *,
        model: Optional[str] = None,
        tools: Optional[list[Any]] = None,
        persona: Optional[PersonaName] = None,
        mode: Optional[str] = None,
        thinking: Optional[dict[str, Any]] = None,
        schema_model: Any = None,
        response_format: Optional[dict[str, Any]] = None,
        verbose: Optional[bool] = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Execute an agent call asynchronously.

        Same parameters as __call__, but returns an awaitable.
        """
        options = self._build_options(
            model=model,
            tools=tools,
            persona=persona,
            mode=mode,
            thinking=thinking,
            schema_model=schema_model,
            response_format=response_format,
            verbose=verbose,
        )
        return await execute_agent(prompt, context, options)

    # ─── Persona Shortcuts ────────────────────────────────────────────────

    def security(
        self, prompt: str, context: Any = None, **kwargs: Any
    ) -> AgentResult:
        """Run with security persona."""
        return self(prompt, context, persona="security", **kwargs)

    def debug(
        self, prompt: str, context: Any = None, **kwargs: Any
    ) -> AgentResult:
        """Run with debugger persona."""
        return self(prompt, context, persona="debugger", **kwargs)

    def architect(
        self, prompt: str, context: Any = None, **kwargs: Any
    ) -> AgentResult:
        """Run with architect persona."""
        return self(prompt, context, persona="architect", **kwargs)

    # ─── Internal ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_options(
        model: Optional[str] = None,
        tools: Optional[list[Any]] = None,
        persona: Optional[PersonaName] = None,
        mode: Optional[str] = None,
        thinking: Optional[dict[str, Any]] = None,
        schema_model: Any = None,
        response_format: Optional[dict[str, Any]] = None,
        verbose: Optional[bool] = None,
    ) -> Optional[AgentCallOptions]:
        """Build AgentCallOptions from keyword arguments."""
        has_any = any(
            v is not None
            for v in [model, tools, persona, mode, thinking, schema_model, response_format, verbose]
        )
        if not has_any:
            return None

        thinking_config = ThinkingConfig(**thinking) if thinking else None
        rf = ResponseFormat(**response_format) if response_format else None

        return AgentCallOptions(
            model=model,
            tools=tools,
            persona=persona,
            mode=mode,  # type: ignore[arg-type]
            thinking=thinking_config,
            schema_model=schema_model,
            response_format=rf,
            verbose=verbose,
        )


# ─── Module-level singleton ──────────────────────────────────────────────────

agent = _AgentCallable()
