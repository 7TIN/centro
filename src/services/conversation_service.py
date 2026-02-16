"""In-memory conversation persistence for MVP chat."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.core.exceptions import ValidationError
from src.models.schemas import ConversationResponse, MessageResponse


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


_CONVERSATIONS: dict[str, ConversationResponse] = {}
_MESSAGES_BY_CONVERSATION: dict[str, list[MessageResponse]] = {}


def reset_conversation_store() -> None:
    """Reset in-memory conversation store (used by tests)."""
    _CONVERSATIONS.clear()
    _MESSAGES_BY_CONVERSATION.clear()


def ensure_conversation(
    person_id: str,
    conversation_id: str | None = None,
    user_id: str = "anonymous",
) -> ConversationResponse:
    now = _utc_now()
    if conversation_id:
        existing = _CONVERSATIONS.get(conversation_id)
        if existing:
            if existing.person_id != person_id:
                raise ValidationError(
                    message="Conversation belongs to a different person",
                    details={
                        "conversation_id": conversation_id,
                        "expected_person_id": existing.person_id,
                        "received_person_id": person_id,
                    },
                )
            return existing

        created = ConversationResponse(
            id=conversation_id,
            user_id=user_id,
            person_id=person_id,
            title=None,
            is_active=True,
            summary=None,
            metadata={"storage": "in_memory"},
            created_at=now,
            updated_at=now,
        )
        _CONVERSATIONS[conversation_id] = created
        _MESSAGES_BY_CONVERSATION.setdefault(conversation_id, [])
        return created

    new_id = str(uuid4())
    created = ConversationResponse(
        id=new_id,
        user_id=user_id,
        person_id=person_id,
        title=None,
        is_active=True,
        summary=None,
        metadata={"storage": "in_memory"},
        created_at=now,
        updated_at=now,
    )
    _CONVERSATIONS[new_id] = created
    _MESSAGES_BY_CONVERSATION[new_id] = []
    return created


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    model: str | None = None,
    tokens_used: int | None = None,
    confidence_score: float | None = None,
    metadata: dict | None = None,
) -> MessageResponse:
    now = _utc_now()
    message = MessageResponse(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        model=model,
        tokens_used=tokens_used,
        confidence_score=confidence_score,
        metadata=metadata or {},
        created_at=now,
    )
    _MESSAGES_BY_CONVERSATION.setdefault(conversation_id, []).append(message)

    if conversation_id in _CONVERSATIONS:
        data = _CONVERSATIONS[conversation_id].model_dump()
        data["updated_at"] = now
        _CONVERSATIONS[conversation_id] = ConversationResponse(**data)

    return message


def get_conversation_history(conversation_id: str, max_messages: int = 10) -> list[dict[str, str]]:
    messages = _MESSAGES_BY_CONVERSATION.get(conversation_id, [])
    if max_messages <= 0:
        return []
    selected = messages[-max_messages:]
    return [{"role": msg.role, "content": msg.content} for msg in selected]
