from fastapi import APIRouter, Request, Response
import redis.asyncio as aioredis
import structlog

from ...integrations.slack.approval_handler import handle_slack_action

log = structlog.get_logger()
router = APIRouter()


@router.post("/webhook/slack/action")
async def slack_action(request: Request):
    """
    Receives Slack interactive component payloads (button clicks).
    Must respond within 3 seconds — graph resume is async.
    """
    from ...config import get_settings
    settings = get_settings()

    body = await request.body()
    redis_client = aioredis.from_url(settings.redis_url)

    try:
        result = await handle_slack_action(body, redis_client)
    finally:
        await redis_client.aclose()

    # Return empty 200 immediately — Slack requires response within 3s
    return Response(status_code=200, content="", media_type="application/json")
