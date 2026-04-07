"""Server-side demo seed data for team + multiple persons."""
from __future__ import annotations

from dataclasses import dataclass

from src.services.knowledge_service import list_knowledge_entries, upsert_seed_knowledge_entry
from src.services.person_service import try_get_person, upsert_seed_person
from src.services.wiki_service import (
    ensure_team_wiki,
    get_team_wiki_overview,
    sync_team_to_all_person_wikis,
    write_team_wiki_page,
)


@dataclass(frozen=True)
class DemoKnowledgeSeed:
    knowledge_id: str
    title: str
    content: str
    source_type: str = "demo_seed"
    priority: int = 8


@dataclass(frozen=True)
class DemoPersonSeed:
    person_id: str
    name: str
    role: str
    department: str
    base_system_prompt: str
    communication_style: dict
    suggested_questions: list[str]
    first_question: str
    knowledge: list[DemoKnowledgeSeed]


DEMO_TEAM_PAGES = {
    "status.md": """
# Team Status

- Incident State: Stable
- Release Track: Controlled rollout
- Current Focus: payment reliability, deploy safety, and incident clarity

## Current Priorities
- Keep checkout error rate under guardrail during releases.
- Keep payment auth success healthy during staged rollout.
- Prefer mitigation-first when customer impact appears.
""".strip(),
    "runbook.md": """
# Shared Runbook

## Before Release
- CI must be green on default branch.
- Rollback owner and on-call ack must be present.
- Feature flag should start OFF.

## During Release
- Rollout in stages and verify metrics every stage.
- Stop progression when guardrails fail.
- Communicate status every 15 minutes during active rollout.

## Incident Rules
- If customer impact is visible, prioritize mitigation over launch.
- Unknown anomaly means hold, investigate, then proceed or rollback.
""".strip(),
    "decisions.md": """
# Team Decisions

## Operating Model
- Team wiki is the shared truth (`main` branch behavior).
- Personal wiki is person-specific context (`feature branch` behavior).
- Chat context must feed team wiki first, then selected person wiki.
- Never combine multiple personal wikis in the same answer context.
""".strip(),
}


DEMO_PERSONS: list[DemoPersonSeed] = [
    DemoPersonSeed(
        person_id="asha-patel",
        name="Asha Patel",
        role="Staff Platform Engineer",
        department="Platform",
        base_system_prompt=(
            "You are Asha. Speak like a calm teammate: concise, risk-aware, practical."
        ),
        communication_style={"tone": "concise", "style": "checklist-first", "risk_callouts": True},
        suggested_questions=[
            "Can we deploy payments now?",
            "What checks are mandatory before rollout?",
            "If auth success drops below threshold, what is immediate action?",
            "Give me a concise rollback order.",
        ],
        first_question="Can we deploy payments now?",
        knowledge=[
            DemoKnowledgeSeed(
                knowledge_id="asha-rollout-policy",
                title="Payment Rollout Guardrails",
                content=(
                    "Use rollout stages 10->25->50->100. Hold at least 15 minutes each stage. "
                    "Stop progression if checkout error rate rises by >0.5% or auth success drops below 97.5%."
                ),
            ),
            DemoKnowledgeSeed(
                knowledge_id="asha-rollback-priority",
                title="Rollback Priority Rule",
                content=(
                    "If two independent guardrails fail or customer-visible impact appears, rollback immediately. "
                    "Disable feature flag first, then rollback artifact."
                ),
            ),
        ],
    ),
    DemoPersonSeed(
        person_id="ravi-menon",
        name="Ravi Menon",
        role="Principal Backend Engineer",
        department="Platform",
        base_system_prompt=(
            "You are Ravi. Respond direct and technical, with short tradeoff reasoning."
        ),
        communication_style={"tone": "direct", "style": "root-cause-first", "likes_examples": True},
        suggested_questions=[
            "Where should we look first for checkout latency spike?",
            "How do we validate migration safety?",
            "What query-level checks should we run before release?",
            "What is the safest partial rollback strategy?",
        ],
        first_question="Where should we look first for checkout latency spike?",
        knowledge=[
            DemoKnowledgeSeed(
                knowledge_id="ravi-latency-debug",
                title="Latency Debug Path",
                content=(
                    "Check p95 by endpoint, DB lock waits, queue lag, and idempotency cache misses. "
                    "If DB lock waits spike with release, hold rollout and profile hot queries first."
                ),
            ),
            DemoKnowledgeSeed(
                knowledge_id="ravi-migration-safety",
                title="Migration Safety Rule",
                content=(
                    "All migration plans must be backward-compatible first, with rollback migration rehearsed in staging."
                ),
            ),
        ],
    ),
    DemoPersonSeed(
        person_id="meera-iyer",
        name="Meera Iyer",
        role="Engineering Manager",
        department="Platform",
        base_system_prompt=(
            "You are Meera. Speak clearly with decision framing, ownership, and stakeholder alignment."
        ),
        communication_style={"tone": "structured", "style": "decision-summary-first", "stakeholder_focus": True},
        suggested_questions=[
            "How should we communicate this release risk to leadership?",
            "What is our go/no-go decision summary?",
            "What should be updated in incident channel now?",
            "Who owns which action before launch?",
        ],
        first_question="What is our go/no-go decision summary?",
        knowledge=[
            DemoKnowledgeSeed(
                knowledge_id="meera-comms-template",
                title="Incident Update Template",
                content=(
                    "Every update should include: scope, customer impact, observed metrics, next checkpoint, and go/no-go call."
                ),
            ),
            DemoKnowledgeSeed(
                knowledge_id="meera-release-ownership",
                title="Release Ownership Rule",
                content=(
                    "Assign explicit rollout owner, rollback owner, and communications owner before entering production window."
                ),
            ),
        ],
    ),
    DemoPersonSeed(
        person_id="kabir-shah",
        name="Kabir Shah",
        role="SRE Lead",
        department="Reliability",
        base_system_prompt=(
            "You are Kabir. Prefer operational clarity and measurable action over abstract advice."
        ),
        communication_style={"tone": "calm", "style": "operational", "signal_driven": True},
        suggested_questions=[
            "What are first 3 actions in an incident spike?",
            "When do we pause rollout versus rollback?",
            "What signals are missing before a go call?",
            "How should on-call handoff be written?",
        ],
        first_question="What are first 3 actions in an incident spike?",
        knowledge=[
            DemoKnowledgeSeed(
                knowledge_id="kabir-incident-open",
                title="Incident Opening Play",
                content=(
                    "Create incident channel, assign commander, capture timeline start, and publish first status update in under 5 minutes."
                ),
            ),
            DemoKnowledgeSeed(
                knowledge_id="kabir-rollout-hold-rule",
                title="Hold vs Rollback Heuristic",
                content=(
                    "Hold when one guardrail blips and quickly recovers. Rollback when multiple guardrails fail or user impact grows."
                ),
            ),
        ],
    ),
]


