"""Create two sample personas and knowledge entries for local Phase 2 testing."""
from src.models.schemas import KnowledgeEntryCreate, PersonCreate
from src.services.knowledge_service import add_knowledge_entry
from src.services.person_service import create_person, reset_person_store


def seed_test_personas() -> dict[str, str]:
    reset_person_store()

    backend = create_person(
        PersonCreate(
            name="Rahul",
            role="Senior Backend Engineer",
            department="Platform Infrastructure",
            base_system_prompt="Answer as Rahul. Use only provided knowledge.",
            communication_style={"tone": "direct", "length": "short"},
        )
    )
    sre = create_person(
        PersonCreate(
            name="Kiran",
            role="Infrastructure SRE",
            department="Reliability Engineering",
            base_system_prompt="Answer as Kiran. Prioritize incident safety.",
            communication_style={"tone": "calm", "length": "brief"},
        )
    )

    add_knowledge_entry(
        backend.id,
        KnowledgeEntryCreate(
            content="For DB latency, start with pg_stat_activity and slow query logs.",
            title="DB troubleshooting",
            source_type="manual",
            priority=8,
        ),
    )
    add_knowledge_entry(
        sre.id,
        KnowledgeEntryCreate(
            content="For incidents, evaluate rollback blast radius before touching config.",
            title="Incident response",
            source_type="manual",
            priority=9,
        ),
    )

    return {"backend_person_id": backend.id, "sre_person_id": sre.id}


if __name__ == "__main__":
    ids = seed_test_personas()
    print("Created test personas:")
    for key, value in ids.items():
        print(f"- {key}: {value}")
