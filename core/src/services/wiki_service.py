"""Markdown-first wiki storage for team + person knowledge."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from typing import Any

from config.settings import get_settings
from src.core.exceptions import NotFoundError, PersonXException, ValidationError
from src.models.schemas import KnowledgeEntryResponse, PersonResponse


_SETTINGS = get_settings()
_APP_ROOT = Path(__file__).resolve().parents[2]
_MACHINE_BLOCK_RE = re.compile(
    r"<!-- MACHINE_DATA_START -->\s*```json\s*(\{.*?\})\s*```\s*<!-- MACHINE_DATA_END -->",
    flags=re.DOTALL,
)

TEAM_WIKI_ID = "core-team"
TEAM_WIKI_NAME = "Core Team Wiki"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _resolve_wiki_root() -> Path:
    configured = (_SETTINGS.wiki_root_dir or "data/wiki").strip()
    root = Path(configured)
    if not root.is_absolute():
        root = (_APP_ROOT / root).resolve()
    return root


def _wiki_root() -> Path:
    root = _resolve_wiki_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _team_wiki_dir() -> Path:
    return _wiki_root() / "team" / "core"


def _persons_root_dir() -> Path:
    return _wiki_root() / "persons"


def _sanitize_person_key(person_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", person_id.strip())
    if not cleaned:
        raise ValidationError(
            message="Invalid person_id for wiki path",
            details={"person_id": person_id},
        )
    return cleaned


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "entry"


def _person_wiki_dir(person_id: str) -> Path:
    return _persons_root_dir() / _sanitize_person_key(person_id)


def _ensure_team_wiki_dirs() -> Path:
    team_dir = _team_wiki_dir()
    team_dir.mkdir(parents=True, exist_ok=True)
    return team_dir


def _ensure_person_wiki_dirs(person_id: str) -> Path:
    person_dir = _person_wiki_dir(person_id)
    (person_dir / "knowledge").mkdir(parents=True, exist_ok=True)
    (person_dir / "synced").mkdir(parents=True, exist_ok=True)
    return person_dir


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


def _json_dumps(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _machine_block(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<!-- MACHINE_DATA_START -->",
            "```json",
            _json_dumps(data),
            "```",
            "<!-- MACHINE_DATA_END -->",
        ]
    )


def _extract_machine_data(content: str) -> dict[str, Any]:
    match = _MACHINE_BLOCK_RE.search(content)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _default_team_pages() -> dict[str, str]:
    now = _utc_now_iso()
    return {
        "index.md": "\n".join(
            [
                "# Core Team Wiki",
                "",
                "- Purpose: Shared source of truth for the whole team.",
                f"- Last Updated: {now}",
                "",
                "## Primary Pages",
                "- [Current Status](status.md)",
                "- [Shared Runbook](runbook.md)",
                "- [Team Decisions](decisions.md)",
                "- [Team Log](log.md)",
                "",
                "## Notes",
                "- Treat this wiki like the `main` branch.",
                "- Person-specific wikis are like feature branches.",
            ]
        )
        + "\n",
        "status.md": "\n".join(
            [
                "# Team Status",
                "",
                f"- Updated: {now}",
                "- Incident State: Stable",
                "- Release Phase: Controlled rollout",
                "- Current Priority: Payments reliability + deploy safety",
                "",
                "## Active Focus",
                "- Keep checkout success and auth metrics healthy during releases.",
                "- Escalate quickly when confidence is low.",
            ]
        )
        + "\n",
        "runbook.md": "\n".join(
            [
                "# Shared Runbook",
                "",
                "## Release Safety",
                "- All required CI checks must pass.",
                "- Rollout should be staged and validated by metrics.",
                "- Keep rollback owner assigned before production changes.",
                "",
                "## Incident Response",
                "- Use incident channel when customer impact is visible.",
                "- Prefer mitigation-first when blast radius is unknown.",
            ]
        )
        + "\n",
        "decisions.md": "\n".join(
            [
                "# Team Decisions",
                "",
                "## 2026-04",
                "- Team wiki is the primary shared context for all personal assistants.",
                "- Personal wiki context is applied only for the selected person.",
                "- Team context is always fed first to keep shared truth aligned.",
            ]
        )
        + "\n",
        "log.md": "# Team Wiki Log\n\n",
    }


def _build_team_index_page() -> str:
    team_dir = _ensure_team_wiki_dirs()
    knowledge_pages = sorted(
        (team_dir / "knowledge").glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    lines: list[str] = [
        "# Core Team Wiki",
        "",
        "- Purpose: Shared source of truth for the whole team.",
        f"- Last Updated: {_utc_now_iso()}",
        "",
        "## Primary Pages",
        "- [Current Status](status.md)",
        "- [Shared Runbook](runbook.md)",
        "- [Team Decisions](decisions.md)",
        "- [Team Log](log.md)",
        "",
        "## Team Knowledge Pages",
    ]
    if not knowledge_pages:
        lines.append("- None yet.")
    else:
        for page in knowledge_pages:
            relative = page.relative_to(team_dir).as_posix()
            title = _extract_title(_safe_read(page), fallback=page.stem)
            updated_at = datetime.fromtimestamp(page.stat().st_mtime, tz=timezone.utc).isoformat()
            lines.append(f"- [{title}]({relative}) - updated {updated_at}")
    lines.extend(
        [
            "",
            "## Notes",
            "- Treat this wiki like the `main` branch.",
            "- Person-specific wikis are like feature branches.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_team_index() -> None:
    team_dir = _ensure_team_wiki_dirs()
    (team_dir / "index.md").write_text(_build_team_index_page(), encoding="utf-8")


def _append_team_log(action: str, details: str) -> None:
    team_dir = _ensure_team_wiki_dirs()
    log_path = team_dir / "log.md"
    if not log_path.exists():
        log_path.write_text("# Team Wiki Log\n\n", encoding="utf-8")
    block = f"## [{_utc_now_iso()}] {action}\n{details.strip()}\n\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(block)


def ensure_team_wiki(seed_pages: dict[str, str] | None = None) -> None:
    team_dir = _ensure_team_wiki_dirs()
    pages = seed_pages or _default_team_pages()
    created = 0
    for name, content in pages.items():
        page_path = team_dir / name
        if page_path.exists():
            continue
        page_path.write_text(content, encoding="utf-8")
        created += 1
    _write_team_index()
    if created:
        _append_team_log("team_wiki_initialized", f"Initialized {created} team wiki pages.")


def write_team_wiki_page(
    page_name: str,
    content: str,
    log_action: str | None = None,
) -> str:
    ensure_team_wiki()
    if not page_name.endswith(".md"):
        raise ValidationError(
            message="Team wiki page must be markdown",
            details={"page_name": page_name},
        )
    page_path = (_team_wiki_dir() / page_name).resolve()
    team_dir = _team_wiki_dir().resolve()
    if page_path != team_dir and team_dir not in page_path.parents:
        raise ValidationError(
            message="Team wiki page path outside allowed directory",
            details={"page_name": page_name},
        )
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(content.strip() + "\n", encoding="utf-8")
    _write_team_index()
    _append_team_log(log_action or "team_page_upsert", f"Updated team page `{page_name}`.")
    return page_path.relative_to(team_dir).as_posix()


def upsert_team_knowledge_page(
    title: str,
    content: str,
    page_slug: str | None = None,
    source_reference: str | None = None,
    tags: list[str] | None = None,
    updated_by: str | None = None,
    sync_person_wikis: bool = True,
) -> dict[str, object]:
    ensure_team_wiki()
    slug = _slugify(page_slug or title)
    tags_line = ", ".join(tags or [])
    page_body = "\n".join(
        [
            f"# Team Knowledge: {title.strip()}",
            "",
            f"- Slug: {slug}",
            f"- Updated At: {_utc_now_iso()}",
            f"- Updated By: {updated_by or 'system'}",
            f"- Source Reference: {source_reference or 'N/A'}",
            f"- Tags: {tags_line or 'N/A'}",
            "",
            "## Content",
            content.strip(),
            "",
        ]
    )
    relative_path = write_team_wiki_page(
        page_name=f"knowledge/{slug}.md",
        content=page_body,
        log_action="team_knowledge_upsert",
    )
    synced = sync_team_to_all_person_wikis() if sync_person_wikis else 0
    return {
        "team_id": TEAM_WIKI_ID,
        "page_path": relative_path,
        "updated_at": _utc_now_iso(),
        "synced_person_wikis": synced,
    }


def list_team_pages() -> list[dict[str, str]]:
    ensure_team_wiki()
    team_dir = _team_wiki_dir().resolve()
    pages: list[dict[str, str]] = []
    for page in sorted(team_dir.rglob("*.md")):
        content = _safe_read(page)
        pages.append(
            {
                "path": page.relative_to(team_dir).as_posix(),
                "title": _extract_title(content, fallback=page.stem),
                "updated_at": datetime.fromtimestamp(page.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    return pages


def get_team_wiki_overview() -> dict[str, object]:
    ensure_team_wiki()
    team_dir = _team_wiki_dir().resolve()
    return {
        "team_id": TEAM_WIKI_ID,
        "team_name": TEAM_WIKI_NAME,
        "root_path": str(team_dir),
        "index_content": _safe_read(team_dir / "index.md"),
        "log_content": _safe_read(team_dir / "log.md"),
        "pages": list_team_pages(),
    }


def read_team_wiki_page(page_path: str) -> dict[str, str]:
    ensure_team_wiki()
    if not page_path or not page_path.strip():
        raise ValidationError(message="Team wiki page path is required")
    team_dir = _team_wiki_dir().resolve()
    resolved = (team_dir / page_path).resolve()
    if resolved != team_dir and team_dir not in resolved.parents:
        raise ValidationError(
            message="Team wiki page path outside allowed directory",
            details={"page_path": page_path},
        )
    if resolved.suffix.lower() != ".md":
        raise ValidationError(
            message="Only markdown pages are supported",
            details={"page_path": page_path},
        )
    if not resolved.exists() or not resolved.is_file():
        raise NotFoundError(
            message=f"Team wiki page not found: {page_path}",
            details={"page_path": page_path},
        )
    content = resolved.read_text(encoding="utf-8")
    return {
        "team_id": TEAM_WIKI_ID,
        "path": resolved.relative_to(team_dir).as_posix(),
        "title": _extract_title(content, fallback=resolved.stem),
        "updated_at": datetime.fromtimestamp(resolved.stat().st_mtime, tz=timezone.utc).isoformat(),
        "content": content,
    }


def _build_profile_page(person: PersonResponse) -> str:
    payload = person.model_dump(mode="json")
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
        lines.extend(["## Base System Prompt", person.base_system_prompt.strip(), ""])
    if person.communication_style:
        lines.extend(["## Communication Style", _json_dumps(person.communication_style), ""])
    if person.metadata:
        lines.extend(["## Metadata", _json_dumps(person.metadata), ""])
    lines.extend(["## Machine Data", _machine_block(payload), ""])
    return "\n".join(lines).strip() + "\n"


def _build_knowledge_page(entry: KnowledgeEntryResponse) -> str:
    payload = entry.model_dump(mode="json")
    tags = ", ".join(entry.tags or [])
    lines: list[str] = [
        f"# Knowledge: {entry.title or entry.id[:8]}",
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
        lines.extend(["## Summary", entry.summary.strip(), ""])
    lines.extend(["## Content", entry.content.strip(), ""])
    if entry.metadata:
        lines.extend(["## Metadata", _json_dumps(entry.metadata), ""])
    lines.extend(["## Machine Data", _machine_block(payload), ""])
    return "\n".join(lines).strip() + "\n"


def _build_person_index_page(person: PersonResponse) -> str:
    person_dir = _ensure_person_wiki_dirs(person.id)
    knowledge_pages = sorted(
        (person_dir / "knowledge").glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    lines: list[str] = [
        f"# Wiki Index: {person.name}",
        "",
        f"- Person ID: {person.id}",
        f"- Updated At: {_utc_now_iso()}",
        "",
        "## Core Pages",
        "- [Profile](profile.md)",
        "- [Log](log.md)",
        "- [Synced Team Snapshot](synced/team_core_snapshot.md)",
        "",
        "## Knowledge Pages",
    ]
    if not knowledge_pages:
        lines.append("- None yet.")
    else:
        for page in knowledge_pages:
            relative = page.relative_to(person_dir).as_posix()
            title = _extract_title(_safe_read(page), fallback=page.stem)
            updated_at = datetime.fromtimestamp(page.stat().st_mtime, tz=timezone.utc).isoformat()
            lines.append(f"- [{title}]({relative}) - updated {updated_at}")
    lines.append("")
    return "\n".join(lines)


def _append_person_log(person_id: str, action: str, details: str) -> None:
    person_dir = _ensure_person_wiki_dirs(person_id)
    log_path = person_dir / "log.md"
    if not log_path.exists():
        log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    block = f"## [{_utc_now_iso()}] {action}\n{details.strip()}\n\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(block)


def _write_person_index(person: PersonResponse) -> None:
    person_dir = _ensure_person_wiki_dirs(person.id)
    (person_dir / "index.md").write_text(_build_person_index_page(person), encoding="utf-8")


def list_person_ids() -> list[str]:
    root = _persons_root_dir()
    if not root.exists():
        return []
    return sorted([item.name for item in root.iterdir() if item.is_dir()])


def parse_person_profile_page(person_id: str) -> PersonResponse:
    profile_path = _person_wiki_dir(person_id) / "profile.md"
    if not profile_path.exists() or not profile_path.is_file():
        raise NotFoundError(
            message=f"Person profile wiki not found: {person_id}",
            details={"person_id": person_id},
        )
    content = profile_path.read_text(encoding="utf-8")
    machine = _extract_machine_data(content)
    if machine:
        return PersonResponse(**machine)
    raise ValidationError(
        message="Person profile page is missing machine data block",
        details={"person_id": person_id, "path": str(profile_path)},
    )


def list_person_profiles() -> list[PersonResponse]:
    profiles: list[PersonResponse] = []
    for person_id in list_person_ids():
        try:
            profiles.append(parse_person_profile_page(person_id))
        except PersonXException:
            continue
    return sorted(profiles, key=lambda item: item.updated_at, reverse=True)


def initialize_person_wiki(person: PersonResponse) -> None:
    person_dir = _ensure_person_wiki_dirs(person.id)
    (person_dir / "profile.md").write_text(_build_profile_page(person), encoding="utf-8")
    if not (person_dir / "log.md").exists():
        (person_dir / "log.md").write_text("# Wiki Log\n\n", encoding="utf-8")
    sync_team_snapshot_for_person(person.id)
    _write_person_index(person)
    _append_person_log(person.id, "person_initialized", f"Initialized wiki for {person.name}.")


def sync_person_profile_page(person: PersonResponse) -> None:
    person_dir = _ensure_person_wiki_dirs(person.id)
    (person_dir / "profile.md").write_text(_build_profile_page(person), encoding="utf-8")
    sync_team_snapshot_for_person(person.id)
    _write_person_index(person)
    _append_person_log(person.id, "profile_updated", f"Updated profile for {person.name}.")


def _knowledge_page_path(person_id: str, knowledge_id: str) -> Path:
    return _ensure_person_wiki_dirs(person_id) / "knowledge" / f"{knowledge_id}.md"


def upsert_knowledge_page(person_id: str, entry: KnowledgeEntryResponse) -> str:
    page_path = _knowledge_page_path(person_id, entry.id)
    page_path.write_text(_build_knowledge_page(entry), encoding="utf-8")
    person = parse_person_profile_page(person_id)
    sync_team_snapshot_for_person(person_id)
    _write_person_index(person)
    _append_person_log(
        person_id,
        "knowledge_upsert",
        f"Upserted knowledge entry {entry.id} ({entry.title or 'untitled'}).",
    )
    return page_path.relative_to(_person_wiki_dir(person_id)).as_posix()


def delete_knowledge_page(person_id: str, knowledge_id: str) -> bool:
    page_path = _knowledge_page_path(person_id, knowledge_id)
    if not page_path.exists():
        return False
    page_path.unlink(missing_ok=True)
    person = parse_person_profile_page(person_id)
    _write_person_index(person)
    _append_person_log(person_id, "knowledge_deleted", f"Deleted knowledge entry {knowledge_id}.")
    return True


def list_person_knowledge_entries(person_id: str) -> list[KnowledgeEntryResponse]:
    person_dir = _person_wiki_dir(person_id)
    if not person_dir.exists() or not person_dir.is_dir():
        raise NotFoundError(
            message=f"Wiki not found for person: {person_id}",
            details={"person_id": person_id},
        )
    entries: list[KnowledgeEntryResponse] = []
    for page in sorted((person_dir / "knowledge").glob("*.md")):
        content = page.read_text(encoding="utf-8")
        machine = _extract_machine_data(content)
        if not machine:
            continue
        try:
            entries.append(KnowledgeEntryResponse(**machine))
        except Exception:
            continue
    return sorted(entries, key=lambda item: item.created_at, reverse=True)


def get_person_knowledge_entry(person_id: str, knowledge_id: str) -> KnowledgeEntryResponse:
    for entry in list_person_knowledge_entries(person_id):
        if entry.id == knowledge_id:
            return entry
    raise NotFoundError(
        message=f"Knowledge entry not found: {knowledge_id}",
        details={"person_id": person_id, "knowledge_id": knowledge_id},
    )


def sync_team_snapshot_for_person(person_id: str) -> None:
    ensure_team_wiki()
    person_dir = _ensure_person_wiki_dirs(person_id)
    snapshot_path = person_dir / "synced" / "team_core_snapshot.md"
    index_text = _safe_read(_team_wiki_dir() / "index.md").strip()
    status_text = _safe_read(_team_wiki_dir() / "status.md").strip()
    runbook_text = _safe_read(_team_wiki_dir() / "runbook.md").strip()
    snapshot = "\n\n".join(
        [
            "# Synced Core Team Snapshot",
            "",
            f"- Synced At: {_utc_now_iso()}",
            "",
            "## Team Index",
            index_text or "No index available.",
            "",
            "## Team Status",
            status_text or "No status available.",
            "",
            "## Team Runbook",
            runbook_text or "No runbook available.",
        ]
    ).strip()
    snapshot_path.write_text(snapshot + "\n", encoding="utf-8")


def sync_team_to_all_person_wikis() -> int:
    count = 0
    for person_id in list_person_ids():
        sync_team_snapshot_for_person(person_id)
        count += 1
    if count:
        _append_team_log("team_sync", f"Synced team snapshot into {count} person wiki folders.")
    return count


def render_team_context(max_pages: int = 3, max_chars: int = 5000) -> str:
    ensure_team_wiki()
    team_dir = _team_wiki_dir()
    priority = ["index.md", "status.md", "runbook.md", "decisions.md"]
    pages: list[Path] = [team_dir / name for name in priority if (team_dir / name).exists()]
    knowledge_pages = sorted(
        (team_dir / "knowledge").glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    pages.extend(knowledge_pages)
    if max_pages > 0:
        pages = pages[:max_pages]
    blocks: list[str] = []
    for page in pages:
        text = _safe_read(page).strip()
        if not text:
            continue
        blocks.append(f"[Team Wiki: {page.name}]\n{text}")
    context = "\n\n".join(blocks).strip()
    if len(context) <= max_chars:
        return context
    return context[:max_chars].rstrip() + "\n\n[Team context truncated]"


def render_person_context(person_id: str, max_pages: int = 4, max_chars: int = 6000) -> str:
    person_dir = _person_wiki_dir(person_id)
    if not person_dir.exists():
        return ""

    blocks: list[str] = []
    profile_text = _safe_read(person_dir / "profile.md").strip()
    if profile_text:
        blocks.append("[Person Wiki: profile.md]\n" + profile_text)

    synced_text = _safe_read(person_dir / "synced" / "team_core_snapshot.md").strip()
    if synced_text:
        blocks.append("[Person Wiki: synced/team_core_snapshot.md]\n" + synced_text)

    knowledge_pages = sorted(
        (person_dir / "knowledge").glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if max_pages > 0:
        knowledge_pages = knowledge_pages[:max_pages]

    for page in knowledge_pages:
        text = _safe_read(page).strip()
        if not text:
            continue
        blocks.append(f"[Person Wiki: {page.relative_to(person_dir).as_posix()}]\n{text}")

    context = "\n\n".join(blocks).strip()
    if len(context) <= max_chars:
        return context
    return context[:max_chars].rstrip() + "\n\n[Person context truncated]"


def render_combined_context(
    person_id: str,
    team_max_pages: int = 3,
    person_max_pages: int = 4,
    max_chars: int = 11000,
) -> str:
    team = render_team_context(max_pages=team_max_pages, max_chars=max_chars)
    person = render_person_context(person_id=person_id, max_pages=person_max_pages, max_chars=max_chars)
    merged = "\n\n".join(section for section in [team, person] if section.strip()).strip()
    if len(merged) <= max_chars:
        return merged
    return merged[:max_chars].rstrip() + "\n\n[Combined context truncated]"


def _resolve_person_wiki_page_path(person_id: str, page_path: str) -> Path:
    if not page_path or not page_path.strip():
        raise ValidationError(message="Wiki page path is required")
    person_dir = _person_wiki_dir(person_id).resolve()
    resolved = (person_dir / page_path).resolve()
    if resolved != person_dir and person_dir not in resolved.parents:
        raise ValidationError(
            message="Wiki page path outside allowed directory",
            details={"page_path": page_path},
        )
    if resolved.suffix.lower() != ".md":
        raise ValidationError(
            message="Only markdown pages are supported",
            details={"page_path": page_path},
        )
    return resolved


def list_person_wiki_pages(person_id: str) -> list[dict[str, str]]:
    person_dir = _person_wiki_dir(person_id).resolve()
    if not person_dir.exists() or not person_dir.is_dir():
        raise NotFoundError(
            message=f"Wiki not found for person: {person_id}",
            details={"person_id": person_id},
        )
    pages: list[dict[str, str]] = []
    for page in sorted(person_dir.rglob("*.md")):
        content = _safe_read(page)
        pages.append(
            {
                "path": page.relative_to(person_dir).as_posix(),
                "title": _extract_title(content, fallback=page.stem),
                "updated_at": datetime.fromtimestamp(page.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    return pages


def get_person_wiki_overview(person_id: str) -> dict[str, object]:
    person_dir = _person_wiki_dir(person_id).resolve()
    if not person_dir.exists() or not person_dir.is_dir():
        raise NotFoundError(
            message=f"Wiki not found for person: {person_id}",
            details={"person_id": person_id},
        )
    return {
        "person_id": person_id,
        "root_path": str(person_dir),
        "index_content": _safe_read(person_dir / "index.md"),
        "log_content": _safe_read(person_dir / "log.md"),
        "pages": list_person_wiki_pages(person_id),
    }


def read_person_wiki_page(person_id: str, page_path: str) -> dict[str, str]:
    person_dir = _person_wiki_dir(person_id).resolve()
    if not person_dir.exists() or not person_dir.is_dir():
        raise NotFoundError(
            message=f"Wiki not found for person: {person_id}",
            details={"person_id": person_id},
        )
    resolved = _resolve_person_wiki_page_path(person_id, page_path)
    if not resolved.exists() or not resolved.is_file():
        raise NotFoundError(
            message=f"Wiki page not found: {page_path}",
            details={"person_id": person_id, "page_path": page_path},
        )
    content = resolved.read_text(encoding="utf-8")
    return {
        "person_id": person_id,
        "path": resolved.relative_to(person_dir).as_posix(),
        "title": _extract_title(content, fallback=resolved.stem),
        "updated_at": datetime.fromtimestamp(resolved.stat().st_mtime, tz=timezone.utc).isoformat(),
        "content": content,
    }


def rebuild_person_wiki(
    person: PersonResponse,
    knowledge_entries: list[KnowledgeEntryResponse],
) -> dict[str, int]:
    person_dir = _ensure_person_wiki_dirs(person.id)
    knowledge_dir = person_dir / "knowledge"
    (person_dir / "profile.md").write_text(_build_profile_page(person), encoding="utf-8")

    incoming = {entry.id for entry in knowledge_entries}
    removed = 0
    for page in knowledge_dir.glob("*.md"):
        if page.stem in incoming:
            continue
        page.unlink(missing_ok=True)
        removed += 1

    written = 0
    for entry in sorted(knowledge_entries, key=lambda item: item.created_at):
        (knowledge_dir / f"{entry.id}.md").write_text(_build_knowledge_page(entry), encoding="utf-8")
        written += 1

    sync_team_snapshot_for_person(person.id)
    _write_person_index(person)
    _append_person_log(
        person.id,
        "wiki_rebuilt",
        f"Rebuilt wiki with {written} knowledge pages and removed {removed} stale pages.",
    )
    return {"written_pages": written, "removed_pages": removed}


def reset_wiki_store() -> None:
    root = _resolve_wiki_root()
    if not root.exists():
        return
    if len(root.parts) < 3:
        raise ValidationError(
            message="Refusing to reset wiki store for unsafe root path",
            details={"root": str(root)},
        )
    shutil.rmtree(root)
