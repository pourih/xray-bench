"""GitHub repository sync module using GitHub REST API."""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Optional
import httpx

from src.events import EventBus, GitHubSyncStatus


class GitHubPublisher:
    """Commits and pushes files to a GitHub repository via GitHub REST API."""

    def __init__(
        self,
        token: Optional[str] = None,
        repo: Optional[str] = None,
        branch: str = "main",
        commit_prefix: str = "Update proxy nodes [automated]",
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo = repo or os.getenv("GITHUB_REPO")
        self.branch = branch or os.getenv("GITHUB_BRANCH", "main")
        self.commit_prefix = commit_prefix
        self.event_bus = event_bus

    def is_configured(self) -> bool:
        """Check if required credentials are provided."""
        return bool(self.token and self.repo and "/" in self.repo)

    async def publish_file(
        self,
        local_file_path: Path | str,
        target_repo_path: Optional[str] = None,
    ) -> bool:
        """
        Commit and push a single file to GitHub repository.
        target_repo_path defaults to the local file's name or relative path.
        """
        local_path = Path(local_file_path)
        if not local_path.is_file():
            msg = f"Cannot publish: local file does not exist: {local_path}"
            if self.event_bus:
                self.event_bus.emit(GitHubSyncStatus(status="ERROR", message=msg))
            return False

        if not self.is_configured():
            msg = "GitHub sync skipped: GITHUB_TOKEN or GITHUB_REPO not configured in .env or config.yaml"
            if self.event_bus:
                self.event_bus.emit(GitHubSyncStatus(status="SKIPPED", message=msg))
            return False

        rel_path = target_repo_path or local_path.name
        rel_path = rel_path.replace("\\", "/").lstrip("/")

        with open(local_path, "rb") as f:
            content_bytes = f.read()

        b64_content = base64.b64encode(content_bytes).decode("utf-8")
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        commit_message = f"{self.commit_prefix} - {rel_path} ({timestamp_str})"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "xray-bench-sync",
        }

        api_url = f"https://api.github.com/repos/{self.repo}/contents/{rel_path}"

        if self.event_bus:
            self.event_bus.emit(
                GitHubSyncStatus(
                    status="STARTING",
                    message=f"Publishing {rel_path} to {self.repo}@{self.branch}...",
                )
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Check if the file already exists to get its sha
                existing_sha: Optional[str] = None
                get_resp = await client.get(
                    api_url,
                    headers=headers,
                    params={"ref": self.branch},
                )
                if get_resp.status_code == 200:
                    existing_sha = get_resp.json().get("sha")

                # 2. Put file contents
                payload = {
                    "message": commit_message,
                    "content": b64_content,
                    "branch": self.branch,
                }
                if existing_sha:
                    payload["sha"] = existing_sha

                put_resp = await client.put(
                    api_url,
                    headers=headers,
                    json=payload,
                )

                if put_resp.status_code in (200, 201):
                    commit_html_url = (
                        put_resp.json().get("commit", {}).get("html_url")
                        or f"https://github.com/{self.repo}/blob/{self.branch}/{rel_path}"
                    )
                    success_msg = f"Successfully pushed {rel_path} to {self.repo} ({self.branch})"
                    if self.event_bus:
                        self.event_bus.emit(
                            GitHubSyncStatus(
                                status="SUCCESS",
                                message=success_msg,
                                url=commit_html_url,
                            )
                        )
                    return True
                else:
                    err_detail = put_resp.text
                    err_msg = f"GitHub API error ({put_resp.status_code}): {err_detail}"
                    if self.event_bus:
                        self.event_bus.emit(GitHubSyncStatus(status="ERROR", message=err_msg))
                    return False

        except Exception as e:
            err_msg = f"Exception while syncing to GitHub: {e}"
            if self.event_bus:
                self.event_bus.emit(GitHubSyncStatus(status="ERROR", message=err_msg))
            return False
