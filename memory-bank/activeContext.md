# Active Context

## Current Focus
v1.2.2 published on PyPI. Docs and reference page live at console-agent.github.io.

## Recent Changes (2026-02-15)
- **Version bump to 1.2.2**: Bumped pyproject.toml and pushed
- **Created docs.md**: Comprehensive Python documentation for the reference page (covers full API, personas, tools, config, budget, caller source, file attachments, anonymization, thinking, structured output, testing, architecture)
- **Reference page integration**: docs.md served via GitHub raw URL to console-agent.github.io/reference.html

## Current Phase
Post-v1.2.2 — Package published on PyPI. Full documentation available.

## What's Working
- All unit/integration/e2e tests pass
- PyPI package: `console-agent==1.2.2`
- `agent()` callable with persona shortcuts (`.security()`, `.debug()`, `.architect()`)
- `agent.arun()` for async usage
- Fire-and-forget (default) and blocking modes
- All 4 personas with auto-detection
- Native Gemini tools (google_search, code_execution, url_context, file_analysis)
- Budget controls, rate limiting, anonymization
- Caller source file detection (traceback → read source → add to context)
- File attachments (PDF, images via FileAttachment)
- Verbose/quiet output modes via Rich
- Thinking mode (budget-based for Gemini 2.5, level-based for Gemini 3)
- Structured output (Pydantic schema_model or plain response_format)
- GitHub Actions CI/CD → PyPI publish with provenance

## What's Next
1. Add caching layer for repeated prompts
2. Add streaming support (v2.0)
3. Explore more personas
4. Consider adding more test coverage

## Key Repos
- **Python**: github.com/console-agent/console_agent_python (PyPI: console-agent)
- **JS/TS**: github.com/console-agent/console_agent (npm: @console-agent/agent)
- **Website**: github.com/console-agent/console-agent.github.io
