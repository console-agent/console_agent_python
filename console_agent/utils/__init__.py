"""Utility modules for console-agent."""

from .anonymize import anonymize, anonymize_value
from .budget import BudgetTracker
from .format import (
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
from .rate_limit import RateLimiter

__all__ = [
    "anonymize",
    "anonymize_value",
    "BudgetTracker",
    "RateLimiter",
    "set_log_level",
    "start_spinner",
    "stop_spinner",
    "format_result",
    "format_error",
    "format_budget_warning",
    "format_rate_limit_warning",
    "format_dry_run",
    "log_debug",
]
