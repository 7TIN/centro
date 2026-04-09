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
async def test_slack_ingest_updates_team_and_person_wiki(monkeypatch):
    async def fake_fetch_slack_channel_snapshot(
        channel_id: str,
        max_messages: int = 25,
        include_thread_replies: bool = True,
    ):
        return {
            "workspace": "Centro Workspace",
            "workspace_url": "https://centro.slack.com",
            "channel_id": channel_id,
            "channel_name": "release-war-room",
            "fetched_at": "2026-04-09T12:15:00+00:00",
            "counts": {"messages": 2, "threads": 1, "thread_replies": 2},
            "messages": [
                {
                    "ts": "1712664000.100000",
                    "timestamp": "2026-04-09T11:59:00+00:00",
                    "text": "Holding rollout at 25 percent due to elevated checkout errors.",
                    "author": "Kabir Shah",
                    "user_id": "U001",
                    "thread_ts": None,
                    "reply_count": 0,
                    "subtype": None,
                },
                {
                    "ts": "1712664060.100000",
                    "timestamp": "2026-04-09T12:00:00+00:00",
                    "text": "Need auth success confirmation before next stage.",
                    "author": "Asha Patel",
                    "user_id": "U002",
                    "thread_ts": "1712664060.100000",
                    "reply_count": 2,
                    "subtype": None,
                },
            ],
            "threads": [
                {
                    "thread_ts": "1712664060.100000",
                    "root": {
                        "ts": "1712664060.100000",
                        "timestamp": "2026-04-09T12:00:00+00:00",
                        "text": "Need auth success confirmation before next stage.",
                        "author": "Asha Patel",
                        "user_id": "U002",
                        "thread_ts": "1712664060.100000",
                        "reply_count": 2,
                        "subtype": None,
                    },
                    "replies": [
                        {
                            "ts": "1712664090.100000",
                            "timestamp": "2026-04-09T12:01:00+00:00",
                            "text": "Auth recovered to 98.1 percent for last 5 minutes.",
                            "author": "Ravi Menon",
                            "user_id": "U003",
                            "thread_ts": "1712664060.100000",
                            "reply_count": 0,
                            "subtype": None,
                        },
                        {
                            "ts": "1712664150.100000",
                            "timestamp": "2026-04-09T12:02:00+00:00",
                            "text": "Proceed only after another interval check.",
                            "author": "Meera Iyer",
                            "user_id": "U004",
                            "thread_ts": "1712664060.100000",
                            "reply_count": 0,
                            "subtype": None,
                        },
                    ],
                }
            ],
        }

    monkeypatch.setattr(main_module, "fetch_slack_channel_snapshot", fake_fetch_slack_channel_snapshot)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bootstrap = await client.post("/v1/demo/bootstrap")
        assert bootstrap.status_code == 200
        person_id = bootstrap.json()["default_person_id"]
        assert person_id

        ingest_resp = await client.post(
            "/v1/ingest/slack",
            json={
                "channel_id": "C_RELEASE",
                "person_id": person_id,
                "max_messages": 20,
            },
        )
        assert ingest_resp.status_code == 200
        body = ingest_resp.json()
        assert body["workspace"] == "Centro Workspace"
        assert body["channel_name"] == "release-war-room"
        assert body["counts"]["messages"] == 2
        assert body["team_page_path"].startswith("knowledge/slack-c-release")
        assert body["person_knowledge_id"] is not None

        team_page = await client.get(f"/v1/team/wiki/pages/{body['team_page_path']}")
        assert team_page.status_code == 200
        team_content = team_page.json()["content"]
        assert "Holding rollout at 25 percent" in team_content
        assert "Auth recovered to 98.1 percent" in team_content

        knowledge = await client.get(f"/v1/persons/{person_id}/knowledge")
        assert knowledge.status_code == 200
        items = knowledge.json()
        slack_entries = [item for item in items if item["source_type"] == "slack_sync"]
        assert len(slack_entries) >= 1
        assert "Slack sync for #release-war-room" in slack_entries[0]["content"]

