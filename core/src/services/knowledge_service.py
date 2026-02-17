"""In-memory knowledge entry service for MVP persona chat."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.core.exceptions import NotFoundError
from src.models.schemas import (
    KnowledgeEntryCreate,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdate,
)
from src.services.person_service import get_person


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


_KNOWLEDGE: dict[str, list[KnowledgeEntryResponse]] = {}


def reset_knowledge_store() -> None:
    """Reset in-memory knowledge store (used by tests)."""
    _KNOWLEDGE.clear()


def add_knowledge_entry(person_id: str, payload: KnowledgeEntryCreate) -> KnowledgeEntryResponse:
    # Enforce person existence for managed knowledge APIs.
    get_person(person_id)

    now = _utc_now()
    entry = KnowledgeEntryResponse(
        id=str(uuid4()),
        person_id=person_id,
        content=payload.content,
        title=payload.title,
        summary=payload.summary,
        source_type=payload.source_type,
        source_reference=payload.source_reference,
        tags=payload.tags,
        priority=payload.priority,
        metadata=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    _KNOWLEDGE.setdefault(person_id, []).append(entry)
    return entry


def list_knowledge_entries(person_id: str) -> list[KnowledgeEntryResponse]:
    get_person(person_id)
    entries = _KNOWLEDGE.get(person_id, [])
    return sorted(entries, key=lambda entry: entry.created_at, reverse=True)


def update_knowledge_entry(
    person_id: str,
    knowledge_id: str,
    payload: KnowledgeEntryUpdate,
) -> KnowledgeEntryResponse:
    entries = _KNOWLEDGE.get(person_id, [])
    for idx, entry in enumerate(entries):
        if entry.id != knowledge_id:
            continue
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return entry
        data = entry.model_dump()
        data.update(updates)
        data["updated_at"] = _utc_now()
        updated = KnowledgeEntryResponse(**data)
        entries[idx] = updated
        return updated

    raise NotFoundError(
        message=f"Knowledge entry not found: {knowledge_id}",
        details={"person_id": person_id, "knowledge_id": knowledge_id},
    )


def render_knowledge_context(person_id: str, max_entries: int = 10) -> str:
    """Render recent knowledge entries as prompt-ready context text."""
    entries = _KNOWLEDGE.get(person_id, [])
    if not entries:
        return ""

    selected = sorted(entries, key=lambda entry: entry.created_at, reverse=True)[:max_entries]
    sections: list[str] = []
    for entry in selected:
        header = entry.title or f"Knowledge ({entry.source_type})"
        source = entry.source_reference or entry.source_type
        sections.append(f"[{header} | source: {source}]")
        sections.append(entry.content.strip())
        sections.append("")

    return "\n".join(sections).strip()
