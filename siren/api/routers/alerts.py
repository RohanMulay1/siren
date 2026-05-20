import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import redis.asyncio as aioredis
import structlog

from ...agent.graph import get_graph
from ...agent.state import initial_state

log = structlog.get_logger()
router = APIRouter()


class AlertWebhookPayload(BaseModel):
    source: str = "custom"  # "prometheus" | "pagerduty" | "cloudwatch" | "custom"
    alert_name: str = ""
    severity: str | None = None
    service: str | None = None
    description: str = ""
    labels: dict = Field(default_factory=dict)
    annotations: dict = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=datetime.utcnow)


class AlertResponse(BaseModel):
    incident_id: str
    status: str
    message: str


async def _run_incident(incident_id: str, correlation_id: str, raw_alert: dict, redis_url: str) -> None:
    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}

    state = initial_state(incident_id, correlation_id, raw_alert)

    # Store correlation → incident_id mapping for Slack approval webhook
    redis_client = aioredis.from_url(redis_url)
    await redis_client.setex(f"siren:correlation:{correlation_id}", 3600 * 4, incident_id)
    await redis_client.aclose()

    try:
        await graph.ainvoke(state, config)
        log.info("incident_complete", incident_id=incident_id)
    except Exception as e:
        log.error("incident_failed", incident_id=incident_id, error=str(e))


@router.post("/webhook/alert", response_model=AlertResponse)
async def receive_alert(
    payload: AlertWebhookPayload,
    background_tasks: BackgroundTasks,
):
    from ...config import get_settings
    settings = get_settings()

    incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    correlation_id = str(uuid.uuid4())[:8]

    raw_alert = payload.model_dump(mode="json")

    background_tasks.add_task(
        _run_incident,
        incident_id=incident_id,
        correlation_id=correlation_id,
        raw_alert=raw_alert,
        redis_url=settings.redis_url,
    )

    log.info("alert_received", incident_id=incident_id, source=payload.source, service=payload.service)

    return AlertResponse(
        incident_id=incident_id,
        status="accepted",
        message=f"Incident {incident_id} created and investigation started.",
    )
