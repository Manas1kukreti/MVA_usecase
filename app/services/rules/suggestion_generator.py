"""Rule suggestion generator — proposes candidate rules via LLM."""

from typing import Any
import uuid

from app.core.enums import RuleSuggestionStatus
from app.core.logging import get_logger
from app.services.llm.interface import LLMProvider, LLMRequest
from app.services.llm.prompts import RULE_SUGGESTION_SYSTEM, RULE_SUGGESTION_PROMPT_V1
from app.services.llm.structured_output import RuleSuggestionBatch
from app.services.profiling.column_profiler import ColumnProfileResult

logger = get_logger(__name__)


class SuggestedRule:
    """An AI-proposed rule that requires approval before scoring."""

    def __init__(
        self,
        suggestion_id: str,
        rule_type: str,
        description: str,
        expression: str,
        target_columns: list[str],
        confidence: float,
        reasoning: str,
        status: RuleSuggestionStatus = RuleSuggestionStatus.PROPOSED,
    ):
        self.suggestion_id = suggestion_id
        self.rule_type = rule_type
        self.description = description
        self.expression = expression
        self.target_columns = target_columns
        self.confidence = confidence
        self.reasoning = reasoning
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "rule_type": self.rule_type,
            "description": self.description,
            "expression": self.expression,
            "target_columns": self.target_columns,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "status": self.status.value,
        }


class RuleSuggestionGenerator:
    """Generates rule suggestions via LLM. Suggestions are NEVER auto-activated."""

    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider

    def generate(
        self,
        profiles: list[ColumnProfileResult],
        primary_domain: str,
        secondary_domain: str | None,
    ) -> list[SuggestedRule]:
        """
        Generate rule suggestions using the LLM.

        All returned suggestions have status=proposed.
        They do NOT participate in scoring until approved.
        """
        columns_summary = self._build_columns_summary(profiles)

        prompt = RULE_SUGGESTION_PROMPT_V1.format(
            primary_domain=primary_domain,
            secondary_domain=secondary_domain or "unknown",
            columns_summary=columns_summary,
        )

        request = LLMRequest(
            prompt=prompt,
            system_message=RULE_SUGGESTION_SYSTEM,
            temperature=0.2,
            max_tokens=2000,
        )

        parsed, response = self._llm.complete_structured(request, RuleSuggestionBatch)
        if parsed is None:
            logger.warning("rule_suggestion_llm_failed", error=response.error)
            return []

        suggestions: list[SuggestedRule] = []
        for s in parsed.suggestions[:5]:  # Max 5 suggestions
            suggestions.append(SuggestedRule(
                suggestion_id=str(uuid.uuid4()),
                rule_type=s.rule_type,
                description=s.description,
                expression=s.expression,
                target_columns=s.target_columns,
                confidence=s.confidence,
                reasoning=s.reasoning,
                status=RuleSuggestionStatus.PROPOSED,
            ))

        return suggestions

    def _build_columns_summary(self, profiles: list[ColumnProfileResult]) -> str:
        """Build bounded column summary for the LLM prompt."""
        lines: list[str] = []
        for p in profiles[:30]:  # Bounded
            lines.append(
                f"- {p.physical_name}: type={p.pandas_dtype}, "
                f"nulls={p.null_ratio:.2%}, "
                f"distinct={p.distinct_count}, "
                f"samples={p.representative_values[:3]}"
            )
        return "\n".join(lines)
