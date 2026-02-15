# System Patterns

## Architecture Overview
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
    Auto-detect caller source file (traceback → read file → add to context)
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
  Parse structured output (AgentResult via Pydantic response_model)
  ↓
  Log results to console with Rich (colors/icons/tree)
  ↓
  Return AgentResult
```

## Key Design Patterns

### Callable Class Singleton
```python
class _AgentCallable:
    def __call__(self, prompt, context=None, **kwargs) -> AgentResult:
        ...
    async def arun(self, prompt, context=None, **kwargs) -> AgentResult:
        ...
    def security(self, prompt, context=None, **kwargs) -> AgentResult:
        return self(prompt, context, persona="security", **kwargs)
    def debug(self, prompt, context=None, **kwargs) -> AgentResult:
        return self(prompt, context, persona="debugger", **kwargs)
    def architect(self, prompt, context=None, **kwargs) -> AgentResult:
        return self(prompt, context, persona="architect", **kwargs)

agent = _AgentCallable()  # Module-level singleton
```

### Module-Level Config Singleton
```python
_config: AgentConfig = deepcopy(DEFAULT_CONFIG)

def update_config(**kwargs):
    global _config, _rate_limiter, _budget_tracker
    merged = _config.model_dump()
    merged.update(kwargs)
    _config = AgentConfig(**merged)
    _rate_limiter = RateLimiter(_config.budget.max_calls_per_day)
    _budget_tracker = BudgetTracker(_config.budget)
```

### Agno Agent Pattern
```python
from agno.agent import Agent
from agno.models.google import Gemini

agent = Agent(
    model=Gemini(id=model_name, api_key=api_key),
    instructions=[persona.system_prompt],
    response_model=AgentOutputSchema,  # Pydantic model for structured output
    tools=resolved_tools,              # Native Gemini tools
)
result = agent.run(full_prompt)
```

### Async from Sync Context
```python
def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        # Jupyter/async context: run in background thread
        result = [None]
        def _run():
            result[0] = asyncio.run(coro)
        thread = threading.Thread(target=_run)
        thread.start()
        thread.join()
        return result[0]
    else:
        return asyncio.run(coro)
```

### Caller Source File Detection
```python
def get_caller_file() -> Optional[SourceFileInfo]:
    # Walk stack frames, skip internal frames (site-packages, agno, asyncio, etc.)
    for frame_info in inspect.stack():
        filename = frame_info.filename
        if not _is_internal_frame(filename) and _is_source_file(filename):
            return SourceFileInfo(file_path=filename, line=frame_info.lineno, ...)

def get_error_source_file(error: BaseException) -> Optional[SourceFileInfo]:
    # Parse traceback, find first non-internal frame
    tb = traceback.extract_tb(error.__traceback__)
    for frame in reversed(tb):
        if not _is_internal_frame(frame.filename):
            return SourceFileInfo(file_path=frame.filename, line=frame.lineno, ...)
```

### Persona Auto-Detection
Keywords in prompt trigger persona overrides:
- "security", "vuln", "exploit", "injection", "xss", "csrf", "owasp", "audit" → security
- "slow", "perf", "optimize", "debug", "error", "crash", "memory", "leak" → debugger
- "design", "architecture", "pattern", "schema", "scalab", "microservice" → architect
- Priority: security > debugger > architect > general (fallback)

### Content Anonymization Pipeline (regex-based)
| Pattern | Replacement |
|---------|-------------|
| Email addresses | `[EMAIL]` |
| IPv4 addresses | `[IP]` |
| Bearer tokens | `Bearer [REDACTED_TOKEN]` |
| AWS keys (AKIA...) | `[REDACTED_AWS_KEY]` |
| PEM private keys | `[REDACTED_PRIVATE_KEY]` |
| Connection strings | `[REDACTED_CONNECTION_STRING]` |
| ENV variables (KEY=val) | `KEY=[REDACTED]` |

### Token Bucket Rate Limiting
- Bucket fills at steady rate (calls per day / 86400 per second)
- Each call consumes one token
- Returns error AgentResult when bucket is empty

### Budget Tracking
- Track daily call count, token usage, estimated cost
- Hard caps: max_calls_per_day, max_tokens_per_call, cost_cap_daily
- Returns error AgentResult when budget exceeded
