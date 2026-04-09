"""GitHub ingestion service for markdown wiki updates."""
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


def _item_row(item: dict[str, Any], include_body: bool = False) -> str:
    number = item.get("number")
    title = item.get("title", "Untitled")
    author = item.get("author", "unknown")
    updated_at = item.get("updated_at", "unknown")
    url = item.get("url", "")
    line = f"- #{number} [{title}]({url}) by `{author}` (updated {updated_at})"
    if include_body:
        body = _shorten(item.get("body"), limit=220)
        if body:
            line += f"\n  - {body}"
    return line


async def _github_get(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, Any] | None = None,
) -> Any:
    response = await client.get(path, params=params)
    if response.is_success:
        return response.json()

    details: dict[str, Any] = {
        "status_code": response.status_code,
        "path": path,
    }
    try:
        payload = response.json()
        if isinstance(payload, dict):
            details["github_error"] = payload.get("message")
    except Exception:
        details["response_text"] = response.text[:500]

    raise ValidationError(
        message="GitHub API request failed",
        details=details,
    )


def _normalize_issue(item: dict[str, Any]) -> dict[str, Any]:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    return {
        "number": item.get("number"),
        "title": item.get("title") or "Untitled issue",
        "url": item.get("html_url") or "",
        "author": user.get("login") or "unknown",
        "state": item.get("state") or "open",
        "updated_at": item.get("updated_at") or "",
        "created_at": item.get("created_at") or "",
        "body": item.get("body") or "",
    }


def _normalize_pr(item: dict[str, Any]) -> dict[str, Any]:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    return {
        "number": item.get("number"),
        "title": item.get("title") or "Untitled pull request",
        "url": item.get("html_url") or "",
        "author": user.get("login") or "unknown",
        "state": item.get("state") or "open",
        "updated_at": item.get("updated_at") or "",
        "created_at": item.get("created_at") or "",
        "merged_at": item.get("merged_at"),
        "body": item.get("body") or "",
    }


async def fetch_github_snapshot(
    owner: str,
    repo: str,
    max_items: int = 10,
    include_open_prs: bool = True,
    include_open_issues: bool = True,
    include_recent_merged_prs: bool = True,
) -> dict[str, Any]:
    """Fetch normalized snapshot of repository state from GitHub REST API."""
    settings = get_settings()
    cleaned_owner = owner.strip()
    cleaned_repo = repo.strip()
    if not cleaned_owner or not cleaned_repo:
        raise ValidationError(
            message="GitHub owner and repo are required",
            details={"owner": owner, "repo": repo},
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "personx-github-ingestor",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    base_url = settings.github_api_base_url.rstrip("/")
    repo_path = f"/repos/{cleaned_owner}/{cleaned_repo}"
    per_page = max(1, min(max_items, 50))

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=timeout,
    ) as client:
        repo_data = await _github_get(client, repo_path)

        tasks: list[asyncio.Task] = []
        labels: list[str] = []

        if include_open_prs:
            labels.append("open_prs")
            tasks.append(
                asyncio.create_task(
                    _github_get(
                        client,
                        f"{repo_path}/pulls",
                        params={
                            "state": "open",
                            "sort": "updated",
                            "direction": "desc",
                            "per_page": per_page,
                        },
                    )
                )
            )

        if include_open_issues:
            labels.append("open_issues")
            tasks.append(
                asyncio.create_task(
                    _github_get(
                        client,
                        f"{repo_path}/issues",
                        params={
                            "state": "open",
                            "sort": "updated",
                            "direction": "desc",
                            "per_page": per_page,
                        },
                    )
                )
            )

        if include_recent_merged_prs:
            labels.append("merged_prs")
            tasks.append(
                asyncio.create_task(
                    _github_get(
                        client,
                        f"{repo_path}/pulls",
                        params={
                            "state": "closed",
                            "sort": "updated",
                            "direction": "desc",
                            "per_page": min(per_page * 3, 100),
                        },
                    )
                )
            )

        fetched: dict[str, Any] = {}
        if tasks:
            values = await asyncio.gather(*tasks)
            fetched = {label: value for label, value in zip(labels, values)}

    open_prs_raw = fetched.get("open_prs", []) or []
    open_issues_raw = fetched.get("open_issues", []) or []
    merged_prs_raw = fetched.get("merged_prs", []) or []

    open_prs = [_normalize_pr(item) for item in open_prs_raw][:per_page]
    # /issues endpoint contains PRs too; filter those out.
    open_issues = [
        _normalize_issue(item)
        for item in open_issues_raw
        if "pull_request" not in item
    ][:per_page]

    merged_prs = [
        _normalize_pr(item)
        for item in merged_prs_raw
        if item.get("merged_at")
    ][:per_page]

    return {
        "repository": repo_data.get("full_name") or f"{cleaned_owner}/{cleaned_repo}",
        "repo_url": repo_data.get("html_url") or f"https://github.com/{cleaned_owner}/{cleaned_repo}",
        "description": repo_data.get("description") or "",
        "fetched_at": _utc_now_iso(),
        "counts": {
            "open_prs": len(open_prs),
            "open_issues": len(open_issues),
            "merged_prs": len(merged_prs),
        },
        "open_prs": open_prs,
        "open_issues": open_issues,
        "merged_prs": merged_prs,
    }


