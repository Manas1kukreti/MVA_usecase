"""API response schemas."""

from typing import Any
from pydantic import BaseModel


class RunCreatedResponse(BaseModel):
    """Response after creating a profile run."""
    run_id: str
    status: str


class RunSummaryResponse(BaseModel):
    """Profile run summary."""
    run_id: str
    status: str
    primary_domain: str
    secondary_domain: dict[str, Any] | None = None
    source_filename: str = ""
    row_count: int | None = None
    column_count: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: dict[str, Any] | None = None


class FullResultResponse(BaseModel):
    """Complete profiling result."""
    run_id: str
    status: str
    primary_domain: str
    secondary_domain: dict[str, Any] = {}
    dataset_profile: dict[str, Any] = {}
    column_profiles: list[dict[str, Any]] = []
    column_classifications: list[dict[str, Any]] = []
    hierarchy: dict[str, Any] = {}
    quality_assessments: list[dict[str, Any]] = []
    overall_quality: dict[str, Any] = {}
    readiness_assessments: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    rule_evaluations: list[dict[str, Any]] = []
    rule_suggestions: list[dict[str, Any]] = []
    warnings: list[str] = []
    started_at: str | None = None
    completed_at: str | None = None
