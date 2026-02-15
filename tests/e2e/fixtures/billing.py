"""
Dummy billing module for E2E testing.
This file has an intentional bug: user["plan"] may be None.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class Plan(TypedDict):
    tier: str  # "free" | "pro" | "enterprise"
    seats: int
    price_per_seat: float


class User(TypedDict):
    id: str
    name: str
    email: str
    plan: Optional[Plan]


def calculate_invoice(user: User) -> dict[str, Any]:
    """Calculate invoice for a user.

    BUG: user["plan"] can be None for free users!
    This will raise TypeError when accessing plan["seats"].
    """
    plan = user["plan"]
    # BUG: No null check! plan can be None for free-tier users
    total = plan["seats"] * plan["price_per_seat"]  # type: ignore[index]
    return {
        "user_id": user["id"],
        "amount": total,
        "currency": "USD",
        "tier": plan["tier"],  # type: ignore[index]
    }


# ─── E2E Test Helpers ─────────────────────────────────────────────────────────


async def simulate_billing_error(api_key: str) -> Any:
    """Simulate: error occurs in billing, developer uses agent to debug.

    The agent should see this file's source code automatically.
    """
    from console_agent.core import execute_agent, update_config
    from console_agent.types import AgentCallOptions

    update_config(
        api_key=api_key,
        model="gemini-2.5-flash-lite",
        mode="blocking",
        log_level="info",
        verbose=True,
        anonymize=False,
        timeout=25000,
        include_caller_source=True,
    )

    free_user: User = {
        "id": "usr_123",
        "name": "John Doe",
        "email": "john@example.com",
        "plan": None,  # intentionally None!
    }

    try:
        calculate_invoice(free_user)
    except Exception as error:
        # This is the key test: pass the error, and the agent should
        # auto-detect this billing.py file and include it as context
        result = await execute_agent(
            "Analyze this billing error and recommend a fix",
            error,
            AgentCallOptions(persona="debugger"),
        )
        return result

    return None


async def simulate_caller_detection(api_key: str) -> Any:
    """Simulate: developer calls agent from this file without an error.

    The agent should auto-detect the caller file (this billing.py).
    """
    from console_agent.core import execute_agent, update_config

    update_config(
        api_key=api_key,
        model="gemini-2.5-flash-lite",
        mode="blocking",
        log_level="info",
        verbose=True,
        anonymize=False,
        timeout=25000,
        include_caller_source=True,
    )

    # Call from this file — agent should detect billing.py as the caller
    result = await execute_agent(
        "Review this billing module for potential bugs and improvements",
    )
    return result


async def simulate_without_caller_source(api_key: str) -> Any:
    """Simulate: include_caller_source disabled — no source file should be sent."""
    from console_agent.core import execute_agent, update_config

    update_config(
        api_key=api_key,
        model="gemini-2.5-flash-lite",
        mode="blocking",
        log_level="info",
        verbose=True,
        anonymize=False,
        timeout=25000,
        include_caller_source=False,
    )

    result = await execute_agent("What is 2 + 2? Answer concisely.")
    return result
