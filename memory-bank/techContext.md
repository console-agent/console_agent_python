# Tech Context

## Tech Stack
- **Language:** Python 3.10+ (type hints, Pydantic v2)
- **AI Framework:** Agno (`agno` >=1.0.0) — lightweight agent framework
- **AI Provider:** Google Gemini via `google-genai` >=1.0.0
- **Structured Output:** Pydantic `response_model` for typed responses
- **Console Output:** Rich library (spinners, colors, formatting)
- **Type System:** Pydantic v2 models for all types (AgentResult, AgentConfig, etc.)
- **Testing:** pytest + pytest-asyncio + pytest-mock
- **CI/CD:** GitHub Actions → PyPI publish with Trusted Publisher (OIDC)

## Package Identity
- **Name:** `console-agent`
- **Version:** 1.2.2
- **License:** MIT
- **Python:** >=3.10

## Key Dependencies
```toml
[project]
dependencies = [
    "agno>=1.0.0",
    "google-genai>=1.0.0",
    "pydantic>=2.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-mock>=3.10",
]
```

## Supported Google Models
| Model | Speed | Use Case | Default |
|-------|-------|----------|---------|
| gemini-2.5-flash-lite | ~200ms | Fast, cheap, general purpose | ✅ Yes |
| gemini-3-flash-preview | ~400ms | Complex reasoning, thinking mode | No |

## Key Features (v1.2.x)
- **Caller source detection**: Auto-reads source file from traceback (skips site-packages, stdlib, agno, asyncio frames); 100KB truncation limit
- **File attachments**: `FileAttachment(filepath, media_type)` using Agno's native File class
- **Verbose/quiet modes**: Rich-based output with spinners, tree formatting, metadata
- **Native Gemini tools**: google_search, code_execution, url_context, file_analysis
- **Structured output**: Pydantic `schema_model` or plain `response_format` (JSON Schema)
- **Thinking mode**: `thinking={"budget": 8192}` (Gemini 2.5) or `thinking={"level": "high"}` (Gemini 3)
- **Async support**: `agent.arun()` + thread fallback for sync contexts / Jupyter

## Package Structure
```
console_agent/
├── __init__.py            # Main export, init(), _AgentCallable singleton
├── core.py                # Core engine (config, execute_agent, dry run)
├── types.py               # All Pydantic models & type definitions
├── providers/
│   └── google.py          # Agno Agent + Gemini integration
├── personas/
│   ├── __init__.py        # Registry, detection, get_persona()
│   ├── debugger.py, security.py, architect.py, general.py
├── tools/
│   ├── __init__.py        # Tool registry
│   ├── code_execution.py, search.py, url_context.py, file_analysis.py
└── utils/
    ├── format.py          # Rich console output (spinners, colors)
    ├── rate_limit.py      # Token bucket algorithm
    ├── budget.py          # Cost/call tracking
    ├── anonymize.py       # PII/secret stripping (regex)
    └── caller_file.py     # Source file detection (traceback parsing)
```

## Build & Publish
- Build: `python -m build` → `dist/console_agent-X.Y.Z-py3-none-any.whl`
- Publish: GitHub Actions with Trusted Publisher (PyPI OIDC, no token needed)
- Provenance: Sigstore transparency log

## Key Differences from TypeScript Version
| Aspect | TypeScript | Python |
|--------|-----------|--------|
| AI Framework | Vercel AI SDK (ToolLoopAgent) | Agno Agent |
| Structured Output | Zod schemas + jsonSchema() | Pydantic response_model |
| Agent Attachment | `console.agent` via Proxy | `agent` callable class singleton |
| Async | Native Promise/await | asyncio + thread fallback |
| Console Output | chalk + ora | Rich library |
| Config | `init({...})` | `init(**kwargs)` |
| Tool Compat | Tools incompatible with JSON output | Agno handles tools natively |
