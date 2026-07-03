"""Rule suggestions API routes."""

from typing import Any

from fastapi import APIRouter

from app.core.enums import RuleSuggestionStatus
from app.core.exceptions import RuleSuggestionNotFoundError
from app.services.rules.approval_service import ApprovalService
from app.schemas.requests import RuleApprovalRequest, RuleRejectionRequest

router = APIRouter(prefix="/rule-suggestions", tags=["rule-suggestions"])

# In-memory store for demo
_suggestions_store: dict[str, dict[str, Any]] = {}

approval_service = ApprovalService()


@router.get("")
def list_suggestions(status: str | None = None) -> dict[str, Any]:
    """List all rule suggestions with optional status filter."""
    suggestions = list(_suggestions_store.values())
    if status:
        suggestions = [s for s in suggestions if s.get("status") == status]
    return {"suggestions": suggestions}


@router.post("/{suggestion_id}/approve")
def approve_suggestion(suggestion_id: str, body: RuleApprovalRequest) -> dict[str, Any]:
    """Approve a proposed rule suggestion."""
    suggestion = _suggestions_store.get(suggestion_id)
    if not suggestion:
        raise RuleSuggestionNotFoundError(suggestion_id)

    current_status = RuleSuggestionStatus(suggestion["status"])
    result = approval_service.approve(suggestion_id, current_status, body.comment)

    # Update store
    suggestion["status"] = result["new_status"]
    suggestion["comment"] = result.get("comment")
    suggestion["reviewed_at"] = result["reviewed_at"]

    return {"suggestion_id": suggestion_id, **result}


@router.post("/{suggestion_id}/reject")
def reject_suggestion(suggestion_id: str, body: RuleRejectionRequest) -> dict[str, Any]:
    """Reject a proposed rule suggestion."""
    suggestion = _suggestions_store.get(suggestion_id)
    if not suggestion:
        raise RuleSuggestionNotFoundError(suggestion_id)

    current_status = RuleSuggestionStatus(suggestion["status"])
    result = approval_service.reject(suggestion_id, current_status, body.reason)

    # Update store
    suggestion["status"] = result["new_status"]
    suggestion["rejection_reason"] = result.get("rejection_reason")
    suggestion["reviewed_at"] = result["reviewed_at"]

    return {"suggestion_id": suggestion_id, **result}
