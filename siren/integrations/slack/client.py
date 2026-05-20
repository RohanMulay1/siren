from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from functools import lru_cache
from ...config import get_settings
from ...agent.state import ActionPlan
from .blocks import build_approval_message, build_incident_notification
import structlog

log = structlog.get_logger()


@lru_cache(maxsize=1)
def _get_slack_client() -> AsyncWebClient:
    settings = get_settings()
    return AsyncWebClient(token=settings.slack_bot_token)


async def send_approval_request(
    incident_id: str,
    correlation_id: str,
    severity: str,
    service: str,
    root_cause: str,
    action: ActionPlan,
    similar_context: str = "",
    investigation_summary: str = "",
) -> str:
    settings = get_settings()
    client = _get_slack_client()

    message = build_approval_message(
        incident_id=incident_id,
        severity=severity,
        service=service,
        root_cause=root_cause,
        action=action,
        similar_context=similar_context,
        investigation_summary=investigation_summary,
        correlation_id=correlation_id,
    )

    resp = await client.chat_postMessage(
        channel=settings.slack_channel_id,
        **message,
    )
    return resp["ts"]


async def send_notification(incident_id: str, severity: str, service: str, summary: str) -> None:
    settings = get_settings()
    client = _get_slack_client()

    message = build_incident_notification(incident_id, severity, service, summary)
    try:
        await client.chat_postMessage(channel=settings.slack_channel_id, **message)
    except SlackApiError as e:
        log.warning("slack_notification_failed", error=str(e))


async def update_message(channel: str, ts: str, text: str) -> None:
    client = _get_slack_client()
    try:
        await client.chat_update(channel=channel, ts=ts, text=text)
    except SlackApiError as e:
        log.warning("slack_update_failed", error=str(e))