def _seed_team_pages() -> None:
    ensure_team_wiki()
    existing_paths = {page["path"] for page in get_team_wiki_overview()["pages"]}
    for page_name, content in DEMO_TEAM_PAGES.items():
        if page_name in existing_paths:
            continue
        write_team_wiki_page(
            page_name=page_name,
            content=content,
            log_action="team_demo_seed_upsert",
        )


def ensure_demo_seed_data() -> dict[str, object]:
    _seed_team_pages()

    seeded_persons: list[dict[str, object]] = []
    for seed in DEMO_PERSONS:
        person_metadata = {
            "demo_seed": "v1",
            "suggested_questions": seed.suggested_questions,
            "first_question": seed.first_question,
            "team_context_policy": "team_first_then_selected_person",
        }

        existing_person = try_get_person(seed.person_id)
        should_upsert_person = (
            existing_person is None
            or not existing_person.metadata
            or "suggested_questions" not in existing_person.metadata
        )
        if should_upsert_person:
            person = upsert_seed_person(
                person_id=seed.person_id,
                name=seed.name,
                role=seed.role,
                department=seed.department,
                base_system_prompt=seed.base_system_prompt,
                communication_style=seed.communication_style,
                metadata=person_metadata,
            )
        else:
            person = existing_person

        existing_knowledge_ids = {entry.id for entry in list_knowledge_entries(seed.person_id)}
        for knowledge in seed.knowledge:
            if knowledge.knowledge_id in existing_knowledge_ids:
                continue
            upsert_seed_knowledge_entry(
                person_id=seed.person_id,
                knowledge_id=knowledge.knowledge_id,
                title=knowledge.title,
                content=knowledge.content,
                source_type=knowledge.source_type,
                priority=knowledge.priority,
                metadata={"demo_seed": "v1"},
            )

        seeded_persons.append(
            {
                "id": person.id,
                "name": person.name,
                "role": person.role,
                "department": person.department,
                "first_question": seed.first_question,
                "suggested_questions": seed.suggested_questions,
            }
        )

    synced_count = sync_team_to_all_person_wikis()
    team_overview = get_team_wiki_overview()

    return {
        "team_id": team_overview["team_id"],
        "team_name": team_overview["team_name"],
        "team_pages": len(team_overview["pages"]),
        "synced_person_wikis": synced_count,
        "persons": seeded_persons,
        "default_person_id": seeded_persons[0]["id"] if seeded_persons else None,
    }
