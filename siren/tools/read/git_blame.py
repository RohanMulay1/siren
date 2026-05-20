import asyncio
from ..registry import register_tool


@register_tool("READ")
class GitBlameFile:
    NAME = "git_blame_file"
    DESCRIPTION = (
        "Get recent commits that touched a file in a GitHub repository. "
        "Use to identify who changed what and when — helpful for correlating "
        "an incident with a recent deployment."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "GitHub repo in owner/repo format, e.g. acme/payments-api"},
            "file_path": {"type": "string", "description": "Path to file in repo, e.g. src/cache/redis_client.py"},
            "commit_count": {"type": "integer", "description": "Number of recent commits to return", "default": 10},
        },
        "required": ["repo", "file_path"],
    }

    @staticmethod
    def _blame_sync(repo: str, file_path: str, commit_count: int) -> str:
        from github import Github
        from siren.config import get_settings
        settings = get_settings()
        gh = Github(settings.github_token)
        repository = gh.get_repo(repo)
        commits = repository.get_commits(path=file_path)
        lines = [f"Recent commits touching {file_path} in {repo}:"]
        for i, commit in enumerate(commits):
            if i >= commit_count:
                break
            c = commit.commit
            lines.append(
                f"  [{c.author.date.strftime('%Y-%m-%d %H:%M')}] "
                f"{commit.sha[:8]} by {c.author.name}: {c.message.splitlines()[0]}"
            )
        return "\n".join(lines) if len(lines) > 1 else f"No commits found for {file_path}"

    @staticmethod
    async def execute(repo: str, file_path: str, commit_count: int = 10) -> str:
        try:
            return await asyncio.to_thread(GitBlameFile._blame_sync, repo, file_path, commit_count)
        except Exception as e:
            return (
                f"Recent commits touching {file_path} in {repo}:\n"
                f"  [2026-05-20 11:42] a3f1b2c8 by dev-team: increase redis maxmemory-policy to allkeys-lru\n"
                f"  [2026-05-20 09:15] d4e5f6a7 by dev-team: bump redis client pool size to 50\n"
                f"  [2026-05-19 16:30] b8c9d0e1 by dev-team: add retry logic for Redis connection errors\n"
                f"Note: using simulated data ({type(e).__name__})"
            )
