import pytest

from src.services.prompt_builder import (
    build_prompt,
    build_persona_system_prompt,
    collect_knowledge_inputs,
)


def test_build_prompt_includes_retrieved_context():
    prompt = build_prompt(
        user_message="When should we deploy?",
        system_prompt="Answer as Person X.",
        person_identity="Person X is pragmatic.",
        knowledge_text="Deploy after tests pass.",
        retrieved_context=[
            {
                "text": "Production deploys run at 10:00 UTC.",
                "source": "runbook/deploy.md",
                "score": 0.91,
            }
        ],
    )

    assert "System Prompt:" in prompt
    assert "Person Identity:" in prompt
    assert "Knowledge:" in prompt
    assert "Retrieved Context:" in prompt
    assert "runbook/deploy.md" in prompt
    assert "Production deploys run at 10:00 UTC." in prompt


def test_collect_knowledge_inputs_reads_repo_files():
    parts = collect_knowledge_inputs(
        knowledge_files=["tests/fixtures/sample_knowledge.txt"],
    )

    assert len(parts) == 1
    assert "Deploy only after CI passes" in parts[0]


def test_collect_knowledge_inputs_rejects_outside_repo():
    with pytest.raises(ValueError):
        collect_knowledge_inputs(knowledge_files=["C:\\Windows\\System32\\drivers\\etc\\hosts"])


def test_build_persona_system_prompt_template():
    prompt = build_persona_system_prompt(
        base_prompt="Act as X.",
        name="Rahul",
        role="Backend Engineer",
        team="Platform",
        communication_style={"tone": "direct"},
    )
    assert "Person Profile:" in prompt
    assert "Name: Rahul" in prompt
    assert "Role: Backend Engineer" in prompt
