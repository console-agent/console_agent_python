"""
Async usage — use agent.arun() in async Python code.

Perfect for FastAPI, aiohttp, or any async framework.

Run with:
    GEMINI_API_KEY=your-key python examples/async_usage.py
"""

import asyncio
import os

from console_agent import agent, init

init(
    api_key=os.environ.get("GEMINI_API_KEY"),
    model="gemini-2.5-flash-lite",
    mode="blocking",
    log_level="info",
)


async def main():
    # ═══════════════════════════════════════════════════════════
    # 1. Basic async call
    # ═══════════════════════════════════════════════════════════

    print("\n━━━ Async Basic ━━━")
    result = await agent.arun("What is 3 + 3? Answer concisely.")
    print(f"Summary: {result.summary}")
    print(f"Tokens: {result.metadata.tokens_used}")

    # ═══════════════════════════════════════════════════════════
    # 2. Async with persona override
    # ═══════════════════════════════════════════════════════════

    print("\n━━━ Async with Persona ━━━")
    result = await agent.arun(
        "Is this code safe?",
        context="os.system(user_input)",
        persona="security",
    )
    print(f"Summary: {result.summary}")
    print(f"Confidence: {result.confidence}")

    # ═══════════════════════════════════════════════════════════
    # 3. Concurrent async calls — run multiple agents in parallel
    # ═══════════════════════════════════════════════════════════

    print("\n━━━ Concurrent Async Calls ━━━")
    results = await asyncio.gather(
        agent.arun("What is the capital of France?"),
        agent.arun(
            "Check for SQL injection",
            context="SELECT * FROM users WHERE id = " + "user_input",
            persona="security",
        ),
        agent.arun(
            "Debug this error",
            context="KeyError: 'username'",
            persona="debugger",
        ),
    )

    for i, r in enumerate(results, 1):
        print(f"\n  Result {i}: {r.summary}")

    print("\n✅ Async examples completed!")


# ═══════════════════════════════════════════════════════════════
# FastAPI integration example (not runnable standalone):
#
#   from fastapi import FastAPI
#   from console_agent import agent, init
#
#   app = FastAPI()
#   init(model="gemini-2.5-flash-lite")
#
#   @app.post("/analyze")
#   async def analyze(code: str):
#       result = await agent.arun(
#           "Analyze this code for bugs",
#           context=code,
#           persona="debugger",
#       )
#       return {"summary": result.summary, "data": result.data}
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    asyncio.run(main())
