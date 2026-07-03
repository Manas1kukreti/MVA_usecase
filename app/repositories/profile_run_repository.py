"""Profile run repository — persists run results to PostgreSQL."""

import uuid
from typing import Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.profile_run import ProfileRun
from app.models.dataset_profile import DatasetProfile
from app.models.column_profile import ColumnProfile
from app.models.secondary_domain_result import SecondaryDomainResult
from app.models.quality_assessment import QualityAssessment
from app.models.readiness_assessment import ReadinessAssessment
from app.models.chart_specification import ChartSpecification
from app.core.enums import RunStatus
from app.core.constants import PIPELINE_VERSION


class ProfileRunRepository:
    """Persists profiling results to PostgreSQL."""

    def __init__(self, session: Session):
        self._session = session

    def create_run(self, run_id: uuid.UUID, primary_domain: str,
                   filename: str, file_type: str) -> ProfileRun:
        """Create a new profile run record."""
        run = ProfileRun(
            id=run_id,
            status=RunStatus.PENDING.value,
            primary_domain=primary_domain,
            source_filename=filename,
            source_file_type=file_type,
            pipeline_version=PIPELINE_VERSION,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def mark_processing(self, run_id: uuid.UUID) -> None:
        """Mark run as processing."""
        run = self._session.get(ProfileRun, run_id)
        if run:
            run.status = RunStatus.PROCESSING.value
            run.started_at = datetime.now(timezone.utc)
            self._session.flush()

    def mark_completed(self, run_id: uuid.UUID, row_count: int, column_count: int,
                       secondary_domain: str | None = None) -> None:
        """Mark run as completed."""
        run = self._session.get(ProfileRun, run_id)
        if run:
            run.status = RunStatus.COMPLETED.value
            run.completed_at = datetime.now(timezone.utc)
            run.row_count = row_count
            run.column_count = column_count
            run.dominant_secondary_domain = secondary_domain
            self._session.flush()

    def mark_failed(self, run_id: uuid.UUID, error_code: str, error_message: str) -> None:
        """Mark run as failed."""
        run = self._session.get(ProfileRun, run_id)
        if run:
            run.status = RunStatus.FAILED.value
            run.failed_at = datetime.now(timezone.utc)
            run.error_code = error_code
            run.error_message = error_message[:1000]
            self._session.flush()

    def get_run(self, run_id: uuid.UUID) -> ProfileRun | None:
        """Get a profile run by ID."""
        return self._session.get(ProfileRun, run_id)

    def persist_dataset_profile(self, run_id: uuid.UUID, profile_data: dict[str, Any]) -> None:
        """Persist dataset-level profile."""
        dp = DatasetProfile(
            run_id=run_id,
            row_count=profile_data.get("row_count", 0),
            column_count=profile_data.get("column_count", 0),
            duplicate_row_count=profile_data.get("duplicate_row_count", 0),
            memory_estimate_bytes=profile_data.get("memory_estimate_bytes"),
            inferred_grain=profile_data.get("inferred_grain"),
            profile_json=profile_data,
        )
        self._session.add(dp)

    def persist_column_profiles(self, run_id: uuid.UUID, columns: list[dict[str, Any]]) -> None:
        """Persist column profiles."""
        for col in columns:
            cp = ColumnProfile(
                run_id=run_id,
                physical_name=col["physical_name"],
                normalized_key=col["normalized_key"],
                pandas_dtype=col.get("pandas_dtype", "object"),
                refined_data_type=col.get("refined_data_type", "unknown"),
                statistics_json=col.get("statistics"),
                candidate_semantic_type=col.get("candidate_semantic_type"),
                candidate_column_role=col.get("candidate_column_role"),
                candidate_confidence=col.get("candidate_confidence"),
                confirmed_semantic_type=col.get("confirmed_semantic_type"),
                confirmed_column_role=col.get("confirmed_column_role"),
                schema_confidence=col.get("schema_confidence"),
                identifier_score=col.get("identifier_score"),
                is_grain_key=col.get("is_grain_key", False),
            )
            self._session.add(cp)

    def persist_quality_assessments(self, run_id: uuid.UUID, assessments: list[dict[str, Any]]) -> None:
        """Persist quality dimension assessments."""
        for a in assessments:
            qa = QualityAssessment(
                run_id=run_id,
                dimension=a["dimension"],
                score=a.get("score"),
                display_score=round(a["score"] * 100, 2) if a.get("score") is not None else None,
                status=a["status"],
                assessed_count=a.get("assessed_count"),
                violation_count=a.get("violation_count"),
                evidence_json=a.get("evidence"),
                reason=a.get("reason"),
            )
            self._session.add(qa)

    def persist_readiness_assessments(self, run_id: uuid.UUID, assessments: list[dict[str, Any]]) -> None:
        """Persist readiness assessments."""
        for a in assessments:
            ra = ReadinessAssessment(
                run_id=run_id,
                assessment_type=a["assessment_type"],
                score=a.get("score"),
                status=a["status"],
                strengths_json=a.get("strengths"),
                blockers_json=a.get("blocking_issues"),
                recommendations_json=a.get("recommendations"),
                evidence_json=a.get("evidence"),
                weight_profile_version=a.get("weight_profile_version"),
            )
            self._session.add(ra)

    def persist_charts(self, run_id: uuid.UUID, charts: list[dict[str, Any]]) -> None:
        """Persist chart specifications."""
        for c in charts:
            cs = ChartSpecification(
                run_id=run_id,
                chart_key=c["chart_key"],
                category=c["category"],
                chart_type=c["chart_type"],
                title=c["title"],
                specification_json=c,
                aggregated_data_json=c.get("data"),
                rank=c.get("rank", 1),
            )
            self._session.add(cs)

    def commit(self) -> None:
        """Commit the current transaction."""
        self._session.commit()
