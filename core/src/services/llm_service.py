"""Minimal LLM wrapper with retry handling for MVP chat."""
from __future__ import annotations

import asyncio

from src.core.exceptions import LLMError
from src.services.gemini_client import generate_text


async def generate_with_retry(
    prompt: str,
    max_attempts: int = 3,
    retry_delay_seconds: float = 0.5,
) -> str:
    """Generate text with bounded retries for transient failures."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await generate_text(prompt)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_attempts:
                if isinstance(exc, LLMError):
                    raise
                raise LLMError(
                    message="LLM generation failed after retries",
                    details={"attempts": attempt, "error": str(exc)},
                ) from exc
            await asyncio.sleep(retry_delay_seconds * attempt)

    # Unreachable, but keeps the type-checker honest.
    raise LLMError(
        message="LLM generation failed after retries",
        details={"error": str(last_error) if last_error else "unknown"},
    )
