"""Markdown-backed person profile service."""
from __future__ import annotations

from datetime import datetime, timezone
import re

from src.core.exceptions import NotFoundError
from src.models.schemas import PersonCreate, PersonResponse, PersonUpdate
from src.services.wiki_service import (
    initialize_person_wiki,
    list_person_ids,
    list_person_profiles,
    parse_person_profile_page,
    sync_person_profile_page,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "person"


def _next_person_id(name: str) -> str:
    base = _slugify(name)
    existing = set(list_person_ids())
    if base not in existing:
        return base
    suffix = 2
    while True:
        candidate = f"{base}-{suffix}"
        if candidate not in existing:
            return candidate
        suffix += 1


def reset_person_store() -> None:
    """Compatibility no-op; wiki files are the source of truth."""
    return None


def create_person(payload: PersonCreate) -> PersonResponse:
    now = _utc_now()
    person = PersonResponse(
        id=_next_person_id(payload.name),
        name=payload.name,
        role=payload.role,
        department=payload.department,
        base_system_prompt=payload.base_system_prompt,
        communication_style=payload.communication_style,
        is_active=True,
        metadata=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    initialize_person_wiki(person)
    return person


def upsert_seed_person(
    person_id: str,
    name: str,
    role: str | None = None,
    department: str | None = None,
    base_system_prompt: str | None = None,
    communication_style: dict | None = None,
    metadata: dict | None = None,
) -> PersonResponse:
    existing = try_get_person(person_id)
    now = _utc_now()
    person = PersonResponse(
        id=person_id,
        name=name,
        role=role,
        department=department,
        base_system_prompt=base_system_prompt,
        communication_style=communication_style,
        is_active=True if existing is None else existing.is_active,
        metadata=metadata,
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    if existing is None:
        initialize_person_wiki(person)
    else:
        sync_person_profile_page(person)
    return person


def list_persons() -> list[PersonResponse]:
    return list_person_profiles()


def get_person(person_id: str) -> PersonResponse:
    return parse_person_profile_page(person_id)


def try_get_person(person_id: str) -> PersonResponse | None:
    try:
        return parse_person_profile_page(person_id)
    except NotFoundError:
        return None


def update_person(person_id: str, payload: PersonUpdate) -> PersonResponse:
    person = get_person(person_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return person

    data = person.model_dump(mode="python")
    data.update(updates)
    data["updated_at"] = _utc_now()
    updated = PersonResponse(**data)
    sync_person_profile_page(updated)
    return updated


def build_person_identity(person: PersonResponse) -> str:
    lines: list[str] = [f"Name: {person.name}"]
    if person.role:
        lines.append(f"Role: {person.role}")
    if person.department:
        lines.append(f"Team: {person.department}")
    if person.communication_style:
        lines.append(f"Communication Style: {person.communication_style}")
    return "\n".join(lines)

