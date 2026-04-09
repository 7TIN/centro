import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.main import app
from src.services.conversation_service import reset_conversation_store
from src.services.knowledge_service import reset_knowledge_store
from src.services.person_service import reset_person_store
from src.services.wiki_service import reset_wiki_store


@pytest.fixture(autouse=True)
def reset_test_stores():
    reset_person_store()
    reset_knowledge_store()
    reset_conversation_store()
    reset_wiki_store()


@pytest.mark.asyncio
async def test_github_ingest_updates_team_and_person_wiki(monkeypatch):
    async def fake_fetch_github_snapshot(
        owner: str,
        repo: str,
        max_items: int = 10,
        include_open_prs: bool = True,
        include_open_issues: bool = True,
        include_recent_merged_prs: bool = True,
    ):
        return {
            "repository": f"{owner}/{repo}",
            "repo_url": f"https://github.com/{owner}/{repo}",
            "description": "Demo repository",
            "fetched_at": "2026-04-09T12:00:00+00:00",
            "counts": {"open_prs": 1, "open_issues": 1, "merged_prs": 1},
            "open_prs": [
                {
                    "number": 101,
                    "title": "Improve release safety checks",
                    "url": f"https://github.com/{owner}/{repo}/pull/101",
                    "author": "alice",
                    "state": "open",
                    "updated_at": "2026-04-09T11:50:00+00:00",
                    "created_at": "2026-04-08T10:00:00+00:00",
                    "body": "Adds stricter rollout checks.",
                }
            ],
            "open_issues": [
                {
                    "number": 55,
                    "title": "Investigate webhook latency",
                    "url": f"https://github.com/{owner}/{repo}/issues/55",
                    "author": "bob",
                    "state": "open",
                    "updated_at": "2026-04-09T10:00:00+00:00",
                    "created_at": "2026-04-08T10:00:00+00:00",
                    "body": "Latency spikes in eu-west.",
                }
            ],
            "merged_prs": [
                {
                    "number": 99,
                    "title": "Fix rollback path",
                    "url": f"https://github.com/{owner}/{repo}/pull/99",
                    "author": "carol",
                    "state": "closed",
                    "updated_at": "2026-04-09T09:00:00+00:00",
                    "created_at": "2026-04-07T10:00:00+00:00",
                    "merged_at": "2026-04-09T08:50:00+00:00",
                    "body": "Merged with tests.",
                }
            ],
        }

    monkeypatch.setattr(main_module, "fetch_github_snapshot", fake_fetch_github_snapshot)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bootstrap = await client.post("/v1/demo/bootstrap")
        assert bootstrap.status_code == 200
        person_id = bootstrap.json()["default_person_id"]
        assert person_id

        ingest_resp = await client.post(
            "/v1/ingest/github",
            json={
                "owner": "acme",
                "repo": "payments-service",
                "person_id": person_id,
                "max_items": 5,
            },
        )
        assert ingest_resp.status_code == 200
        body = ingest_resp.json()
        assert body["repository"] == "acme/payments-service"
        assert body["counts"]["open_prs"] == 1
        assert body["team_page_path"].startswith("knowledge/github-acme-payments-service")
        assert body["person_knowledge_id"] is not None

        team_page = await client.get(f"/v1/team/wiki/pages/{body['team_page_path']}")
        assert team_page.status_code == 200
        team_content = team_page.json()["content"]
        assert "Improve release safety checks" in team_content
        assert "Investigate webhook latency" in team_content

        knowledge = await client.get(f"/v1/persons/{person_id}/knowledge")
        assert knowledge.status_code == 200
        items = knowledge.json()
        github_entries = [item for item in items if item["source_type"] == "github_sync"]
        assert len(github_entries) >= 1
        assert "GitHub sync for acme/payments-service" in github_entries[0]["content"]

