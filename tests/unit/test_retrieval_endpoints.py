import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.main import app


class FakeVectorStore:
    def __init__(self):
        self.last_upsert = None
        self.last_search = None

    def upsert_documents(self, person_id: str, documents: list[str], source: str = "manual"):
        self.last_upsert = {
            "person_id": person_id,
            "documents": documents,
            "source": source,
        }
        return 3

    def search(
        self,
        person_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ):
        self.last_search = {
            "person_id": person_id,
            "query": query,
            "top_k": top_k,
            "min_score": min_score,
        }
        return [
            {
                "id": "vec-1",
                "score": 0.88,
                "text": "Use blue-green rollout for production deploys.",
                "source": "ops/deploy_runbook.md",
                "metadata": {"person_id": person_id},
            }
        ]


@pytest.mark.asyncio
async def test_retrieval_index_endpoint(monkeypatch):
    fake_store = FakeVectorStore()
    monkeypatch.setattr(main_module, "get_vector_store_service", lambda: fake_store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/retrieval/index",
            json={
                "person_id": "person_x",
                "source": "manual",
                "knowledge_text": "Blue-green deploy strategy with two target groups.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["person_id"] == "person_x"
    assert body["indexed_chunks"] == 3
    assert fake_store.last_upsert is not None


@pytest.mark.asyncio
async def test_retrieval_search_endpoint(monkeypatch):
    fake_store = FakeVectorStore()
    monkeypatch.setattr(main_module, "get_vector_store_service", lambda: fake_store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/retrieval/search",
            json={
                "person_id": "person_x",
                "query": "How do we deploy safely?",
                "top_k": 4,
                "min_score": 0.5,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["person_id"] == "person_x"
    assert len(body["results"]) == 1
    assert body["results"][0]["source"] == "ops/deploy_runbook.md"
    assert fake_store.last_search is not None
    assert fake_store.last_search["top_k"] == 4


@pytest.mark.asyncio
async def test_chat_uses_retrieval_when_requested(monkeypatch):
    fake_store = FakeVectorStore()
    monkeypatch.setattr(main_module, "get_vector_store_service", lambda: fake_store)

    captured = {}

    async def fake_generate_text(prompt: str) -> str:
        captured["prompt"] = prompt
        return "retrieved answer"

    monkeypatch.setattr(main_module, "generate_text", fake_generate_text)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={
                "person_id": "person_x",
                "message": "How do we deploy safely?",
                "use_retrieval": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "retrieved answer"
    assert body["metadata"]["retrieval_used"] is True
    assert body["metadata"]["retrieved_chunks"] == 1
    assert "Retrieved Context:" in captured["prompt"]
