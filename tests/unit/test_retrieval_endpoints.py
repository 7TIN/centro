import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.main import app


class FakeVectorStore:
    def __init__(self):
        self.last_upsert = None
        self.last_search = None
        self.last_delete = None
        self.last_replace = None

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
        enable_hybrid_fallback: bool = True,
    ):
        self.last_search = {
            "person_id": person_id,
            "query": query,
            "top_k": top_k,
            "min_score": min_score,
            "enable_hybrid_fallback": enable_hybrid_fallback,
        }
        return [
            {
                "id": "vec-1",
                "score": 0.88,
                "text": "Use blue-green rollout for production deploys.",
                "source": "ops/deploy_runbook.md",
                "metadata": {"person_id": person_id},
                "retrieval_mode": "vector",
            }
        ]

    def delete_by_source(self, person_id: str, source: str):
        self.last_delete = {"person_id": person_id, "source": source}
        return 2

    def replace_source_documents(self, person_id: str, source: str, documents: list[str]):
        self.last_replace = {"person_id": person_id, "source": source, "documents": documents}
        return 2, 4


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
    assert body["results"][0]["retrieval_mode"] == "vector"
    assert fake_store.last_search is not None
    assert fake_store.last_search["top_k"] == 4
    assert fake_store.last_search["enable_hybrid_fallback"] is True


@pytest.mark.asyncio
async def test_chat_uses_retrieval_when_requested(monkeypatch):
    fake_store = FakeVectorStore()
    monkeypatch.setattr(main_module, "get_vector_store_service", lambda: fake_store)

    captured = {}

    async def fake_generate_with_retry(prompt: str, max_attempts: int = 3, retry_delay_seconds: float = 0.5) -> str:
        captured["prompt"] = prompt
        return "retrieved answer"

    monkeypatch.setattr(main_module, "generate_with_retry", fake_generate_with_retry)

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


@pytest.mark.asyncio
async def test_retrieval_delete_source_endpoint(monkeypatch):
    fake_store = FakeVectorStore()
    monkeypatch.setattr(main_module, "get_vector_store_service", lambda: fake_store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/retrieval/source/delete",
            json={"person_id": "person_x", "source": "runbook"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted_chunks"] == 2
    assert fake_store.last_delete == {"person_id": "person_x", "source": "runbook"}


@pytest.mark.asyncio
async def test_retrieval_replace_source_endpoint(monkeypatch):
    fake_store = FakeVectorStore()
    monkeypatch.setattr(main_module, "get_vector_store_service", lambda: fake_store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/retrieval/source/replace",
            json={
                "person_id": "person_x",
                "source": "runbook",
                "knowledge_text": "Deployment notes",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted_chunks"] == 2
    assert body["indexed_chunks"] == 4
    assert fake_store.last_replace is not None
