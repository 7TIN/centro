"""In-memory person profile service for MVP persona chat."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.core.exceptions import NotFoundError
from src.models.schemas import PersonCreate, PersonResponse, PersonUpdate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


_PERSONS: dict[str, PersonResponse] = {}


def reset_person_store() -> None:
    """Reset in-memory person store (used by tests)."""
    _PERSONS.clear()


def create_person(payload: PersonCreate) -> PersonResponse:
    now = _utc_now()
    person = PersonResponse(
        id=str(uuid4()),
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
    _PERSONS[person.id] = person
    return person


def list_persons() -> list[PersonResponse]:
    return sorted(_PERSONS.values(), key=lambda person: person.created_at, reverse=True)


def get_person(person_id: str) -> PersonResponse:
    person = _PERSONS.get(person_id)
    if person is None:
        raise NotFoundError(
            message=f"Person not found: {person_id}",
            details={"person_id": person_id},
        )
    return person


def try_get_person(person_id: str) -> PersonResponse | None:
    return _PERSONS.get(person_id)


def update_person(person_id: str, payload: PersonUpdate) -> PersonResponse:
    person = get_person(person_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return person

    data = person.model_dump()
    data.update(updates)
    data["updated_at"] = _utc_now()
    updated = PersonResponse(**data)
    _PERSONS[person_id] = updated
    return updated


def build_person_identity(person: PersonResponse) -> str:
    """Build a compact identity block used in prompt assembly."""
    lines: list[str] = [f"Name: {person.name}"]
    if person.role:
        lines.append(f"Role: {person.role}")
    if person.department:
        lines.append(f"Team: {person.department}")
    if person.communication_style:
        lines.append(f"Communication Style: {person.communication_style}")
    return "\n".join(lines)
