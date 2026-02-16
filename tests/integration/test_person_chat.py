import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.main import app
from src.services.conversation_service import reset_conversation_store
from src.services.knowledge_service import reset_knowledge_store
from src.services.person_service import reset_person_store


@pytest.fixture(autouse=True)
def reset_stores():
    reset_person_store()
    reset_knowledge_store()
    reset_conversation_store()


@pytest.mark.asyncio
async def test_same_question_returns_persona_specific_responses(monkeypatch):
    async def fake_generate_with_retry(prompt: str, max_attempts: int = 3, retry_delay_seconds: float = 0.5):
        if "Role: Backend Engineer" in prompt:
            return "Backend path: check DB query plan first."
        if "Role: Infrastructure SRE" in prompt:
            return "SRE path: check error budget and rollback conditions."
        return "Generic answer"

    monkeypatch.setattr(main_module, "generate_with_retry", fake_generate_with_retry)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        backend_person = await client.post(
            "/v1/persons",
            json={
                "name": "Asha",
                "role": "Backend Engineer",
                "department": "Platform",
                "base_system_prompt": "Answer as Asha.",
            },
        )
        sre_person = await client.post(
            "/v1/persons",
            json={
                "name": "Kiran",
                "role": "Infrastructure SRE",
                "department": "Infra",
                "base_system_prompt": "Answer as Kiran.",
            },
        )

        backend_id = backend_person.json()["id"]
        sre_id = sre_person.json()["id"]

        q = "How should we handle production latency?"
        backend_chat = await client.post("/v1/chat", json={"person_id": backend_id, "message": q})
        sre_chat = await client.post("/v1/chat", json={"person_id": sre_id, "message": q})

    assert backend_chat.status_code == 200
    assert sre_chat.status_code == 200
    assert backend_chat.json()["response"] != sre_chat.json()["response"]
