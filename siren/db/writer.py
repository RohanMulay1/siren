"""Write incident state to Postgres for structured querying and audit trail."""
from datetime import datetime, timezone
from .models import Incident, ActionAudit
from .session import get_session_factory
from ..agent.state import IncidentState
import structlog

log = structlog.get_logger()


async def upsert_incident_record(state: IncidentState, database_url: str) -> None:
    factory = get_session_factory(database_url)
    async with factory() as session:
        async with session.begin():
            from sqlalchemy import select
            result = await session.execute(
                select(Incident).where(Incident.incident_id == state["incident_id"])
            )
            record = result.scalar_one_or_none()

            now = datetime.now(timezone.utc)
            resolved_at = now if state.get("remediation_verified") else None

            if record is None:
                record = Incident(
                    incident_id=state["incident_id"],
                    severity=state.get("severity", "P3"),
                    affected_service=state.get("affected_service", "unknown"),
                    affected_region=state.get("affected_region", "unknown"),
                    alert_source=state.get("alert_source", "custom"),
                    incident_summary=state.get("incident_summary", ""),
                    root_cause=state.get("root_cause"),
                    root_cause_confidence=state.get("root_cause_confidence", 0.0),
                    workflow_status=state.get("workflow_status", "ingesting"),
                    raw_alert=state.get("raw_alert", {}),
                    similar_incidents_count=len(state.get("similar_incidents", [])),
                    resolved_at=resolved_at,
                    qdrant_vector_id=state.get("qdrant_vector_id"),
                    postmortem_id=state.get("postmortem_id"),
                )
                session.add(record)
            else:
                record.workflow_status = state.get("workflow_status", record.workflow_status)
                record.root_cause = state.get("root_cause") or record.root_cause
                record.root_cause_confidence = state.get("root_cause_confidence") or record.root_cause_confidence
                record.resolved_at = resolved_at or record.resolved_at
                record.qdrant_vector_id = state.get("qdrant_vector_id") or record.qdrant_vector_id
                record.postmortem_id = state.get("postmortem_id") or record.postmortem_id


async def write_action_audit(
    incident_id: str,
    action_id: str,
    tool_name: str,
    tool_args: dict,
    classification: str,
    approved: bool | None,
    approved_by: str | None,
    result_status: str,
    result_summary: str,
    database_url: str,
) -> None:
    factory = get_session_factory(database_url)
    async with factory() as session:
        async with session.begin():
            audit = ActionAudit(
                incident_id=incident_id,
                action_id=action_id,
                tool_name=tool_name,
                tool_args=tool_args,
                classification=classification,
                approved=approved,
                approved_by=approved_by,
                executed_at=datetime.now(timezone.utc),
                result_status=result_status,
                result_summary=result_summary[:500] if result_summary else "",
            )
            session.add(audit)
