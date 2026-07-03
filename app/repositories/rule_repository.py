"""Rule repository — persists rule definitions, suggestions, and evaluations."""

import uuid
from typing import Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.rule_definition import RuleDefinition
from app.models.rule_suggestion import RuleSuggestion
from app.models.rule_evaluation import RuleEvaluation
from app.core.enums import RuleSuggestionStatus


class RuleRepository:
    """Persists business rules and suggestions to PostgreSQL."""

    def __init__(self, session: Session):
        self._session = session

    def persist_rule_evaluation(self, run_id: uuid.UUID, rule_def_id: uuid.UUID,
                                evaluation: dict[str, Any]) -> None:
        """Persist a rule evaluation result."""
        re = RuleEvaluation(
            run_id=run_id,
            rule_definition_id=rule_def_id,
            records_checked=evaluation["records_checked"],
            pass_count=evaluation["pass_count"],
            fail_count=evaluation["fail_count"],
            score=evaluation["score"],
            evidence_json=evaluation.get("evidence"),
        )
        self._session.add(re)

    def persist_suggestion(self, run_id: uuid.UUID, suggestion: dict[str, Any]) -> uuid.UUID:
        """Persist an AI-proposed rule suggestion."""
        suggestion_id = uuid.uuid4()
        rs = RuleSuggestion(
            id=suggestion_id,
            run_id=run_id,
            suggested_definition_json=suggestion,
            confidence=suggestion.get("confidence", 0.0),
            status=RuleSuggestionStatus.PROPOSED.value,
            evidence_json=suggestion.get("evidence"),
        )
        self._session.add(rs)
        return suggestion_id

    def get_suggestion(self, suggestion_id: uuid.UUID) -> RuleSuggestion | None:
        """Get a rule suggestion by ID."""
        return self._session.get(RuleSuggestion, suggestion_id)

    def approve_suggestion(self, suggestion_id: uuid.UUID, comment: str | None = None) -> None:
        """Approve a rule suggestion."""
        suggestion = self.get_suggestion(suggestion_id)
        if suggestion:
            suggestion.status = RuleSuggestionStatus.APPROVED.value
            suggestion.comment = comment
            suggestion.reviewed_at = datetime.now(timezone.utc)
            self._session.flush()

    def reject_suggestion(self, suggestion_id: uuid.UUID, reason: str | None = None) -> None:
        """Reject a rule suggestion."""
        suggestion = self.get_suggestion(suggestion_id)
        if suggestion:
            suggestion.status = RuleSuggestionStatus.REJECTED.value
            suggestion.rejection_reason = reason
            suggestion.reviewed_at = datetime.now(timezone.utc)
            self._session.flush()

    def list_suggestions(self, run_id: uuid.UUID | None = None,
                         status: str | None = None) -> list[RuleSuggestion]:
        """List suggestions with optional filters."""
        query = self._session.query(RuleSuggestion)
        if run_id:
            query = query.filter(RuleSuggestion.run_id == run_id)
        if status:
            query = query.filter(RuleSuggestion.status == status)
        return query.all()

    def commit(self) -> None:
        """Commit transaction."""
        self._session.commit()
