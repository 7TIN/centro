import pytest

from src.core.exceptions import LLMError
from src.services import llm_service


@pytest.mark.asyncio
async def test_generate_with_retry_succeeds_after_retry(monkeypatch):
    calls = {"count": 0}

    async def flaky_generate_text(prompt: str) -> str:
        calls["count"] += 1
        if calls["count"] < 2:
            raise RuntimeError("temporary failure")
        return "ok"

    monkeypatch.setattr(llm_service, "generate_text", flaky_generate_text)
    result = await llm_service.generate_with_retry("hello", max_attempts=3, retry_delay_seconds=0)

    assert result == "ok"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_generate_with_retry_raises_llm_error(monkeypatch):
    async def always_fail(prompt: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(llm_service, "generate_text", always_fail)

    with pytest.raises(LLMError):
        await llm_service.generate_with_retry("hello", max_attempts=2, retry_delay_seconds=0)
