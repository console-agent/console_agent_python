"""
Console formatting — rich output with colors, icons, and tree structure.
Uses the 'rich' library for spinners, colors, and structured output.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from ..types import AgentResult, LogLevel, PersonaDefinition

_console = Console()
_current_log_level: LogLevel = "info"

_LOG_LEVELS: list[LogLevel] = ["silent", "errors", "info", "debug"]


def set_log_level(level: LogLevel) -> None:
    global _current_log_level
    _current_log_level = level


def _should_log(level: LogLevel) -> bool:
    return _LOG_LEVELS.index(_current_log_level) >= _LOG_LEVELS.index(level)


# ─── Spinner Management ──────────────────────────────────────────────────────


class SpinnerHandle:
    """Wraps a Rich Live spinner so we can start/stop it."""

    def __init__(self, live: Live, text: str) -> None:
        self._live = live
        self._text = text

    def stop(self, success: bool) -> None:
        self._live.stop()
        prefix = "[dim]\\[AGENT][/dim]"
        icon = "[green]✓[/green]" if success else "[red]✗[/red]"
        _console.print(f"{prefix} {icon} {self._text}")


def start_spinner(persona: PersonaDefinition, prompt: str) -> Optional[SpinnerHandle]:
    if not _should_log("info"):
        return None

    truncated = prompt[:57] + "..." if len(prompt) > 60 else prompt
    text = f"{persona.icon} {persona.label}... [dim]{truncated}[/dim]"

    spinner = Spinner("dots", text=text)
    live = Live(spinner, console=_console, transient=True)
    live.start()
    return SpinnerHandle(live, text)


def stop_spinner(spinner: Optional[SpinnerHandle], success: bool) -> None:
    if spinner is not None:
        spinner.stop(success)


# ─── Result Formatting ──────────────────────────────────────────────────────


def format_result(result: AgentResult, persona: PersonaDefinition) -> None:
    if not _should_log("info"):
        return

    prefix = "[dim]\\[AGENT][/dim]"

    if result.confidence >= 0.8:
        conf_style = "green"
    elif result.confidence >= 0.5:
        conf_style = "yellow"
    else:
        conf_style = "red"

    status_icon = "[green]✓[/green]" if result.success else "[red]✗[/red]"

    _console.print()
    _console.print(f"{prefix} {persona.icon} [bold]{persona.label}[/bold] Complete")
    _console.print(f"{prefix} ├─ {status_icon} {result.summary}")

    # Show actions / tools used
    for action in result.actions:
        _console.print(f"{prefix} ├─ [dim]Tool:[/dim] [cyan]{action}[/cyan]")

    # Show key data points
    for key, value in result.data.items():
        display_value = value if isinstance(value, str) else json.dumps(value)
        _console.print(f"{prefix} ├─ [dim]{key}:[/dim] {display_value}")

    # Show reasoning if available
    if result.reasoning:
        lines = result.reasoning.split("\n")[:3]
        _console.print(f"{prefix} ├─ [dim]Reasoning:[/dim]")
        for line in lines:
            _console.print(f"{prefix} │  [dim]{line.strip()}[/dim]")

    # Footer with metadata
    confidence = f"[{conf_style}]confidence: {result.confidence:.2f}[/{conf_style}]"
    latency = f"[dim]{result.metadata.latency_ms}ms[/dim]"
    tokens = f"[dim]{result.metadata.tokens_used} tokens[/dim]"
    cached = " [green](cached)[/green]" if result.metadata.cached else ""

    _console.print(f"{prefix} └─ {confidence} | {latency} | {tokens}{cached}")
    _console.print()


# ─── Error Formatting ────────────────────────────────────────────────────────


def format_error(error: Exception, persona: PersonaDefinition) -> None:
    if not _should_log("errors"):
        return

    prefix = "[dim]\\[AGENT][/dim]"
    _console.print()
    _console.print(f"{prefix} {persona.icon} [red]Error:[/red] {error}")
    if _should_log("debug"):
        import traceback
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        _console.print(f"{prefix} [dim]{''.join(tb)}[/dim]")
    _console.print()


# ─── Budget Warning ──────────────────────────────────────────────────────────


def format_budget_warning(reason: str) -> None:
    if not _should_log("errors"):
        return
    prefix = "[dim]\\[AGENT][/dim]"
    _console.print(f"{prefix} [yellow]⚠ Budget limit:[/yellow] {reason}")


# ─── Rate Limit Warning ─────────────────────────────────────────────────────


def format_rate_limit_warning() -> None:
    if not _should_log("errors"):
        return
    prefix = "[dim]\\[AGENT][/dim]"
    _console.print(f"{prefix} [yellow]⚠ Rate limited:[/yellow] Too many calls. Try again later.")


# ─── Dry Run ─────────────────────────────────────────────────────────────────


def format_dry_run(
    prompt: str,
    persona: PersonaDefinition,
    context: Any = None,
) -> None:
    if not _should_log("info"):
        return

    prefix = "[dim]\\[AGENT][/dim]"
    _console.print()
    _console.print(f"{prefix} [magenta]DRY RUN[/magenta] {persona.icon} {persona.label}")
    _console.print(f"{prefix} ├─ [dim]Persona:[/dim] {persona.name}")
    _console.print(f"{prefix} ├─ [dim]Prompt:[/dim] {prompt}")

    if context is not None:
        ctx_str = context if isinstance(context, str) else json.dumps(context, indent=2, default=str)
        lines = ctx_str.split("\n")[:5]
        _console.print(f"{prefix} ├─ [dim]Context:[/dim]")
        for line in lines:
            _console.print(f"{prefix} │  [dim]{line}[/dim]")

    _console.print(f"{prefix} └─ [dim](No API call made)[/dim]")
    _console.print()


# ─── Debug logging ───────────────────────────────────────────────────────────


def log_debug(message: str) -> None:
    if not _should_log("debug"):
        return
    _console.print(f"[dim]\\[AGENT DEBUG][/dim] [dim]{message}[/dim]")
