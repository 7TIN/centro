"""
Simple prompt builder for Gemini-only mode.
Combines system prompt, person identity, knowledge, and user message.
"""
from pathlib import Path
from typing import Any


def read_knowledge_files(file_paths: list[str] | None) -> list[str]:
    if not file_paths:
        return []

    repo_root = Path(__file__).resolve().parents[2]
    contents: list[str] = []

    for path_str in file_paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = (repo_root / path).resolve()

        if repo_root not in path.parents and path != repo_root:
            raise ValueError(f"Knowledge file path not allowed: {path_str}")

        if not path.exists() or not path.is_file():
            raise ValueError(f"Knowledge file not found: {path_str}")

        contents.append(path.read_text(encoding="utf-8", errors="replace"))

    return contents


def collect_knowledge_inputs(
    knowledge_text: str | None = None,
    knowledge_files: list[str] | None = None,
) -> list[str]:
    """Collect inline knowledge and file-based knowledge into one list."""
    parts: list[str] = []
    if knowledge_text and knowledge_text.strip():
        parts.append(knowledge_text.strip())
    parts.extend(read_knowledge_files(knowledge_files))
    return parts


def format_retrieved_context(retrieved_context: list[dict[str, Any]] | None) -> str:
    """Format retrieved chunks into a readable context block."""
    if not retrieved_context:
        return ""

    lines: list[str] = []
    for index, item in enumerate(retrieved_context, start=1):
        text = str(item.get("text") or item.get("content") or "").strip()
        if not text:
            continue

        source = item.get("source")
        score = item.get("score")

        label = f"[Retrieved {index}"
        if source:
            label += f" | {source}"
        if isinstance(score, (int, float)):
            label += f" | score={float(score):.3f}"
        label += "]"

        lines.append(label)
        lines.append(text)
        lines.append("")

    return "\n".join(lines).strip()


def build_prompt(
    user_message: str,
    system_prompt: str | None = None,
    person_identity: str | None = None,
    knowledge_text: str | None = None,
    knowledge_files: list[str] | None = None,
    retrieved_context: list[dict[str, Any]] | None = None,
) -> str:
    parts: list[str] = []

    if system_prompt:
        parts.append(f"System Prompt:\n{system_prompt.strip()}")

    if person_identity:
        parts.append(f"Person Identity:\n{person_identity.strip()}")

    knowledge_parts = collect_knowledge_inputs(
        knowledge_text=knowledge_text,
        knowledge_files=knowledge_files,
    )
    if knowledge_parts:
        parts.append("Knowledge:\n" + "\n\n".join(knowledge_parts))

    retrieval_block = format_retrieved_context(retrieved_context)
    if retrieval_block:
        parts.append("Retrieved Context:\n" + retrieval_block)

    parts.append(f"User Message:\n{user_message.strip()}")

    return "\n\n".join(parts).strip()
