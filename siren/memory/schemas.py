from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class IncidentVectorPayload(BaseModel):
    incident_id: str
    severity: str
    affected_service: str
    affected_region: str = "unknown"
    alert_source: str
    incident_summary: str

    root_cause: str
    root_cause_category: str  # "oom", "connection_pool", "deploy_regression", "disk_saturation", etc.
    symptoms: list[str]

    resolution_summary: str
    actions_taken: list[str]
    resolved: bool

    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    time_to_resolve_minutes: float | None = None

    resolution_effective: bool = True
    recurrence_count: int = 0
    postmortem_text: str = ""


def build_embedding_text(payload: IncidentVectorPayload) -> str:
    """
    Structured concatenation for embedding — NOT raw alert text.
    Maximizes semantic overlap between similar incidents across
    different phrasings of the same underlying failure mode.
    """
    return (
        f"Service: {payload.affected_service}. "
        f"Symptoms: {', '.join(payload.symptoms)}. "
        f"Root cause category: {payload.root_cause_category}. "
        f"Root cause: {payload.root_cause}. "
        f"Resolution: {payload.resolution_summary}. "
        f"Actions taken: {', '.join(payload.actions_taken)}."
    )
