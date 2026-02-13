"""
Structured output — get typed, validated responses from the agent.

Use Pydantic models for compile-time type safety, or raw JSON schemas
for looser control. Both guarantee the LLM returns the exact shape you need.

Run with:
    GEMINI_API_KEY=your-key python examples/structured_output.py
"""

import os
from typing import List

from pydantic import BaseModel, Field

from console_agent import agent, init

init(
    api_key=os.environ.get("GEMINI_API_KEY"),
    model="gemini-2.5-flash-lite",
    mode="blocking",
    log_level="info",
)

# ═══════════════════════════════════════════════════════════════
# 1. Pydantic schema — typed, validated structured output
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Pydantic Schema ━━━")


class EmailValidation(BaseModel):
    is_valid: bool = Field(description="Whether the email is valid")
    reason: str = Field(description="Why the email is or is not valid")
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for fixing the email",
    )


result = agent(
    "Validate this email address and explain why it is or is not valid",
    context="not-a-real-email@",
    schema_model=EmailValidation,
)

print(f"Is valid: {result.data['is_valid']}")
print(f"Reason: {result.data['reason']}")
print(f"Suggestions: {result.data['suggestions']}")

# ═══════════════════════════════════════════════════════════════
# 2. Another Pydantic schema — code review
# ═══════════════════════════════════════════════════════════════

print("\n━━━ Code Review Schema ━━━")


class CodeReview(BaseModel):
    quality_score: int = Field(ge=1, le=10, description="Code quality 1-10")
    issues: List[str] = Field(description="List of issues found")
    improvements: List[str] = Field(description="Suggested improvements")
    summary: str = Field(description="One-line summary")


result = agent(
    "Review this Python function for quality and best practices",
    context="""
def get_user(id):
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {id}")
    return cursor.fetchone()
""",
    schema_model=CodeReview,
)

print(f"Quality: {result.data['quality_score']}/10")
print(f"Summary: {result.data['summary']}")
print(f"Issues: {result.data['issues']}")

# ═══════════════════════════════════════════════════════════════
# 3. JSON Schema (response_format) — no Pydantic needed
# ═══════════════════════════════════════════════════════════════

print("\n━━━ JSON Schema (response_format) ━━━")
result = agent(
    "Analyze this code for security issues. "
    "Return severity, issue, and fix.",
    context="x = eval(user_input)",
    response_format={
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "description": "One of: low, medium, high, critical",
                },
                "issue": {
                    "type": "string",
                    "description": "Description of the issue",
                },
                "fix": {
                    "type": "string",
                    "description": "Suggested fix",
                },
            },
            "required": ["severity", "issue", "fix"],
        },
    },
)

print(f"Data: {result.data}")

print("\n✅ Structured output examples completed!")
