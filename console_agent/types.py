"""
Type definitions for console-agent.
All TypeScript interfaces are ported to Pydantic models.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ─── Core Result Type ────────────────────────────────────────────────────────


class ToolCall(BaseModel):
    """Record of a tool invocation during agent execution."""

    name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None


class AgentMetadata(BaseModel):
    """Execution metadata attached to every AgentResult."""

    model: str
    tokens_used: int = 0
    latency_ms: int = 0
    tool_calls: List[ToolCall] = Field(default_factory=list)
    cached: bool = False


class AgentResult(BaseModel):
    """Structured result returned by every agent call."""

    success: bool
    summary: str
    reasoning: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    actions: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    metadata: AgentMetadata = Field(default_factory=lambda: AgentMetadata(model=""))


# ─── Structured output schema (what we ask the LLM to return) ────────────────


class AgentOutputSchema(BaseModel):
    """Pydantic model used as Agno response_model for structured output."""

    success: bool = Field(description="Whether the task was completed successfully")
    summary: str = Field(description="One-line human-readable conclusion")
    reasoning: Optional[str] = Field(
        default=None, description="Your thought process"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured findings as key-value pairs",
    )
    actions: List[str] = Field(
        default_factory=list,
        description="List of tools/steps you used",
    )
    confidence: float = Field(
        ge=0, le=1, description="0-1 confidence score"
    )


# ─── Persona Types ───────────────────────────────────────────────────────────

PersonaName = Literal["debugger", "security", "architect", "general"]

ToolName = Literal["code_execution", "google_search", "url_context", "file_analysis"]


class PersonaDefinition(BaseModel):
    """Definition of an agent persona with system prompt and tool config."""

    name: PersonaName
    system_prompt: str
    icon: str
    label: str
    default_tools: List[ToolName] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


# ─── Tool Types ──────────────────────────────────────────────────────────────


class GoogleSearchConfig(BaseModel):
    mode: Optional[str] = None
    dynamic_threshold: Optional[float] = None


class ToolConfig(BaseModel):
    type: ToolName
    config: Optional[GoogleSearchConfig] = None


# ─── Thinking Config ─────────────────────────────────────────────────────────


class ThinkingConfig(BaseModel):
    """Configuration for model reasoning/thinking."""

    level: Optional[Literal["minimal", "low", "medium", "high"]] = None
    budget: Optional[int] = None
    include_thoughts: bool = False


# ─── Safety Settings ─────────────────────────────────────────────────────────


class HarmCategory(str, Enum):
    HATE_SPEECH = "HARM_CATEGORY_HATE_SPEECH"
    DANGEROUS_CONTENT = "HARM_CATEGORY_DANGEROUS_CONTENT"
    HARASSMENT = "HARM_CATEGORY_HARASSMENT"
    SEXUALLY_EXPLICIT = "HARM_CATEGORY_SEXUALLY_EXPLICIT"


class HarmBlockThreshold(str, Enum):
    BLOCK_NONE = "BLOCK_NONE"
    BLOCK_ONLY_HIGH = "BLOCK_ONLY_HIGH"
    BLOCK_MEDIUM_AND_ABOVE = "BLOCK_MEDIUM_AND_ABOVE"
    BLOCK_LOW_AND_ABOVE = "BLOCK_LOW_AND_ABOVE"


class SafetySetting(BaseModel):
    category: HarmCategory
    threshold: HarmBlockThreshold


# ─── Budget Config ───────────────────────────────────────────────────────────


class BudgetConfig(BaseModel):
    """Budget controls to prevent cost explosion."""

    max_calls_per_day: int = 100
    max_tokens_per_call: int = 8000
    cost_cap_daily: float = 1.0


# ─── Response Format ─────────────────────────────────────────────────────────


class ResponseFormat(BaseModel):
    """Plain JSON Schema for structured output (no Pydantic model needed)."""

    type: Literal["json_object"] = "json_object"
    schema_: Dict[str, Any] = Field(alias="schema")


# ─── Call Options ─────────────────────────────────────────────────────────────

LogLevel = Literal["silent", "errors", "info", "debug"]


class FileAttachment(BaseModel):
    """A file to attach to an agent call (PDF, image, etc.).

    Uses Agno's native File class under the hood for multipart uploads.
    """

    filepath: str  # Path to the file on disk
    media_type: Optional[str] = None  # Optional MIME type override


class AgentCallOptions(BaseModel):
    """Per-call overrides passed to agent()."""

    model: Optional[str] = None
    tools: Optional[List[Union[ToolName, ToolConfig]]] = None
    thinking: Optional[ThinkingConfig] = None
    persona: Optional[PersonaName] = None
    mode: Optional[Literal["fire-and-forget", "blocking"]] = None
    schema_model: Optional[Any] = None  # Pydantic model class for typed output
    response_format: Optional[ResponseFormat] = None
    verbose: Optional[bool] = None
    include_caller_source: Optional[bool] = None  # Override for this call
    files: Optional[List[FileAttachment]] = None  # Explicit file attachments

    model_config = {"arbitrary_types_allowed": True}


# ─── Global Config ────────────────────────────────────────────────────────────


class AgentConfig(BaseModel):
    """Global configuration for console-agent."""

    provider: Literal["google"] = "google"
    api_key: Optional[str] = None
    model: str = "gemini-2.5-flash-lite"
    persona: PersonaName = "general"
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    mode: Literal["fire-and-forget", "blocking"] = "fire-and-forget"
    timeout: int = 10000  # milliseconds
    anonymize: bool = True
    local_only: bool = False
    dry_run: bool = False
    log_level: LogLevel = "info"
    verbose: bool = False
    include_caller_source: bool = True
    safety_settings: List[SafetySetting] = Field(default_factory=list)