def render_github_snapshot_markdown(snapshot: dict[str, Any]) -> str:
    """Render normalized GitHub snapshot into markdown for team wiki page."""
    repo = snapshot.get("repository", "unknown")
    repo_url = snapshot.get("repo_url", "")
    description = snapshot.get("description", "")
    fetched_at = snapshot.get("fetched_at", _utc_now_iso())
    counts = snapshot.get("counts", {})
    open_prs = snapshot.get("open_prs", []) or []
    open_issues = snapshot.get("open_issues", []) or []
    merged_prs = snapshot.get("merged_prs", []) or []

    lines: list[str] = [
        f"## Repository: {repo}",
        f"- Source: {repo_url}",
        f"- Synced At: {fetched_at}",
        f"- Open PRs: {counts.get('open_prs', 0)}",
        f"- Open Issues: {counts.get('open_issues', 0)}",
        f"- Recently Merged PRs: {counts.get('merged_prs', 0)}",
        "",
    ]

    if description:
        lines.extend(["## Description", description, ""])

    lines.append("## Open Pull Requests")
    if open_prs:
        lines.extend(_item_row(item, include_body=False) for item in open_prs)
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("## Open Issues")
    if open_issues:
        lines.extend(_item_row(item, include_body=False) for item in open_issues)
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("## Recently Merged Pull Requests")
    if merged_prs:
        lines.extend(_item_row(item, include_body=False) for item in merged_prs)
    else:
        lines.append("- None.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_github_person_summary(snapshot: dict[str, Any], person_name: str | None = None) -> str:
    """Compact person-facing summary from GitHub snapshot."""
    repo = snapshot.get("repository", "unknown")
    fetched_at = snapshot.get("fetched_at", _utc_now_iso())
    counts = snapshot.get("counts", {})
    open_prs = snapshot.get("open_prs", []) or []
    open_issues = snapshot.get("open_issues", []) or []
    merged_prs = snapshot.get("merged_prs", []) or []

    greeting = f"GitHub sync for {repo}."
    if person_name:
        greeting = f"GitHub sync for {repo}, relevant for {person_name}."

    lines: list[str] = [
        greeting,
        f"Synced at {fetched_at}.",
        (
            "Counts: "
            f"{counts.get('open_prs', 0)} open PRs, "
            f"{counts.get('open_issues', 0)} open issues, "
            f"{counts.get('merged_prs', 0)} recently merged PRs."
        ),
        "",
        "Most recently updated open PRs:",
    ]
    if open_prs:
        lines.extend(_item_row(item, include_body=False) for item in open_prs[:5])
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("Most recently updated open issues:")
    if open_issues:
        lines.extend(_item_row(item, include_body=False) for item in open_issues[:5])
    else:
        lines.append("- None.")
    lines.append("")
    if merged_prs:
        lines.append("Recently merged PRs:")
        lines.extend(_item_row(item, include_body=False) for item in merged_prs[:5])
        lines.append("")

    return "\n".join(lines).strip()

