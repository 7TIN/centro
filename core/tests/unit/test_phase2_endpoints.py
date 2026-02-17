import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.main import app
from src.services.conversation_service import reset_conversation_store
from src.services.knowledge_service import reset_knowledge_store
from src.services.person_service import reset_person_store


@pytest.fixture(autouse=True)
def reset_phase2_stores():
    reset_person_store()
    reset_knowledge_store()
    reset_conversation_store()


@pytest.mark.asyncio
async def test_person_and_knowledge_crud_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        person_resp = await client.post(
            "/v1/persons",
            json={
                "name": "Rahul",
                "role": "Senior Backend Engineer",
                "department": "Platform",
                "base_system_prompt": "Answer as Rahul using only provided context.",
                "communication_style": {"tone": "direct"},
            },
        )
        assert person_resp.status_code == 200
        person = person_resp.json()
        person_id = person["id"]

        list_resp = await client.get("/v1/persons")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        get_resp = await client.get(f"/v1/persons/{person_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Rahul"

        patch_resp = await client.patch(
            f"/v1/persons/{person_id}",
            json={"role": "Principal Backend Engineer"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["role"] == "Principal Backend Engineer"

        knowledge_resp = await client.post(
            f"/v1/persons/{person_id}/knowledge",
            json={
                "content": "Always check logs first before changing configs.",
                "title": "Debug habit",
                "source_type": "manual",
                "priority": 7,
            },
        )
        assert knowledge_resp.status_code == 200

        knowledge_list = await client.get(f"/v1/persons/{person_id}/knowledge")
        assert knowledge_list.status_code == 200
        items = knowledge_list.json()
        assert len(items) == 1
        assert "Always check logs first" in items[0]["content"]


@pytest.mark.asyncio
async def test_chat_uses_persona_context(monkeypatch):
    captured = {}

    async def fake_generate_with_retry(prompt: str, max_attempts: int = 3, retry_delay_seconds: float = 0.5):
        captured["prompt"] = prompt
        return "persona answer"

    monkeypatch.setattr(main_module, "generate_with_retry", fake_generate_with_retry)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        person_resp = await client.post(
            "/v1/persons",
            json={
                "name": "Nina",
                "role": "SRE",
                "department": "Infra",
                "base_system_prompt": "Answer exactly as Nina.",
                "communication_style": {"tone": "concise"},
            },
        )
        person_id = person_resp.json()["id"]

        await client.post(
            f"/v1/persons/{person_id}/knowledge",
            json={
                "content": "Nina prefers rollback-first incident handling.",
                "source_type": "manual",
                "title": "Incident policy",
            },
        )

        chat_resp = await client.post(
            "/v1/chat",
            json={
                "person_id": person_id,
                "message": "How should we react to a bad deploy?",
            },
        )

    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["response"] == "persona answer"
    assert body["metadata"]["person_found"] is True
    assert body["metadata"]["knowledge_entries_used"] == 1
    assert "Nina prefers rollback-first incident handling." in captured["prompt"]
    assert "Role: SRE" in captured["prompt"]
