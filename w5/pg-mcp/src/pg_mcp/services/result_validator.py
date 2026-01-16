"""Result validation service using LLM."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ValidationResult(BaseModel):
    """Result of LLM-based validation."""

    is_valid: bool = Field(description="Whether the result matches user intent")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score from 0 to 1"
    )
    explanation: str = Field(description="Explanation of the validation result")


# System prompt for result validation
VALIDATION_SYSTEM_PROMPT = """You are a database query result validator. Your task is to \
analyze whether query results correctly answer the user's original question.

Analyze the following:
1. Does the result structure match what was asked?
2. Does the data appear reasonable for the question?
3. Are there any obvious inconsistencies or errors?

Respond with a JSON object containing:
- "is_valid": boolean - true if the result appears to correctly answer the question
- "confidence": number between 0 and 1 - how confident you are in the assessment
- "explanation": string - brief explanation of your assessment

Be conservative: if you're uncertain, set is_valid to true but lower the confidence.
Empty results can be valid if the question naturally could have no matches."""


VALIDATION_USER_PROMPT_TEMPLATE = """User's Question: {user_intent}

Generated SQL Query:
{query}

Query Result ({row_count} rows{truncated_note}):
{result_summary}

Analyze whether this result correctly answers the user's question."""


@dataclass
class ResultValidatorConfig:
    """Configuration for result validator."""

    timeout: float = 30.0
    max_result_rows_for_validation: int = 20
    max_result_chars: int = 4000


class ResultValidator:
    """Validates query results using LLM to check if they match user intent.

    This service uses an LLM to analyze whether the query results
    appropriately answer the user's original natural language question.
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        config: ResultValidatorConfig | None = None,
    ) -> None:
        """Initialize the result validator.

        Args:
            client: OpenAI async client
            model: Model name to use for validation
            config: Optional configuration settings
        """
        self._client = client
        self._model = model
        self._config = config or ResultValidatorConfig()
        self._logger = logger.bind(service="result_validator", model=model)

    async def validate_result(
        self,
        query: str,
        user_intent: str,
        result: list[dict[str, Any]],
    ) -> ValidationResult:
        """Validate whether query results match user intent.

        Args:
            query: The SQL query that was executed
            user_intent: The user's original natural language question
            result: Query results as a list of dictionaries

        Returns:
            ValidationResult with validity, confidence, and explanation

        Raises:
            asyncio.TimeoutError: If validation times out
        """
        self._logger.info(
            "Validating result",
            query_length=len(query),
            user_intent_length=len(user_intent),
            result_row_count=len(result),
        )

        # Handle empty results
        if not result:
            return ValidationResult(
                is_valid=True,
                confidence=0.8,
                explanation="Empty result set. This could be valid if the query "
                "conditions naturally yield no matches.",
            )

        # Prepare result summary (truncate large results)
        result_summary, truncated = self._prepare_result_summary(result)

        # Build prompt
        truncated_note = ", truncated for validation" if truncated else ""
        user_message = VALIDATION_USER_PROMPT_TEMPLATE.format(
            user_intent=user_intent,
            query=query,
            row_count=len(result),
            truncated_note=truncated_note,
            result_summary=result_summary,
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore
                    temperature=0,
                    response_format={"type": "json_object"},
                ),
                timeout=self._config.timeout,
            )

            return self._parse_response(response)

        except asyncio.TimeoutError:
            self._logger.warning(
                "Validation timed out",
                timeout=self._config.timeout,
            )
            # Return a safe default on timeout - don't block valid results
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                explanation=f"Validation timed out after {self._config.timeout}s. "
                "Assuming result is valid.",
            )

        except Exception as e:
            self._logger.error("Validation failed", error=str(e))
            # Return a safe default on error
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                explanation=f"Validation error: {e}. Assuming result is valid.",
            )

    def _prepare_result_summary(
        self,
        result: list[dict[str, Any]],
    ) -> tuple[str, bool]:
        """Prepare a summary of the result for LLM validation.

        Truncates large results to avoid exceeding token limits.

        Args:
            result: Full query result

        Returns:
            Tuple of (summary_string, was_truncated)
        """
        max_rows = self._config.max_result_rows_for_validation
        max_chars = self._config.max_result_chars

        truncated = len(result) > max_rows
        rows_to_show = result[:max_rows]

        # Format as JSON for clarity
        try:
            summary = json.dumps(rows_to_show, indent=2, default=str)
        except (TypeError, ValueError):
            # Fallback to string representation
            summary = str(rows_to_show)

        # Truncate if still too long
        if len(summary) > max_chars:
            truncated = True
            summary = summary[:max_chars] + "\n... (truncated)"

        return summary, truncated

    def _parse_response(self, response: Any) -> ValidationResult:
        """Parse the LLM response into ValidationResult.

        Args:
            response: OpenAI ChatCompletion response

        Returns:
            Parsed ValidationResult
        """
        try:
            content = response.choices[0].message.content
            if not content:
                return ValidationResult(
                    is_valid=True,
                    confidence=0.5,
                    explanation="Empty response from validator. Assuming valid.",
                )

            data = json.loads(content)

            # Extract and validate fields
            is_valid = bool(data.get("is_valid", True))
            confidence = float(data.get("confidence", 0.5))
            explanation = str(data.get("explanation", "No explanation provided"))

            # Clamp confidence to [0, 1]
            confidence = max(0.0, min(1.0, confidence))

            self._logger.info(
                "Validation completed",
                is_valid=is_valid,
                confidence=confidence,
            )

            return ValidationResult(
                is_valid=is_valid,
                confidence=confidence,
                explanation=explanation,
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            self._logger.warning("Failed to parse validation response", error=str(e))
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                explanation=f"Failed to parse validation response: {e}. Assuming valid.",
            )
