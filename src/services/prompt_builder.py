"""
Simple prompt builder for Gemini-only mode.
Combines system prompt, person identity, knowledge, and user message.
"""
from pathlib import Path


def _read_knowledge_files(file_paths: list[str] | None) -> list[str]:
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


def build_prompt(
    user_message: str,
    system_prompt: str | None = None,
    person_identity: str | None = None,
    knowledge_text: str | None = None,
    knowledge_files: list[str] | None = None,
) -> str:
    parts: list[str] = []

    if system_prompt:
        parts.append(f"System Prompt:\n{system_prompt.strip()}")

    if person_identity:
        parts.append(f"Person Identity:\n{person_identity.strip()}")

    knowledge_parts = []
    if knowledge_text:
        knowledge_parts.append(knowledge_text.strip())
    knowledge_parts.extend(_read_knowledge_files(knowledge_files))
    if knowledge_parts:
        parts.append("Knowledge:\n" + "\n\n".join(knowledge_parts))

    parts.append(f"User Message:\n{user_message.strip()}")

    return "\n\n".join(parts).strip()
