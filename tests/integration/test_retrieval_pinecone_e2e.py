import os

import pytest

from src.services.vector_store import VectorStoreService


pytestmark = pytest.mark.integration


def test_retrieval_pinecone_e2e():
    if os.getenv("RUN_PINECONE_E2E") != "1":
        pytest.skip("Set RUN_PINECONE_E2E=1 to run Pinecone integration test.")

    service = VectorStoreService()
    person_id = "pinecone_e2e_person"
    source = "pinecone_e2e_source"

    service.delete_by_source(person_id=person_id, source=source)
    indexed = service.upsert_documents(
        person_id=person_id,
        source=source,
        documents=[
            "Rollback should be considered first during high-error incidents.",
            "Blue-green deploys reduce blast radius for production releases.",
        ],
        extra_metadata={"suite": "pinecone_e2e"},
    )
    assert indexed > 0

    results = service.search(
        person_id=person_id,
        query="What should we do first in an incident?",
        top_k=3,
        min_score=0.1,
        enable_hybrid_fallback=True,
    )

    assert results
    combined_text = " ".join(result.get("text", "").lower() for result in results)
    assert "rollback" in combined_text

    deleted = service.delete_by_source(person_id=person_id, source=source)
    assert deleted >= 0
