# Product Context

## Why This Product Exists
Python port of console-agent — bringing the same "jQuery of AI Agents" experience to the Python ecosystem. Developers want agentic AI capabilities embedded directly in their runtime code — for debugging, security auditing, data validation, and decision-making — without framework complexity.

## Problem It Solves
- **Agents are too complicated:** 100+ lines of boilerplate with Langchain/CrewAI
- **Wrong abstraction layer:** Existing tools are for chat apps, not runtime utilities
- **Context switching kills flow:** Switching to external tools breaks development momentum
- **Python developers need parity:** Same API, same features as the TypeScript version

## How It Should Work
`agent(...)` should feel as natural as `print()`. Drop it anywhere in your Python code:
- **Fire-and-forget (default):** Returns immediately, logs results async
- **Blocking mode:** `agent("task", context=data, mode="blocking")` returns `AgentResult`
- **Async support:** `await agent.arun("task", context=data)`
- **Persona shortcuts:** `agent.security()`, `.debug()`, `.architect()`
- **Zero config required:** Works out of the box with sensible defaults + GEMINI_API_KEY env

## Target Users
- Python developers (Django, Flask, FastAPI, data science)
- Full-stack developers using both JS and Python
- Solo founders / indie hackers
- Platform engineers debugging production
- Security-conscious teams needing runtime validation

## Relationship to TypeScript Package
- **Feature parity**: Same personas, tools, budget, anonymization, caller source detection
- **Same API design**: `agent()` = `console.agent()`, `init()` = `init()`
- **Same AI backend**: Google Gemini via Agno Agent framework
- **Same structured output**: `AgentResult` with identical fields
- **Separate package**: `pip install console-agent` (PyPI) vs `npm install @console-agent/agent` (npm)
