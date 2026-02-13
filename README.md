# console-agent 🐍

> **`agent("debug this")` — as easy as `print()`**

Drop `agent()` anywhere in your Python code to execute agentic AI workflows. Powered by Google Gemini via [Agno](https://github.com/agno-agi/agno).

[![PyPI](https://img.shields.io/pypi/v/console-agent)](https://pypi.org/project/console-agent/)
[![Python](https://img.shields.io/pypi/pyversions/console-agent)](https://pypi.org/project/console-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ⚡ Quick Start

```bash
pip install console-agent
```

```python
from console_agent import agent, init

# Optional: configure (works with sensible defaults + GEMINI_API_KEY env var)
init(api_key="your-key", model="gemini-2.5-flash-lite")

# Fire-and-forget — just like print()
agent("analyze this error", context=error)

# Get structured results
result = agent("validate email format", context=email, mode="blocking")
print(result.summary)
print(result.confidence)
```

## 🎭 Persona Shortcuts

Each persona has a specialized system prompt optimized for its domain:

```python
# 🛡️ Security audit
agent.security("audit this SQL query", context=query)

# 🐛 Debug analysis
agent.debug("investigate slow query", context={"duration": dur, "sql": sql})

# 🏗️ Architecture review
agent.architect("review API design", context=endpoint)
```

Personas are auto-detected from prompt keywords, or you can force one:

```python
agent("analyze this code", persona="security")
```

## 🔄 Async Support

```python
# Native async
result = await agent.arun("analyze this", context=data)

# Works in Jupyter notebooks too!
```

## ⚙️ Configuration

```python
from console_agent import init

init(
    api_key="...",                    # or set GEMINI_API_KEY env var
    model="gemini-2.5-flash-lite",   # default model
    persona="general",               # default persona
    mode="fire-and-forget",          # or "blocking"
    timeout=10000,                   # ms before timeout
    anonymize=True,                  # auto-strip secrets/PII
    dry_run=False,                   # log without calling API
    log_level="info",                # silent | errors | info | debug
    budget={
        "max_calls_per_day": 100,
        "max_tokens_per_call": 8000,
        "cost_cap_daily": 1.0,
    },
)
```

## 📊 Structured Output

Get typed responses using Pydantic models:

```python
from pydantic import BaseModel

class CodeReview(BaseModel):
    issues: list[str]
    severity: str
    suggestion: str

result = agent(
    "review this function",
    context=code,
    schema_model=CodeReview,
)
# result.data is a dict matching CodeReview fields
```

## 🔒 Built-in Safety

- **PII/Secret anonymization** — auto-strips API keys, emails, IPs, tokens before sending
- **Rate limiting** — token bucket algorithm prevents abuse
- **Budget tracking** — daily call limits, token caps, and cost caps
- **Dry run mode** — log prompts without making API calls

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/unit/ -v

# Run integration tests (dry run, no API key needed)
pytest tests/integration/ -v

# Run e2e tests (requires GEMINI_API_KEY)
GEMINI_API_KEY=your-key pytest tests/e2e/ -v
```

## 📦 Architecture

```
console_agent/
├── __init__.py          # Public API: agent(), init()
├── types.py             # Pydantic models (AgentResult, AgentConfig, etc.)
├── core.py              # Agent engine (orchestration, budget, rate-limit)
├── personas/            # Specialized AI personas
│   ├── general.py       # 🔍 General-purpose
│   ├── debugger.py      # 🐛 Error analysis
│   ├── security.py      # �️ Security audit
│   └── architect.py     # 🏗️ Architecture review
├── providers/
│   └── google.py        # Agno + Gemini integration
├── utils/
│   ├── anonymize.py     # PII/secret stripping
│   ├── rate_limit.py    # Token bucket rate limiter
│   ├── budget.py        # Daily budget tracker
│   └── format.py        # Rich console output
└── tools/
    ├── code_execution.py
    ├── search.py
    └── file_analysis.py
```

## 🔗 Also Available

- **Node.js:** [`@console-agent/agent`](https://www.npmjs.com/package/@console-agent/agent)
- **Docs:** [console-agent.github.io](https://console-agent.github.io)
- **GitHub:** [github.com/console-agent](https://github.com/console-agent)

## License

MIT © [Console Agent](https://console-agent.github.io)
