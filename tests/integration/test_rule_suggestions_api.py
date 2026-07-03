"""Integration tests for rule suggestion approval/rejection endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.api.routes.rule_suggestions import _suggestions_store


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def seed_suggestions():
    """Seed the in-memory store with test suggestions."""
    _suggestions_store.clear()
    _suggestions_store["sugg-001"] = {
        "suggestion_id": "sugg-001",
        "rule_type": "numeric_range",
        "description": "Amount should be positive",
        "expression": "amount > 0",
        "target_columns": ["amount"],
        "confidence": 0.88,
        "status": "proposed",
    }
    _suggestions_store["sugg-002"] = {
        "suggestion_id": "sugg-002",
        "rule_type": "non_null",
        "description": "Customer ID should not be null",
        "expression": "customer_id IS NOT NULL",
        "target_columns": ["customer_id"],
        "confidence": 0.92,
        "status": "proposed",
    }
    _suggestions_store["sugg-003"] = {
        "suggestion_id": "sugg-003",
        "rule_type": "allowed_values",
        "description": "Status must be valid",
        "expression": "status IN ('approved', 'declined')",
        "target_columns": ["status"],
        "confidence": 0.75,
        "status": "approved",  # Already approved
    }
    yield
    _suggestions_store.clear()


class TestRuleSuggestionEndpoints:
    """Test rule suggestion API endpoints."""

    def test_list_suggestions(self, client):
        resp = client.get("/api/v1/rule-suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggestions"]) == 3

    def test_list_suggestions_filter_by_status(self, client):
        resp = client.get("/api/v1/rule-suggestions?status=proposed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggestions"]) == 2
        assert all(s["status"] == "proposed" for s in data["suggestions"])

    def test_approve_proposed_rule(self, client):
        resp = client.post(
            "/api/v1/rule-suggestions/sugg-001/approve",
            json={"comment": "Confirmed by data team"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "approved"
        assert data["suggestion_id"] == "sugg-001"

        # Verify it's updated in store
        assert _suggestions_store["sugg-001"]["status"] == "approved"

    def test_reject_proposed_rule(self, client):
        resp = client.post(
            "/api/v1/rule-suggestions/sugg-002/reject",
            json={"reason": "Not applicable to this domain"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "rejected"
        assert _suggestions_store["sugg-002"]["status"] == "rejected"

    def test_cannot_approve_already_approved(self, client):
        resp = client.post(
            "/api/v1/rule-suggestions/sugg-003/approve",
            json={},
        )
        assert resp.status_code == 409
        data = resp.json()
        assert data["error"]["code"] == "INVALID_RULE_TRANSITION"

    def test_cannot_reject_already_approved(self, client):
        resp = client.post(
            "/api/v1/rule-suggestions/sugg-003/reject",
            json={"reason": "Too late"},
        )
        assert resp.status_code == 409

    def test_not_found_suggestion(self, client):
        resp = client.post(
            "/api/v1/rule-suggestions/nonexistent/approve",
            json={},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RULE_SUGGESTION_NOT_FOUND"
