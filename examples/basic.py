"""
Basic usage of console-agent — as easy as print()

Run with:
    GEMINI_API_KEY=your-key python examples/basic.py
"""

import os

from console_agent import agent, init

# ═══════════════════════════════════════════════════════════════
# Setup — optional (works with GEMINI_API_KEY env var + defaults)
# ═══════════════════════════════════════════════════════════════

init(
    api_key=os.environ.get("GEMINI_API_KEY"),
    model="gemini-2.5-flash-lite",
    mode="blocking",
    log_level="info",
)

# ═══════════════════════════════════════════════════════════════
# 1. Simple prompt
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Test 1: Basic prompt ━━━")
result = agent("What is 2 + 2? Answer concisely.")
print(f"Summary: {result.summary}")
print(f"Success: {result.success}")
print(f"Confidence: {result.confidence}")
print(f"Tokens: {result.metadata.tokens_used}")

# ═══════════════════════════════════════════════════════════════
# 2. With context — pass any data alongside your prompt
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Test 2: Prompt with context ━━━")
result = agent(
    "Analyze these performance metrics",
    context={
        "avg_response_time": "3200ms",
        "p99_response_time": "8500ms",
        "error_rate": 0.02,
        "requests_per_second": 150,
        "database_queries": 12,
        "cache_hit_rate": 0.35,
    },
)
print(f"Summary: {result.summary}")
print(f"Data: {result.data}")

# ═══════════════════════════════════════════════════════════════
# 3. Error debugging — just pass the exception
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Test 3: Debug an error ━━━")
try:
    data = {"users": None}
    names = [u["name"] for u in data["users"]]  # type: ignore
except Exception as e:
    result = agent("Why did this fail?", context=str(e))
    print(f"Summary: {result.summary}")
    print(f"Actions: {result.actions}")

print("\n✅ Basic examples completed!")
