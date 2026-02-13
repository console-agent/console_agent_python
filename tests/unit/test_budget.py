"""Tests for the budget tracker."""

from console_agent.types import BudgetConfig
from console_agent.utils.budget import BudgetTracker


class TestBudgetTracker:
    def test_allows_calls_within_budget(self):
        config = BudgetConfig(max_calls_per_day=10, max_tokens_per_call=8000, cost_cap_daily=1.0)
        tracker = BudgetTracker(config)
        result = tracker.can_make_call()
        assert result.allowed is True
        assert result.reason is None

    def test_blocks_when_calls_exhausted(self):
        config = BudgetConfig(max_calls_per_day=2, max_tokens_per_call=8000, cost_cap_daily=1.0)
        tracker = BudgetTracker(config)
        tracker.record_usage(100, 0.01)
        tracker.record_usage(100, 0.01)
        result = tracker.can_make_call()
        assert result.allowed is False
        assert "call limit" in result.reason.lower()

    def test_blocks_when_cost_exceeded(self):
        config = BudgetConfig(max_calls_per_day=100, max_tokens_per_call=8000, cost_cap_daily=0.05)
        tracker = BudgetTracker(config)
        tracker.record_usage(1000, 0.05)
        result = tracker.can_make_call()
        assert result.allowed is False
        assert "cost cap" in result.reason.lower()

    def test_get_stats(self):
        config = BudgetConfig(max_calls_per_day=10, max_tokens_per_call=8000, cost_cap_daily=1.0)
        tracker = BudgetTracker(config)
        tracker.record_usage(500, 0.02)
        stats = tracker.get_stats()
        assert stats.calls_today == 1
        assert stats.calls_remaining == 9
        assert stats.tokens_today == 500
        assert stats.cost_today == 0.02

    def test_reset(self):
        config = BudgetConfig(max_calls_per_day=2, max_tokens_per_call=8000, cost_cap_daily=1.0)
        tracker = BudgetTracker(config)
        tracker.record_usage(100, 0.01)
        tracker.record_usage(100, 0.01)
        assert tracker.can_make_call().allowed is False
        tracker.reset()
        assert tracker.can_make_call().allowed is True

    def test_max_tokens_per_call(self):
        config = BudgetConfig(max_calls_per_day=10, max_tokens_per_call=4096, cost_cap_daily=1.0)
        tracker = BudgetTracker(config)
        assert tracker.max_tokens_per_call == 4096
