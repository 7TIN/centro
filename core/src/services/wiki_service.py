"""Persistent per-person wiki service (Approach B)."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil

from config.settings import get_settings
from src.core.exceptions import NotFoundError, ValidationError
from src.models.schemas import KnowledgeEntryResponse, PersonResponse


_SETTINGS = get_settings()
_APP_ROOT = Path(__file__).resolve().parents[2]


def _resolve_wiki_root() -> Path:
    configured = (_SETTINGS.wiki_root_dir or "data/wiki").strip()
    root = Path(configured)
    if not root.is_absolute():
        root = (_APP_ROOT / root).resolve()
    return root


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_person_key(person_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", person_id.strip())
    if not cleaned:
        raise ValidationError(
            message="Invalid person_id for wiki path",
            details={"person_id": person_id},
        )
    return cleaned


def _person_wiki_dir(person_id: str) -> Path:
    return _resolve_wiki_root() / _sanitize_person_key(person_id)


def _ensure_person_wiki_dirs(person_id: str) -> Path:
    wiki_dir = _person_wiki_dir(person_id)
    (wiki_dir / "knowledge").mkdir(parents=True, exist_ok=True)
    return wiki_dir


def _safe_read(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def _extract_person_name_from_profile(person_id: str) -> str | None:
    profile_path = _person_wiki_dir(person_id) / "profile.md"
    if not profile_path.exists():
        return None
    title = _extract_title(_safe_read(profile_path), fallback="")
    if title.startswith("Profile:"):
        return title.split("Profile:", maxsplit=1)[1].strip() or None
    return title or None


def _entry_title(entry: KnowledgeEntryResponse) -> str:
    if entry.title and entry.title.strip():
        return entry.title.strip()
    return f"Knowledge {entry.id[:8]}"


def _build_profile_page(person: PersonResponse) -> str:
    lines: list[str] = [
        f"# Profile: {person.name}",
        "",
        f"- Person ID: {person.id}",
        f"- Role: {person.role or 'Unknown'}",
        f"- Team: {person.department or 'Unknown'}",
        f"- Active: {person.is_active}",
        f"- Updated At: {person.updated_at.isoformat()}",
        "",
    ]

    if person.base_system_prompt:
        lines.extend(
            [
                "## Base System Prompt",
                person.base_system_prompt.strip(),
                "",
            ]
        )

    if person.communication_style:
        lines.extend(
            [
                "## Communication Style",
                "```json",
                json.dumps(person.communication_style, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )

    if person.metadata:
        lines.extend(
            [
                "## Metadata",
                "```json",
                json.dumps(person.metadata, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _build_knowledge_page(entry: KnowledgeEntryResponse) -> str:
    tags = ", ".join(entry.tags or [])
    lines: list[str] = [
        f"# Knowledge: {_entry_title(entry)}",
        "",
        f"- Entry ID: {entry.id}",
        f"- Person ID: {entry.person_id}",
        f"- Source Type: {entry.source_type}",
        f"- Source Reference: {entry.source_reference or 'N/A'}",
        f"- Priority: {entry.priority}",
        f"- Tags: {tags or 'N/A'}",
        f"- Created At: {entry.created_at.isoformat()}",
        f"- Updated At: {entry.updated_at.isoformat()}",
        "",
    ]

    if entry.summary:
        lines.extend(
            [
                "## Summary",
                entry.summary.strip(),
                "",
            ]
        )

    lines.extend(
        [
            "## Content",
            entry.content.strip(),
            "",
        ]
    )

    if entry.metadata:
        lines.extend(
            [
                "## Metadata",
                "```json",
                json.dumps(entry.metadata, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _ensure_log_file(person_id: str) -> Path:
    wiki_dir = _ensure_person_wiki_dirs(person_id)
    log_path = wiki_dir / "log.md"
    if not log_path.exists():
        log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    return log_path


def _append_log(person_id: str, action: str, details: str) -> None:
    log_path = _ensure_log_file(person_id)
    block = f"## [{_utc_now_iso()}] {action}\n{details.strip()}\n\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(block)


def _build_index_page(person_id: str, person_name: str | None = None) -> str:
    wiki_dir = _ensure_person_wiki_dirs(person_id)
    resolved_name = person_name or _extract_person_name_from_profile(person_id) or person_id
    knowledge_pages = sorted(
        (wiki_dir / "knowledge").glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    lines: list[str] = [
        f"# Wiki Index: {resolved_name}",
        "",
        f"- Person ID: {person_id}",
        f"- Updated At: {_utc_now_iso()}",
        "",
        "## Core Pages",
        "- [Profile](profile.md)",
        "- [Log](log.md)",
        "",
        "## Knowledge Pages",
    ]

    if not knowledge_pages:
        lines.append("- None yet.")
    else:
        for page in knowledge_pages:
            relative = page.relative_to(wiki_dir).as_posix()
            content = _safe_read(page)
            title = _extract_title(content, fallback=page.stem)
            updated_at = datetime.fromtimestamp(page.stat().st_mtime, tz=timezone.utc).isoformat()
            lines.append(f"- [{title}]({relative}) - updated {updated_at}")

    lines.append("")
    return "\n".join(lines)


def _write_index(person_id: str, person_name: str | None = None) -> None:
    wiki_dir = _ensure_person_wiki_dirs(person_id)
    index_content = _build_index_page(person_id=person_id, person_name=person_name)
    (wiki_dir / "index.md").write_text(index_content, encoding="utf-8")


def _resolve_wiki_page_path(person_id: str, page_path: str) -> Path:
    if not page_path or not page_path.strip():
        raise ValidationError(
            message="Wiki page path is required",
            details={"page_path": page_path},
        )

    wiki_dir = _person_wiki_dir(person_id).resolve()
    candidate = (wiki_dir / page_path).resolve()
    if candidate != wiki_dir and wiki_dir not in candidate.parents:
        raise ValidationError(
            message="Wiki page path is outside allowed directory",
            details={"page_path": page_path},
        )
    if candidate.suffix.lower() != ".md":
        raise ValidationError(
            message="Only markdown wiki pages are supported",
            details={"page_path": page_path},
        )
    return candidate


def initialize_person_wiki(person: PersonResponse) -> None:
    wiki_dir = _ensure_person_wiki_dirs(person.id)
    (wiki_dir / "profile.md").write_text(_build_profile_page(person), encoding="utf-8")
    _ensure_log_file(person.id)
    _write_index(person.id, person_name=person.name)
    _append_log(
        person.id,
        "person_initialized",
        f"Initialized wiki for {person.name}.",
    )


def sync_person_profile_page(person: PersonResponse) -> None:
    wiki_dir = _ensure_person_wiki_dirs(person.id)
    (wiki_dir / "profile.md").write_text(_build_profile_page(person), encoding="utf-8")
    _write_index(person.id, person_name=person.name)
    _append_log(
        person.id,
        "profile_updated",
        f"Updated profile for {person.name}.",
    )


def upsert_knowledge_page(person_id: str, entry: KnowledgeEntryResponse) -> str:
    wiki_dir = _ensure_person_wiki_dirs(person_id)
    page_path = wiki_dir / "knowledge" / f"{entry.id}.md"
    page_path.write_text(_build_knowledge_page(entry), encoding="utf-8")
    _write_index(person_id)
    _append_log(
        person_id,
        "knowledge_upsert",
        f"Upserted knowledge page for entry {entry.id} ({_entry_title(entry)}).",
    )
    return page_path.relative_to(wiki_dir).as_posix()


def rebuild_person_wiki(
    person: PersonResponse,
    knowledge_entries: list[KnowledgeEntryResponse],
) -> dict[str, int]:
    wiki_dir = _ensure_person_wiki_dirs(person.id)
    knowledge_dir = wiki_dir / "knowledge"
    (wiki_dir / "profile.md").write_text(_build_profile_page(person), encoding="utf-8")

    incoming_ids = {entry.id for entry in knowledge_entries}
    removed_count = 0
    for existing_path in knowledge_dir.glob("*.md"):
        if existing_path.stem in incoming_ids:
            continue
        existing_path.unlink(missing_ok=True)
        removed_count += 1

    written_count = 0
    for entry in sorted(knowledge_entries, key=lambda item: item.created_at):
        (knowledge_dir / f"{entry.id}.md").write_text(
            _build_knowledge_page(entry),
            encoding="utf-8",
        )
        written_count += 1

    _write_index(person.id, person_name=person.name)
    _append_log(
        person.id,
        "wiki_rebuilt",
        f"Rebuilt wiki with {written_count} knowledge pages and removed {removed_count} stale pages.",
    )

    return {"written_pages": written_count, "removed_pages": removed_count}


def list_wiki_pages(person_id: str) -> list[dict[str, str]]:
    wiki_dir = _person_wiki_dir(person_id).resolve()
    if not wiki_dir.exists() or not wiki_dir.is_dir():
        raise NotFoundError(
            message=f"Wiki not found for person: {person_id}",
            details={"person_id": person_id},
        )

    pages: list[dict[str, str]] = []
    for page in sorted(wiki_dir.rglob("*.md")):
        content = _safe_read(page)
        pages.append(
            {
                "path": page.relative_to(wiki_dir).as_posix(),
                "title": _extract_title(content, fallback=page.stem),
                "updated_at": datetime.fromtimestamp(
                    page.stat().st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
            }
        )
    return pages


def get_wiki_overview(person_id: str) -> dict[str, object]:
    wiki_dir = _person_wiki_dir(person_id).resolve()
    if not wiki_dir.exists() or not wiki_dir.is_dir():
        raise NotFoundError(
            message=f"Wiki not found for person: {person_id}",
            details={"person_id": person_id},
        )

    index_content = _safe_read(wiki_dir / "index.md")
    log_content = _safe_read(wiki_dir / "log.md")
    pages = list_wiki_pages(person_id)

    return {
        "person_id": person_id,
        "root_path": str(wiki_dir),
        "index_content": index_content,
        "log_content": log_content,
        "pages": pages,
    }


def read_wiki_page(person_id: str, page_path: str) -> dict[str, str]:
    wiki_dir = _person_wiki_dir(person_id).resolve()
    if not wiki_dir.exists() or not wiki_dir.is_dir():
        raise NotFoundError(
            message=f"Wiki not found for person: {person_id}",
            details={"person_id": person_id},
        )

    resolved_path = _resolve_wiki_page_path(person_id, page_path)
    if not resolved_path.exists() or not resolved_path.is_file():
        raise NotFoundError(
            message=f"Wiki page not found: {page_path}",
            details={"person_id": person_id, "page_path": page_path},
        )

    content = resolved_path.read_text(encoding="utf-8")
    return {
        "person_id": person_id,
        "path": resolved_path.relative_to(wiki_dir).as_posix(),
        "title": _extract_title(content, fallback=resolved_path.stem),
        "updated_at": datetime.fromtimestamp(
            resolved_path.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat(),
        "content": content,
    }


def render_wiki_context(
    person_id: str,
    max_pages: int | None = None,
    max_chars: int | None = None,
) -> str:
    wiki_dir = _person_wiki_dir(person_id)
    if not wiki_dir.exists() or not wiki_dir.is_dir():
        return ""

    page_limit = max_pages or _SETTINGS.wiki_context_max_pages
    char_limit = max_chars or _SETTINGS.wiki_context_max_chars

    sections: list[str] = []

    index_text = _safe_read(wiki_dir / "index.md")
    if index_text:
        sections.append("[Wiki Index]\n" + index_text.strip())

    profile_text = _safe_read(wiki_dir / "profile.md")
    if profile_text:
        sections.append("[Wiki Profile]\n" + profile_text.strip())

    knowledge_pages = sorted(
        (wiki_dir / "knowledge").glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:page_limit]

    for page in knowledge_pages:
        page_text = _safe_read(page)
        if not page_text:
            continue
        title = _extract_title(page_text, fallback=page.stem)
        relative = page.relative_to(wiki_dir).as_posix()
        sections.append(f"[Wiki Page: {title} | {relative}]\n{page_text.strip()}")

    context = "\n\n".join(section for section in sections if section.strip()).strip()
    if not context:
        return ""

    if len(context) <= char_limit:
        return context

    trimmed = context[:char_limit].rstrip()
    return trimmed + "\n\n[Wiki context truncated for prompt size]"


def reset_wiki_store() -> None:
    """Reset file-backed wiki store (used by tests)."""
    root = _resolve_wiki_root()
    if not root.exists():
        return

    # Safety check: never allow wiping filesystem roots.
    if len(root.parts) < 3:
        raise ValidationError(
            message="Refusing to reset wiki store for unsafe root path",
            details={"root": str(root)},
        )

    shutil.rmtree(root)
