"""Markdown-backed knowledge entry service."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.models.schemas import (
    KnowledgeEntryCreate,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdate,
)
from src.services.person_service import get_person
from src.services.wiki_service import (
    get_person_knowledge_entry,
    list_person_knowledge_entries,
    upsert_knowledge_page,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def reset_knowledge_store() -> None:
    """Compatibility no-op; wiki markdown is source-of-truth."""
    return None


def _build_entry(
    person_id: str,
    knowledge_id: str,
    content: str,
    title: str | None,
    summary: str | None,
    source_type: str,
    source_reference: str | None,
    tags: list[str] | None,
    priority: int,
    metadata: dict | None,
    created_at: datetime,
    updated_at: datetime,
) -> KnowledgeEntryResponse:
    return KnowledgeEntryResponse(
        id=knowledge_id,
        person_id=person_id,
        content=content,
        title=title,
        summary=summary,
        source_type=source_type,
        source_reference=source_reference,
        tags=tags,
        priority=priority,
        metadata=metadata,
        created_at=created_at,
        updated_at=updated_at,
    )


def add_knowledge_entry(person_id: str, payload: KnowledgeEntryCreate) -> KnowledgeEntryResponse:
    get_person(person_id)
    now = _utc_now()
    entry = _build_entry(
        person_id=person_id,
        knowledge_id=str(uuid4()),
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
    upsert_knowledge_page(person_id, entry)
    return entry


def upsert_seed_knowledge_entry(
    person_id: str,
    knowledge_id: str,
    content: str,
    title: str | None = None,
    summary: str | None = None,
    source_type: str = "seed",
    source_reference: str | None = None,
    tags: list[str] | None = None,
    priority: int = 7,
    metadata: dict | None = None,
) -> KnowledgeEntryResponse:
    get_person(person_id)
    existing = None
    try:
        existing = get_person_knowledge_entry(person_id, knowledge_id)
    except Exception:
        existing = None
    now = _utc_now()
    entry = _build_entry(
        person_id=person_id,
        knowledge_id=knowledge_id,
        content=content,
        title=title,
        summary=summary,
        source_type=source_type,
        source_reference=source_reference,
        tags=tags,
        priority=priority,
        metadata=metadata,
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    upsert_knowledge_page(person_id, entry)
    return entry


def list_knowledge_entries(person_id: str) -> list[KnowledgeEntryResponse]:
    get_person(person_id)
    return list_person_knowledge_entries(person_id)


def update_knowledge_entry(
    person_id: str,
    knowledge_id: str,
    payload: KnowledgeEntryUpdate,
) -> KnowledgeEntryResponse:
    current = get_person_knowledge_entry(person_id, knowledge_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return current

    data = current.model_dump(mode="python")
    data.update(updates)
    data["updated_at"] = _utc_now()
    updated = KnowledgeEntryResponse(**data)
    upsert_knowledge_page(person_id, updated)
    return updated


def render_knowledge_context(person_id: str, max_entries: int = 10) -> str:
    entries = list_knowledge_entries(person_id)
    if not entries:
        return ""

    selected = entries[:max_entries]
    sections: list[str] = []
    for entry in selected:
        header = entry.title or f"Knowledge ({entry.source_type})"
        source = entry.source_reference or entry.source_type
        sections.append(f"[{header} | source: {source}]")
        sections.append(entry.content.strip())
        sections.append("")

    return "\n".join(sections).strip()

