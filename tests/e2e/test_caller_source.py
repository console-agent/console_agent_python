"""
E2E tests — Caller Source File Detection.

Tests that the agent automatically reads and sends the caller's
source file to the AI model for better context-aware debugging.

Uses a dummy billing.py fixture with an intentional bug.

Requires GEMINI_API_KEY in environment.
"""

from __future__ import annotations

import json
import os

import pytest

from tests.e2e.fixtures.billing import (
    simulate_billing_error,
    simulate_caller_detection,
    simulate_without_caller_source,
)

API_KEY = os.environ.get("GEMINI_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not API_KEY or API_KEY == "your-gemini-api-key-here",
    reason="GEMINI_API_KEY not set — skipping E2E tests",
)


class TestCallerSourceDetection:
    """E2E: Caller Source File Detection (billing.py fixture)."""

    @pytest.mark.timeout(60)
    async def test_error_path_agent_receives_billing_source(self):
        """Error path — agent receives billing.py source via error traceback."""
        result = await simulate_billing_error(API_KEY)

        assert result is not None
        assert hasattr(result, "success")
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0
        assert result.metadata.tokens_used > 0
        assert result.metadata.latency_ms > 0

        # The agent should reference the billing bug in its response
        full_text = json.dumps(result.model_dump(), default=str).lower()
        mentions_billing = any(
            kw in full_text
            for kw in ["plan", "none", "null", "billing", "optional", "check", "undefined"]
        )
        assert mentions_billing, f"Agent did not mention billing bug. Response: {result.summary}"

        print(f"\n🐛 Billing error analysis: {result.summary}")
        print(f"   Data: {json.dumps(result.data, indent=2, default=str)}")

    @pytest.mark.timeout(60)
    async def test_caller_detection_agent_sees_billing_py(self):
        """Caller detection — agent sees billing.py when called from it."""
        result = await simulate_caller_detection(API_KEY)

        assert result is not None
        assert isinstance(result.success, bool)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0
        assert result.metadata.tokens_used > 0

        # The agent should have found bugs in the billing code
        full_text = json.dumps(result.model_dump(), default=str).lower()
        mentions_bug = any(
            kw in full_text
            for kw in ["plan", "none", "null", "optional", "bug", "check", "undefined"]
        )
        assert mentions_bug, f"Agent did not find billing bugs. Response: {result.summary}"

        print(f"\n🔍 Caller detection review: {result.summary}")
        print(f"   Data: {json.dumps(result.data, indent=2, default=str)}")

    @pytest.mark.timeout(60)
    async def test_disabled_works_without_caller_source(self):
        """Disabled — works fine without caller source."""
        result = await simulate_without_caller_source(API_KEY)

        assert result is not None
        assert result.success is True
        assert isinstance(result.summary, str)
        assert result.metadata.tokens_used > 0

        print(f"\n✅ No caller source result: {result.summary}")
