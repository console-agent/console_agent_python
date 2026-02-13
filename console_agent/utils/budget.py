"""
Budget tracker — monitors daily token usage and cost.
Enforces hard caps to prevent cost explosion.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional

from ..types import BudgetConfig


@dataclass
class BudgetCheckResult:
    allowed: bool
    reason: Optional[str] = None


@dataclass
class BudgetStats:
    calls_today: int
    calls_remaining: int
    tokens_today: int
    cost_today: float
    cost_remaining: float


class BudgetTracker:
    """Tracks daily API usage against configured budget limits."""

    def __init__(self, config: BudgetConfig) -> None:
        self._config = config
        self._calls_today = 0
        self._tokens_today = 0
        self._cost_today = 0.0
        self._day_start = self._get_start_of_day()

    def can_make_call(self) -> BudgetCheckResult:
        """Check if a call is within budget. Resets counters at midnight UTC."""
        self._maybe_reset_day()

        if self._calls_today >= self._config.max_calls_per_day:
            return BudgetCheckResult(
                allowed=False,
                reason=f"Daily call limit reached ({self._config.max_calls_per_day} calls/day)",
            )

        if self._cost_today >= self._config.cost_cap_daily:
            return BudgetCheckResult(
                allowed=False,
                reason=f"Daily cost cap reached (${self._config.cost_cap_daily:.2f})",
            )

        return BudgetCheckResult(allowed=True)

    def record_usage(self, tokens_used: int, cost_usd: float) -> None:
        """Record a completed call's usage."""
        self._maybe_reset_day()
        self._calls_today += 1
        self._tokens_today += tokens_used
        self._cost_today += cost_usd

    def get_stats(self) -> BudgetStats:
        """Get current usage stats."""
        self._maybe_reset_day()
        return BudgetStats(
            calls_today=self._calls_today,
            calls_remaining=max(0, self._config.max_calls_per_day - self._calls_today),
            tokens_today=self._tokens_today,
            cost_today=self._cost_today,
            cost_remaining=max(0, self._config.cost_cap_daily - self._cost_today),
        )

    def reset(self) -> None:
        """Reset all counters (for testing)."""
        self._calls_today = 0
        self._tokens_today = 0
        self._cost_today = 0.0
        self._day_start = self._get_start_of_day()

    @property
    def max_tokens_per_call(self) -> int:
        return self._config.max_tokens_per_call

    def _maybe_reset_day(self) -> None:
        current_day_start = self._get_start_of_day()
        if current_day_start > self._day_start:
            self._calls_today = 0
            self._tokens_today = 0
            self._cost_today = 0.0
            self._day_start = current_day_start

    @staticmethod
    def _get_start_of_day() -> float:
        now = datetime.datetime.now(datetime.timezone.utc)
        start = datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.timezone.utc)
        return start.timestamp()
