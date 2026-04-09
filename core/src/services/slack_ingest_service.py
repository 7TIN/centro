"""Slack ingestion service for markdown wiki updates."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from config.settings import get_settings
from src.core.exceptions import ValidationError


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _shorten(text: str | None, limit: int = 280) -> str:
    if not text:
        return ""
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _format_ts(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return ts


async def _slack_api_call(
    client: httpx.AsyncClient,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.get(method, params=params)
    if not response.is_success:
        raise ValidationError(
            message="Slack API request failed",
            details={"status_code": response.status_code, "method": method},
        )

    payload = response.json()
    if not isinstance(payload, dict):
        raise ValidationError(
            message="Slack API returned unexpected payload",
            details={"method": method},
        )
    if payload.get("ok") is not True:
        raise ValidationError(
            message="Slack API returned an error",
            details={"method": method, "error": payload.get("error")},
        )
    return payload


def _normalize_message(item: dict[str, Any], author_name: str | None = None) -> dict[str, Any]:
    user = item.get("user")
    username = author_name or (user if isinstance(user, str) else "unknown")
    return {
        "ts": str(item.get("ts") or ""),
        "timestamp": _format_ts(item.get("ts")),
        "text": item.get("text") or "",
        "author": username,
        "user_id": user if isinstance(user, str) else None,
        "thread_ts": item.get("thread_ts"),
        "reply_count": int(item.get("reply_count") or 0),
        "subtype": item.get("subtype"),
    }


async def _resolve_user_names(
    client: httpx.AsyncClient,
    user_ids: set[str],
) -> dict[str, str]:
    if not user_ids:
        return {}

    async def fetch_one(user_id: str) -> tuple[str, str]:
        payload = await _slack_api_call(client, "users.info", params={"user": user_id})
        user = payload.get("user", {})
        profile = user.get("profile", {}) if isinstance(user, dict) else {}
        display_name = (
            profile.get("display_name")
            or profile.get("real_name")
            or user.get("name")
            or user_id
        )
        return user_id, str(display_name)

    tasks = [asyncio.create_task(fetch_one(user_id)) for user_id in sorted(user_ids)]
    results: dict[str, str] = {}
    if tasks:
        done = await asyncio.gather(*tasks, return_exceptions=True)
        for item in done:
            if isinstance(item, Exception):
                continue
            user_id, name = item
            results[user_id] = name
    return results


async def fetch_slack_channel_snapshot(
    channel_id: str,
    max_messages: int = 25,
    include_thread_replies: bool = True,
) -> dict[str, Any]:
    """Fetch normalized channel snapshot from Slack API."""
    settings = get_settings()
    token = settings.slack_token.strip()
    if not token:
        raise ValidationError(
            message="Slack token is not configured",
            details={"hint": "Set SLACK_TOKEN in environment"},
        )
    cleaned_channel = channel_id.strip()
    if not cleaned_channel:
        raise ValidationError(message="channel_id is required for Slack ingest")

    limit = max(1, min(max_messages, 100))

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(
        base_url=settings.slack_api_base_url.rstrip("/") + "/",
        headers=headers,
        timeout=timeout,
    ) as client:
        auth_payload = await _slack_api_call(client, "auth.test")
        channel_info_payload = await _slack_api_call(
            client,
            "conversations.info",
            params={"channel": cleaned_channel},
        )
        history_payload = await _slack_api_call(
            client,
            "conversations.history",
            params={"channel": cleaned_channel, "limit": limit},
        )

        channel = channel_info_payload.get("channel", {})
        channel_name = channel.get("name") or cleaned_channel
        workspace = auth_payload.get("team") or "Slack Workspace"
        workspace_url = auth_payload.get("url") or ""

        raw_messages = history_payload.get("messages", []) or []
        thread_roots = [
            item
            for item in raw_messages
            if item.get("thread_ts") and item.get("thread_ts") == item.get("ts") and int(item.get("reply_count") or 0) > 0
        ]

        thread_replies: dict[str, list[dict[str, Any]]] = {}
        if include_thread_replies and thread_roots:
            async def fetch_thread_replies(root: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
                thread_ts = str(root.get("thread_ts") or "")
                payload = await _slack_api_call(
                    client,
                    "conversations.replies",
                    params={"channel": cleaned_channel, "ts": thread_ts, "limit": 20},
                )
                replies = payload.get("messages", []) or []
                # Skip first message because it is the root message itself.
                return thread_ts, replies[1:] if len(replies) > 1 else []

            tasks = [asyncio.create_task(fetch_thread_replies(root)) for root in thread_roots[:10]]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for item in results:
                    if isinstance(item, Exception):
                        continue
                    thread_ts, replies = item
                    thread_replies[thread_ts] = replies

        user_ids: set[str] = set()
        for item in raw_messages:
            user = item.get("user")
            if isinstance(user, str) and user:
                user_ids.add(user)
        for replies in thread_replies.values():
            for item in replies:
                user = item.get("user")
                if isinstance(user, str) and user:
                    user_ids.add(user)

        user_names = await _resolve_user_names(client, user_ids)

    messages = [
        _normalize_message(item, author_name=user_names.get(item.get("user")))
        for item in raw_messages
    ]

    normalized_threads: list[dict[str, Any]] = []
    for root in thread_roots[:10]:
        thread_ts = str(root.get("thread_ts") or "")
        replies = [
            _normalize_message(reply, author_name=user_names.get(reply.get("user")))
            for reply in thread_replies.get(thread_ts, [])
        ]
        normalized_threads.append(
            {
                "thread_ts": thread_ts,
                "root": _normalize_message(root, author_name=user_names.get(root.get("user"))),
                "replies": replies,
            }
        )

    return {
        "workspace": workspace,
        "workspace_url": workspace_url,
        "channel_id": cleaned_channel,
        "channel_name": channel_name,
        "fetched_at": _utc_now_iso(),
        "counts": {
            "messages": len(messages),
            "threads": len(normalized_threads),
            "thread_replies": sum(len(thread.get("replies", [])) for thread in normalized_threads),
        },
        "messages": messages,
        "threads": normalized_threads,
    }


def render_slack_snapshot_markdown(snapshot: dict[str, Any]) -> str:
    """Render normalized Slack snapshot into markdown for team wiki page."""
    workspace = snapshot.get("workspace", "Slack")
    workspace_url = snapshot.get("workspace_url", "")
    channel_name = snapshot.get("channel_name", "channel")
    channel_id = snapshot.get("channel_id", "")
    fetched_at = snapshot.get("fetched_at", _utc_now_iso())
    counts = snapshot.get("counts", {})
    messages = snapshot.get("messages", []) or []
    threads = snapshot.get("threads", []) or []

    lines: list[str] = [
        f"## Slack Channel Snapshot: #{channel_name}",
        f"- Workspace: {workspace}",
        f"- Workspace URL: {workspace_url or 'N/A'}",
        f"- Channel ID: {channel_id}",
        f"- Synced At: {fetched_at}",
        f"- Messages: {counts.get('messages', 0)}",
        f"- Threads: {counts.get('threads', 0)}",
        f"- Thread Replies: {counts.get('thread_replies', 0)}",
        "",
        "## Latest Messages",
    ]
    if messages:
        for item in messages[:20]:
            lines.append(
                f"- {item.get('timestamp')} `{item.get('author')}`: {_shorten(item.get('text'), limit=220)}"
            )
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("## Active Threads")
    if threads:
        for thread in threads[:10]:
            root = thread.get("root", {})
            lines.append(
                f"- Thread {thread.get('thread_ts')} root by `{root.get('author')}` at {root.get('timestamp')}: "
                f"{_shorten(root.get('text'), limit=180)}"
            )
            replies = thread.get("replies", []) or []
            for reply in replies[:5]:
                lines.append(
                    f"  - Reply by `{reply.get('author')}` at {reply.get('timestamp')}: "
                    f"{_shorten(reply.get('text'), limit=160)}"
                )
    else:
        lines.append("- None.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_slack_person_summary(snapshot: dict[str, Any], person_name: str | None = None) -> str:
    """Compact person-facing summary from Slack snapshot."""
    channel_name = snapshot.get("channel_name", "channel")
    fetched_at = snapshot.get("fetched_at", _utc_now_iso())
    counts = snapshot.get("counts", {})
    messages = snapshot.get("messages", []) or []
    threads = snapshot.get("threads", []) or []

    intro = f"Slack sync for #{channel_name}."
    if person_name:
        intro = f"Slack sync for #{channel_name}, relevant for {person_name}."

    lines: list[str] = [
        intro,
        f"Synced at {fetched_at}.",
        (
            "Counts: "
            f"{counts.get('messages', 0)} messages, "
            f"{counts.get('threads', 0)} threads, "
            f"{counts.get('thread_replies', 0)} thread replies."
        ),
        "",
        "Latest channel updates:",
    ]
    if messages:
        for item in messages[:8]:
            lines.append(
                f"- {item.get('timestamp')} `{item.get('author')}`: {_shorten(item.get('text'), limit=180)}"
            )
    else:
        lines.append("- None.")
    lines.append("")

    if threads:
        lines.append("Notable active threads:")
        for thread in threads[:5]:
            root = thread.get("root", {})
            lines.append(
                f"- {root.get('timestamp')} `{root.get('author')}`: {_shorten(root.get('text'), limit=160)}"
            )
        lines.append("")

    return "\n".join(lines).strip()

