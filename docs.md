# console-agent (Python) — Documentation

## Table of Contents
- [Getting Started](#getting-started)
- [How It Works](#how-it-works)
- [API Reference](#api-reference)
- [Providers](#providers)
- [Personas](#personas)
- [Tools](#tools)
- [Configuration](#configuration)
- [Budget & Rate Limiting](#budget--rate-limiting)
- [Caller Source Detection](#caller-source-detection)
- [File Attachments](#file-attachments)
- [Privacy & Anonymization](#privacy--anonymization)
- [Thinking Mode](#thinking-mode)
- [Console Output](#console-output)
- [Testing](#testing)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

```bash
pip install console-agent
```

### Set your API key

```bash
# Option 1: .env file
echo "GEMINI_API_KEY=your-key-here" >> .env

# Option 2: Environment variable
export GEMINI_API_KEY=your-key-here
```

Get a free API key at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Quick Start (Zero Config)

```python
from console_agent import agent

# Fire-and-forget (default) — logs results, never blocks your app
agent("analyze this error", context=error)

# Get structured results
result = agent("validate this data", context=records, mode="blocking")
print(result.success, result.summary, result.data)
```

### Quick Start (With Config)

```python
import os
from console_agent import agent, init

init(
    api_key=os.environ["GEMINI_API_KEY"],
    model="gemini-2.5-flash-lite",
    mode="blocking",
    log_level="info",
)

# Now use agent() anywhere
result = agent("check for vulnerabilities", context=code)
```

---

## How It Works

```
agent("prompt", context=..., **options)
         ↓
    Parse arguments (prompt string, context, keyword options)
         ↓
    Select persona (auto-detect from keywords, or explicit)
         ↓
    Anonymize content (strip secrets, PII if enabled)
         ↓
    Check rate limits & budget
         ↓
    Format prompt with persona system prompt + context
         ↓
  ┌──────────────────┬──────────────────┐
  │ Fire-and-forget  │  Blocking mode   │
  │ (default)        │  (mode=...)      │
  ↓                  ↓                  │
  Log spinner        Return result ─────┘
  ↓                  ↓
  Send to Gemini via Agno Agent
  ↓
  Agent reasons + optionally uses tools (search, code exec)
  ↓
  Parse structured output (AgentResult)
  ↓
  Log results to console with colors/icons
  ↓
  Return AgentResult
```

---

## API Reference

### `init(**kwargs)`

Configure the agent. Call once at app startup. Optional — sensible defaults work.

```python
import os
from console_agent import init

init(
    api_key=os.environ.get("GEMINI_API_KEY"),
    model="gemini-2.5-flash-lite",       # Default model
    persona="general",                    # Default persona
    mode="fire-and-forget",               # "fire-and-forget" | "blocking"
    timeout=10000,                        # ms
    anonymize=True,                       # Strip secrets/PII
    local_only=False,                     # Disable cloud tools
    dry_run=False,                        # Log without API call
    log_level="info",                     # "silent" | "errors" | "info" | "debug"
    verbose=False,                        # Show full [AGENT] tree output
    include_caller_source=True,           # Auto-read caller source file
    budget={
        "max_calls_per_day": 100,
        "max_tokens_per_call": 8000,
        "cost_cap_daily": 1.00,
    },
)
```

### `agent(prompt, context=None, **options)`

The main API. Call it like `print()`.

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `prompt` | `str` | What you want the agent to do |
| `context` | `Any` (optional) | Data for the agent to analyze |
| `model` | `str` (optional) | Override model for this call |
| `tools` | `list` (optional) | Native Gemini tools to enable |
| `persona` | `PersonaName` (optional) | Force persona for this call |
| `mode` | `str` (optional) | Override execution mode |
| `thinking` | `dict` (optional) | Thinking/reasoning config |
| `schema_model` | `BaseModel` (optional) | Pydantic model for typed output |
| `response_format` | `dict` (optional) | Plain JSON Schema for output |
| `verbose` | `bool` (optional) | Override verbose output |

**Returns:** `AgentResult`

```python
# Simple
agent("explain this error", context=error)

# With context dict
agent("optimize this query", context={"sql": query, "duration": "3.2s"})

# With per-call options
result = agent(
    "analyze", context=data,
    persona="security",
    model="gemini-3-flash-preview",
    tools=["google_search"],
    thinking={"level": "high", "include_thoughts": True},
)
```

### `agent.arun(prompt, context=None, **options)`

Async version — same parameters, returns an awaitable.

```python
import asyncio

async def main():
    result = await agent.arun("analyze this", context=data)
    print(result.summary)

asyncio.run(main())
```

### `agent.security(prompt, context=None, **options)`

Shortcut that forces the **security** persona.

```python
agent.security("check for SQL injection", context=user_input)
# Equivalent to: agent("check for SQL injection", context=user_input, persona="security")
```

### `agent.debug(prompt, context=None, **options)`

Shortcut that forces the **debugger** persona.

```python
agent.debug("why is this slow?", context={"duration": dur, "query": sql})
```

### `agent.architect(prompt, context=None, **options)`

Shortcut that forces the **architect** persona.

```python
agent.architect("review this API design", context={"endpoint": endpoint})
```

---

## AgentResult

Every `agent()` call returns an `AgentResult` (Pydantic model):

```python
class AgentResult(BaseModel):
    success: bool              # Did the agent complete the task?
    summary: str               # One-line human-readable conclusion
    reasoning: Optional[str]   # Agent's thought process (if thinking enabled)
    data: dict[str, Any]       # Structured findings (key-value pairs)
    actions: list[str]         # Steps/tools the agent used
    confidence: float          # 0-1 confidence score
    metadata: AgentMetadata    # model, tokens, latency, etc.

class AgentMetadata(BaseModel):
    model: str                 # Model used (e.g., "gemini-2.5-flash-lite")
    tokens_used: int           # Total tokens consumed
    latency_ms: int            # Wall clock time
    tool_calls: list[ToolCall] # Detailed tool call info
    cached: bool               # Whether response used cache
```

**Using results in your app:**

```python
result = agent("validate this email", context=email)

if not result.success:
    raise ValueError(result.summary)

if result.confidence < 0.8:
    print(f"Low confidence: {result.summary}")

# Use structured data
risk = result.data.get("risk")
recommendation = result.data.get("recommendation")
```

---

## Providers

console-agent supports multiple AI providers. Choose based on your needs:

### Google Gemini (default)

Cloud-hosted models with full tool support. Requires a free API key.

```python
from console_agent import init

init(
    provider="google",                    # default
    api_key="...",                        # or set GEMINI_API_KEY env var
    model="gemini-2.5-flash-lite",       # default model
)
```

**Setup:**
1. Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Set `GEMINI_API_KEY` env var or pass `api_key` to `init()`

**Supports:** ✅ Tools (google_search, code_execution, url_context) · ✅ Thinking mode · ✅ File attachments · ✅ Structured output

### Ollama (Local Models)

Run models locally with [Ollama](https://ollama.com). Free, 100% private, no API key needed.

```bash
# 1. Install Ollama: https://ollama.com
# 2. Pull a model
ollama pull llama3.2
```

```python
from console_agent import init

init(
    provider="ollama",
    model="llama3.2",                         # any model from `ollama list`
    ollama_host="http://localhost:11434",      # default Ollama host
)
```

**Setup:**
1. Install Ollama from [ollama.com](https://ollama.com)
2. Pull a model: `ollama pull llama3.2`
3. That's it — no API key needed

**Supports:** ✅ All personas · ✅ Structured output · ⚠️ Text-only file attachments

**Not supported:** ❌ Tools (google_search, code_execution, url_context) · ❌ Thinking mode

The Ollama provider auto-defaults to `llama3.2` if the configured model is a Gemini model name. You can use any model available in your Ollama installation (`ollama list`).

The host can also be set via the `OLLAMA_HOST` environment variable.

### Provider Comparison

| | Google Gemini | Ollama |
|---|---|---|
| Setup | `GEMINI_API_KEY` env var | Install Ollama + pull model |
| Config | `provider="google"` | `provider="ollama"` |
| Models | `gemini-2.5-flash-lite`, etc. | `llama3.2`, any `ollama list` model |
| Tools | ✅ google_search, code_execution, url_context | ❌ Not supported |
| Thinking | ✅ Supported | ❌ Not supported |
| File attachments | ✅ Full support (PDF, images, video) | ⚠️ Text-only |
| Cost | Pay per token (very cheap) | Free (local) |
| Privacy | Cloud (with anonymization) | 100% local |
| Speed | ~200ms (flash-lite) | Depends on hardware |

---

## Personas

### Available Personas

| Persona | Icon | System Role | Default Tools |
|---------|------|-------------|---------------|
| `general` | 🔍 | Senior full-stack engineer | code_execution, google_search |
| `security` | 🛡️ | OWASP security expert | google_search |
| `debugger` | 🐛 | Senior debugging expert | code_execution, google_search |
| `architect` | 🏗️ | Principal engineer | google_search |

### Auto-Detection

Personas auto-detect from keywords in your prompt:

| Keywords | Persona |
|----------|---------|
| security, vuln, exploit, injection, xss, csrf, owasp, audit | `security` |
| slow, perf, optimize, debug, error, crash, memory, leak, fix, trace | `debugger` |
| design, architecture, pattern, schema, scalab, microservice, system | `architect` |
| (no match) | Falls back to configured default |

**Priority:** security > debugger > architect > general

```python
# Auto-detects "security" persona
agent("check for SQL injection vulnerabilities", context=user_input)

# Auto-detects "debugger" persona
agent("why is this slow?", context=metrics)

# Force a specific persona
agent("analyze this", context=data, persona="architect")
```

---

## Tools

### Built-in Google Tools

These are Google's server-side tools — no local code execution:

#### `code_execution`
Generates and runs Python code in Google's sandbox.

**Use for:** Math, algorithms, data transformations, calculations.

```python
agent(
    "calculate the optimal batch size given these constraints",
    context={"total_items": 1000000, "memory_limit": "4GB", "cpu_cores": 8},
    tools=["code_execution"],
)
```

#### `google_search`
Searches the web with source attribution.

**Use for:** Security research, fact-checking, library vulnerabilities, current info.

```python
agent.security(
    "check if requests==2.28.0 has known vulnerabilities",
    tools=["google_search"],
)
```

#### `url_context`
Fetch and analyze web pages.

**Use for:** Reading documentation, analyzing APIs, extracting page content.

```python
agent(
    "summarize this page",
    tools=["url_context"],
)
```

#### `file_analysis`
Process files (PDF, images, video).

**Use for:** Document analysis, OCR, image understanding.

### Disabling Tools

```python
# No tools at all
agent("just analyze this text", context=data, tools=[])

# Enterprise mode — disable all cloud tools globally
init(local_only=True)
```

---

## Configuration

### Full Config Reference

```python
class AgentConfig(BaseModel):
    provider: Literal["google", "ollama"] = "google"
    api_key: Optional[str] = None          # Or use GEMINI_API_KEY env
    model: str = "gemini-2.5-flash-lite"
    ollama_host: str = "http://localhost:11434"  # Ollama host (or OLLAMA_HOST env)
    persona: PersonaName = "general"
    mode: Literal["fire-and-forget", "blocking"] = "fire-and-forget"
    timeout: int = 10000                   # ms
    budget: BudgetConfig                   # See below
    anonymize: bool = True                 # Strip PII/secrets
    local_only: bool = False               # Disable cloud tools
    dry_run: bool = False                  # Log without API calls
    log_level: LogLevel = "info"           # "silent"|"errors"|"info"|"debug"
    verbose: bool = False                  # Full [AGENT] tree output
    include_caller_source: bool = True     # Auto-read source files
    safety_settings: list[SafetySetting] = []
```

### Defaults

```python
AgentConfig(
    provider="google",
    model="gemini-2.5-flash-lite",
    persona="general",
    mode="fire-and-forget",
    timeout=10000,
    anonymize=True,
    local_only=False,
    dry_run=False,
    log_level="info",
    verbose=False,
    include_caller_source=True,
    budget=BudgetConfig(
        max_calls_per_day=100,
        max_tokens_per_call=8000,
        cost_cap_daily=1.00,
    ),
)
```

### Per-Call Options

Override config for a single call:

```python
class AgentCallOptions(BaseModel):
    model: Optional[str] = None
    tools: Optional[list[ToolName | ToolConfig]] = None
    thinking: Optional[ThinkingConfig] = None
    persona: Optional[PersonaName] = None
    mode: Optional[Literal["fire-and-forget", "blocking"]] = None
    schema_model: Optional[Any] = None          # Pydantic model class
    response_format: Optional[ResponseFormat] = None
    verbose: Optional[bool] = None
    include_caller_source: Optional[bool] = None
    files: Optional[list[FileAttachment]] = None
```

---

## Budget & Rate Limiting

### How It Works

- **max_calls_per_day**: Hard limit on API calls per 24h period
- **max_tokens_per_call**: Caps output tokens per call
- **cost_cap_daily**: Estimated daily cost cap in USD

When limits are hit, `agent()` returns an error result immediately (no API call):

```python
AgentResult(
    success=False,
    summary="Rate limited — too many calls. Try again later.",
    data={},
    actions=[],
    confidence=0,
    metadata=AgentMetadata(tokens_used=0, latency_ms=0, ...),
)
```

### Configuration

```python
init(
    budget={
        "max_calls_per_day": 100,      # 100 calls per day
        "max_tokens_per_call": 8000,   # 8K tokens max per call
        "cost_cap_daily": 1.00,        # $1/day max
    },
)
```

### Cost Estimation

| Model | Input Cost | Output Cost |
|-------|-----------|-------------|
| gemini-2.5-flash-lite | ~$0.01/1M tokens | ~$0.04/1M tokens |
| gemini-3-flash-preview | ~$0.03/1M tokens | ~$0.12/1M tokens |

At the default budget (100 calls/day, 8K tokens/call):
- **Estimated max daily cost:** ~$0.03 with flash-lite

---

## Caller Source Detection

When debugging, the agent **automatically reads the source file** where `agent()` was called (or where an Exception originated) and sends it as context to the AI model. This gives the agent full visibility into your code without you having to copy-paste anything.

### How It Works

1. **Error path**: When you pass an `Exception` as context, the agent parses the traceback to find the originating file, reads it, and sends the source code with line numbers (arrow marking the error line).
2. **Caller path**: Even without an error, the agent detects which file called `agent()` and includes that file's source.

### Example — Automatic Error Source Detection

```python
# billing.py
def calculate_invoice(user):
    total = user.plan.seats * user.plan.price_per_seat  # BUG: plan can be None!
    return {"user_id": user.id, "amount": total}

try:
    calculate_invoice(free_user)
except Exception as error:
    # Agent auto-reads billing.py from the traceback
    # and sends the full file with line numbers to Gemini
    agent.debug("analyze this billing error", context=error)
```

The agent sees:
```
--- Source File: billing.py (line 3) ---
      1 | def calculate_invoice(user):
      2 |     # BUG: plan can be None!
 →    3 |     total = user.plan.seats * user.plan.price_per_seat
      4 |     return {"user_id": user.id, "amount": total}
```

### Configuration

```python
# Enabled by default
init(include_caller_source=True)

# Disable globally
init(include_caller_source=False)

# Disable per-call
agent("analyze", context=data, include_caller_source=False)
```

### Limits

- Files larger than **100KB** are truncated to prevent excessive token usage
- Only `.py` source files are read
- Internal frames (site-packages, standard library) are skipped automatically

---

## File Attachments

You can explicitly attach files (PDFs, images, etc.) to any agent call using the `files` option:

```python
from console_agent import agent
from console_agent.types import FileAttachment

# Attach a PDF document
result = agent(
    "What is an embedding model according to this document?",
    files=[
        FileAttachment(filepath="./data/ai.pdf", media_type="application/pdf"),
    ],
)

# Attach an image
result = agent(
    "Describe what's in this screenshot",
    files=[
        FileAttachment(filepath="./screenshot.png", media_type="image/png"),
    ],
)

# Multiple files at once
result = agent(
    "Compare these two documents",
    files=[
        FileAttachment(filepath="./doc1.pdf", media_type="application/pdf"),
        FileAttachment(filepath="./doc2.pdf", media_type="application/pdf"),
    ],
)
```

### Supported Media Types

| Type | Media Type |
|------|-----------|
| PDF | `application/pdf` |
| PNG | `image/png` |
| JPEG | `image/jpeg` |
| WebP | `image/webp` |
| GIF | `image/gif` |
| Plain text | `text/plain` |

### FileAttachment Model

```python
class FileAttachment(BaseModel):
    filepath: str                      # Path to the file on disk
    media_type: Optional[str] = None   # Optional MIME type override
```

---

## Privacy & Anonymization

### What Gets Stripped (when `anonymize=True`)

| Pattern | Replacement |
|---------|-------------|
| Email addresses | `[EMAIL]` |
| IPv4 addresses | `[IP]` |
| Bearer tokens | `Bearer [REDACTED_TOKEN]` |
| AWS access keys (AKIA...) | `[REDACTED_AWS_KEY]` |
| Private keys (PEM) | `[REDACTED_PRIVATE_KEY]` |
| Connection strings (postgres://, mongodb://) | `[REDACTED_CONNECTION_STRING]` |
| Environment variables (KEY=value) | `KEY=[REDACTED]` |

### Enterprise Mode

```python
init(
    anonymize=True,     # Strip all PII/secrets
    local_only=True,    # No cloud tools (code execution, search)
)
```

---

## Thinking Mode

### Gemini 2.5 Models (Budget-based)

```python
result = agent(
    "optimize this algorithm", context=code,
    model="gemini-2.5-flash-lite",
    thinking={
        "budget": 8192,               # Token budget for reasoning
        "include_thoughts": True,
    },
)
print(result.reasoning)   # Agent's thought process
```

### Gemini 3 Models (Level-based)

```python
result = agent(
    "design database schema for multi-tenant SaaS",
    context=requirements,
    model="gemini-3-flash-preview",
    thinking={
        "level": "high",              # "minimal" | "low" | "medium" | "high"
        "include_thoughts": True,
    },
)
```

---

## Structured Output

### Option A: Pydantic Model (typed, validated)

```python
from pydantic import BaseModel, Field
from typing import List

class Sentiment(BaseModel):
    sentiment: str = Field(description="positive/negative/neutral")
    score: float
    keywords: List[str]

result = agent(
    "analyze sentiment", context=review,
    schema_model=Sentiment,
)
result.data["sentiment"]  # "positive" ✅ typed
```

### Option B: Plain JSON Schema (no Pydantic needed)

```python
info = agent(
    "extract info", context=text,
    response_format={
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
            },
            "required": ["name", "age"],
        },
    },
)
info.data["name"]  # "John Doe" ✅
```

---

## Console Output

### Default vs Verbose Mode

By default, agent output is compact. Enable verbose mode for full traces:

```python
# Global verbose
init(verbose=True)

# Per-call verbose
agent("analyze this", verbose=True)
```

### Verbose Output

```
[AGENT] - 🛡️ Security audit... check for SQL injection
[AGENT] ✓ 🛡️ Security audit Complete
[AGENT] ├─ ✓ SQL injection vulnerability detected
[AGENT] ├─ Tool: google_search
[AGENT] ├─ risk: HIGH
[AGENT] ├─ fix: Use parameterized queries
[AGENT] └─ confidence: 0.94 | 247ms | 156 tokens
```

### Log Levels

| Level | Shows |
|-------|-------|
| `silent` | Nothing |
| `errors` | Only errors |
| `info` | Spinners, results, summaries |
| `debug` | Everything (model, persona, tools, prompts) |

### Dry Run Mode

Test without API calls:

```python
init(dry_run=True)

agent("test prompt", context=data)
# → [AGENT] DRY RUN 🔍 Analyzing
# → [AGENT] ├─ Persona: general
# → [AGENT] ├─ Prompt: test prompt
# → [AGENT] └─ (No API call made)
```

---

## Testing

### Run Unit Tests (no API key needed)

```bash
pytest tests/unit          # Run unit tests
pytest tests/integration   # Run integration tests (uses dryRun)
```

### Run E2E Tests (requires API key)

```bash
# Set your API key in .env
echo "GEMINI_API_KEY=your-real-key" > .env

# Run E2E tests
pytest tests/e2e
```

E2E tests auto-skip if no valid API key is set.

### Test Structure

```
tests/
├── unit/                  # No API key needed
│   ├── test_personas.py
│   ├── test_anonymize.py
│   ├── test_rate_limit.py
│   ├── test_budget.py
│   ├── test_caller_file.py
│   ├── test_agent_config.py
│   └── test_ollama_provider.py
├── integration/           # No API key needed (uses dry_run)
│   └── test_agent_dryrun.py
└── e2e/                   # Requires API keys / running services
    ├── test_agent_real.py       # Requires GEMINI_API_KEY
    ├── test_caller_source.py    # Requires GEMINI_API_KEY
    └── test_ollama_real.py      # Requires running Ollama server
```

---

## Architecture

### Package Structure

```
console_agent/
├── __init__.py            # Main export, init(), agent singleton
├── core.py                # Core engine (config, execute_agent, dry run)
├── types.py               # All Pydantic models & type definitions
├── providers/
│   ├── google.py          # Agno Agent + Gemini integration
│   └── ollama.py          # Agno Agent + Ollama integration (local models)
├── personas/
│   ├── __init__.py        # Registry, detection, get_persona()
│   ├── debugger.py        # 🐛 Debugging expert
│   ├── security.py        # 🛡️ OWASP expert
│   ├── architect.py       # 🏗️ Principal engineer
│   └── general.py         # 🔍 Full-stack engineer
├── tools/
│   ├── __init__.py        # Tool registry
│   ├── code_execution.py  # Google code execution
│   ├── search.py          # Google search grounding
│   ├── url_context.py     # URL fetching and analysis
│   └── file_analysis.py   # File/image/PDF processing
└── utils/
    ├── format.py          # Console output (Rich + spinners)
    ├── rate_limit.py      # Token bucket algorithm
    ├── budget.py          # Cost/call tracking
    ├── anonymize.py       # PII/secret stripping
    └── caller_file.py     # Source file detection
```

### Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| AI Agent | `Agno Agent` | Lightweight, built-in tool loop, structured output |
| Structured Output | Pydantic `response_model` | Native Python validation, type safety |
| Agent API | Callable class singleton | `agent()` + persona methods (`.security()`, `.debug()`, `.architect()`) |
| Config | Module-level singleton | Simple, no external state, `init()` pattern |
| Console Output | `Rich` library | Beautiful terminal output, spinners, colors |
| Rate Limiting | Token bucket | Simple, reset daily |
| Anonymization | Regex patterns | Fast, no external deps |
| Async Support | `asyncio` + thread fallback | Works in sync code, async code, and Jupyter |

### Dependencies

- `agno` — Agent framework (tool loop, structured output)
- `google-genai` — Google Gemini provider
- `ollama` — Ollama Python client (local model support)
- `openai` — Required by Agno's Ollama provider
- `rich` — Console colors, spinners, formatting
- `pydantic` — Type definitions, validation

---

## Troubleshooting

### "GEMINI_API_KEY not set"

Set the API key via environment or `init()`:

```bash
export GEMINI_API_KEY=your-key
```

Or:

```python
init(api_key="your-key")
```

### "Rate limited"

You've hit the daily call limit. Either:
- Wait for the daily reset
- Increase `budget["max_calls_per_day"]` in `init()`

### "Daily cost cap reached"

Increase `budget["cost_cap_daily"]` in `init()`.

### Agent returns `success=False`

The agent encountered an error. Check `result.summary` for details:

```python
result = agent("task", context=data)
if not result.success:
    print(f"Agent error: {result.summary}")
```

### Console output is noisy

```python
init(log_level="errors")   # Only show errors
init(log_level="silent")   # No output at all
```

### Testing without API calls

```python
init(dry_run=True)
# All calls return mock results without hitting the API
```

### Ollama: "Connection refused" / "Cannot connect"

Make sure Ollama is running:

```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

If using a custom host, set it in `init()` or via env var:

```python
init(provider="ollama", ollama_host="http://your-host:11434")
```

Or:

```bash
export OLLAMA_HOST=http://your-host:11434
```

### Ollama: "Model not found"

Pull the model first:

```bash
ollama pull llama3.2
```

Check available models:

```bash
ollama list
```

### Ollama: Tools not working

Tools (google_search, code_execution, url_context) are **not supported** with the Ollama provider. They are Google/Gemini-specific. If you need tools, use `provider="google"`.

---

## Type Exports

Full type support with exported Pydantic models:

```python
from console_agent import (
    AgentResult,
    AgentConfig,
    AgentCallOptions,
    BudgetConfig,
    FileAttachment,
    LogLevel,
    PersonaName,
    ResponseFormat,
    ThinkingConfig,
    ToolCall,
    ToolName,
)
```

---

## Models Reference

### Google Gemini Models

| Model | Best For | Speed | Cost |
|-------|----------|-------|------|
| `gemini-2.5-flash-lite` | General purpose, fast | ~200ms | Very low |
| `gemini-3-flash-preview` | Complex reasoning, thinking mode | ~400ms | Low |

**Default:** `gemini-2.5-flash-lite` — handles 99% of use cases.

### Ollama Models

| Model | Best For | Size |
|-------|----------|------|
| `llama3.2` | General purpose (default for Ollama) | ~2GB |
| `llama3.2:1b` | Lightweight, fast responses | ~1.3GB |
| `mistral` | Strong reasoning | ~4.1GB |
| `codellama` | Code-focused tasks | ~3.8GB |
| `deepseek-coder` | Code generation & review | ~776MB |

Use any model available via `ollama list`. See [ollama.com/library](https://ollama.com/library) for the full model catalog.

---

## License

MIT © Pavel
