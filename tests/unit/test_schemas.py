import pytest
from pydantic import ValidationError

from src.models.schemas import (
    ChatRequest,
    HealthResponse,
    PersonResponse,
    RetrievalIndexRequest,
)


def test_chat_request_strips_message():
    payload = ChatRequest(person_id="person_x", message="  hello  ")
    assert payload.message == "hello"


def test_chat_request_rejects_whitespace_message():
    with pytest.raises(ValidationError):
        ChatRequest(person_id="person_x", message="   ")


def test_retrieval_index_requires_content():
    with pytest.raises(ValidationError):
        RetrievalIndexRequest(person_id="person_x")


def test_health_response_timestamp_is_timezone_aware():
    response = HealthResponse(
        status="healthy",
        environment="development",
        version="v1",
        database=False,
    )
    assert response.timestamp.tzinfo is not None


def test_person_response_accepts_object_attributes():
    class PersonRow:
        id = "abc"
        name = "X"
        role = "Engineer"
        department = "Platform"
        base_system_prompt = "prompt"
        communication_style = {"tone": "direct"}
        is_active = True
        metadata = {"team": "infra"}
        created_at = "2026-02-16T00:00:00Z"
        updated_at = "2026-02-16T00:00:00Z"

    parsed = PersonResponse.model_validate(PersonRow())
    assert parsed.id == "abc"
    assert parsed.name == "X"
