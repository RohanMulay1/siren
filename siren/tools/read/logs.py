import json
from datetime import datetime, timedelta
from ..registry import register_tool


@register_tool("READ")
class FetchCloudwatchLogs:
    NAME = "fetch_cloudwatch_logs"
    DESCRIPTION = (
        "Fetch the last N log events from a CloudWatch log group. "
        "Use to inspect application errors, stack traces, and request logs."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "log_group": {"type": "string", "description": "CloudWatch log group name, e.g. /ecs/payments-api"},
            "log_stream": {"type": "string", "description": "Optional log stream filter"},
            "start_time": {"type": "string", "description": "ISO8601 datetime, defaults to 30 minutes ago"},
            "filter_pattern": {"type": "string", "description": "CloudWatch filter pattern, e.g. ERROR or OOM"},
            "limit": {"type": "integer", "description": "Max events to return, max 500", "default": 100},
        },
        "required": ["log_group"],
    }

    @staticmethod
    async def execute(
        log_group: str,
        log_stream: str | None = None,
        start_time: str | None = None,
        filter_pattern: str | None = None,
        limit: int = 100,
    ) -> str:
        try:
            import boto3
            from ..config import get_settings
            settings = get_settings()

            client = boto3.client("logs", region_name=settings.aws_default_region)

            start_ms = (
                int(datetime.fromisoformat(start_time).timestamp() * 1000)
                if start_time
                else int((datetime.utcnow() - timedelta(minutes=30)).timestamp() * 1000)
            )

            kwargs: dict = {
                "logGroupName": log_group,
                "startTime": start_ms,
                "limit": min(limit, 500),
                "interleaved": True,
            }
            if log_stream:
                kwargs["logStreamNames"] = [log_stream]
            if filter_pattern:
                kwargs["filterPattern"] = filter_pattern

            resp = client.filter_log_events(**kwargs)
            events = resp.get("events", [])

            if not events:
                return f"No log events found in {log_group} matching criteria."

            lines = []
            for e in events:
                ts = datetime.utcfromtimestamp(e["timestamp"] / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
                lines.append(f"[{ts}] {e['message'].strip()}")

            return "\n".join(lines)
        except Exception as e:
            return f"[CloudWatch error] {type(e).__name__}: {e}"
