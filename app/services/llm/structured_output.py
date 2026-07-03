"""Pydantic models for structured LLM outputs."""

from pydantic import BaseModel, Field


class ColumnSemanticDecision(BaseModel):
    """LLM decision for a single column's semantic type and role."""
    column_name: str
    decision: str = Field(description="One of: confirmed, overridden, unresolved")
    confirmed_semantic_type: str | None = None
    confirmed_column_role: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    recommended_mandatory: bool | None = None
    recommended_expected_unique: bool | None = None


class SchemaIntelligenceBatchResponse(BaseModel):
    """LLM batch response for multiple columns."""
    columns: list[ColumnSemanticDecision]
    model_name: str = ""
    prompt_version: str = "si-v1"


class SecondaryDomainDecision(BaseModel):
    """LLM decision for secondary domain classification."""
    selected_domain: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    evidence: list[str] = []


class RuleSuggestionOutput(BaseModel):
    """A single LLM-proposed business rule."""
    rule_type: str
    description: str
    expression: str
    target_columns: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class RuleSuggestionBatch(BaseModel):
    """Batch of LLM-proposed rules."""
    suggestions: list[RuleSuggestionOutput]
