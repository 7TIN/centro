import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.main import app
from src.services.conversation_service import reset_conversation_store
from src.services.knowledge_service import reset_knowledge_store
from src.services.person_service import reset_person_store
from src.services.wiki_service import reset_wiki_store


@pytest.fixture(autouse=True)
def reset_test_stores():
    reset_person_store()
    reset_knowledge_store()
    reset_conversation_store()
    reset_wiki_store()


@pytest.mark.asyncio
async def test_wiki_is_persisted_and_readable_per_person():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        person_resp = await client.post(
            "/v1/persons",
            json={
                "name": "Asha Patel",
                "role": "Staff Platform Engineer",
                "department": "Platform",
                "base_system_prompt": "Respond as Asha.",
            },
        )
        assert person_resp.status_code == 200
        person_id = person_resp.json()["id"]

        knowledge_resp = await client.post(
            f"/v1/persons/{person_id}/knowledge",
            json={
                "title": "Rollback preference",
                "content": "Always disable feature flag first before rollback artifact.",
                "source_type": "manual",
                "priority": 8,
            },
        )
        assert knowledge_resp.status_code == 200
        knowledge_id = knowledge_resp.json()["id"]

        wiki_resp = await client.get(f"/v1/persons/{person_id}/wiki")
        assert wiki_resp.status_code == 200
        wiki = wiki_resp.json()
        page_paths = {page["path"] for page in wiki["pages"]}
        assert "index.md" in page_paths
        assert "log.md" in page_paths
        assert "profile.md" in page_paths
        assert f"knowledge/{knowledge_id}.md" in page_paths
        assert "Rollback preference" in wiki["index_content"]

        page_resp = await client.get(
            f"/v1/persons/{person_id}/wiki/pages/knowledge/{knowledge_id}.md"
        )
        assert page_resp.status_code == 200
        page = page_resp.json()
        assert page["path"] == f"knowledge/{knowledge_id}.md"
        assert "Always disable feature flag first" in page["content"]


@pytest.mark.asyncio
async def test_chat_includes_wiki_context_in_prompt(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_generate_with_retry(
        prompt: str,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.5,
    ):
        captured["prompt"] = prompt
        return "wiki-aware answer"

    monkeypatch.setattr(main_module, "generate_with_retry", fake_generate_with_retry)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        person_resp = await client.post(
            "/v1/persons",
            json={
                "name": "Nina",
                "role": "SRE",
                "department": "Infra",
                "base_system_prompt": "Answer as Nina.",
            },
        )
        person_id = person_resp.json()["id"]

        await client.post(
            f"/v1/persons/{person_id}/knowledge",
            json={
                "title": "Incident rule",
                "content": "Nina prefers rollback-first when customer impact is visible.",
                "source_type": "manual",
            },
        )

        chat_resp = await client.post(
            "/v1/chat",
            json={
                "person_id": person_id,
                "message": "How should we handle a risky deploy?",
            },
        )

    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["response"] == "wiki-aware answer"
    assert body["metadata"]["team_context_used"] is True
    assert body["metadata"]["person_wiki_context_used"] is True
    assert "[Team Wiki: index.md]" in captured["prompt"]
    assert "[Person Wiki: profile.md]" in captured["prompt"]
    assert "Nina prefers rollback-first" in captured["prompt"]


@pytest.mark.asyncio
async def test_demo_bootstrap_creates_team_and_multiple_person_wikis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bootstrap_resp = await client.post("/v1/demo/bootstrap")
        assert bootstrap_resp.status_code == 200
        payload = bootstrap_resp.json()
        assert payload["team_id"] == "core-team"
        assert len(payload["persons"]) >= 4
        default_person = payload["default_person_id"]
        assert default_person

        team_wiki_resp = await client.get("/v1/team/wiki")
        assert team_wiki_resp.status_code == 200
        team_wiki = team_wiki_resp.json()
        page_paths = {page["path"] for page in team_wiki["pages"]}
        assert "index.md" in page_paths
        assert "status.md" in page_paths

        person_wiki_resp = await client.get(f"/v1/persons/{default_person}/wiki")
        assert person_wiki_resp.status_code == 200
        person_wiki = person_wiki_resp.json()
        person_page_paths = {page["path"] for page in person_wiki["pages"]}
        assert "synced/team_core_snapshot.md" in person_page_paths
