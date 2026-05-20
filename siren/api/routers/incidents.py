from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc
from ...agent.graph import get_graph
from ...db import get_session_factory, Incident
from ...config import get_settings

router = APIRouter()


@router.get("/incidents")
async def list_incidents(limit: int = 20):
    settings = get_settings()
    try:
        factory = get_session_factory(settings.database_url)
        async with factory() as session:
            result = await session.execute(
                select(Incident).order_by(desc(Incident.created_at)).limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "incident_id": r.incident_id,
                    "severity": r.severity,
                    "affected_service": r.affected_service,
                    "workflow_status": r.workflow_status,
                    "root_cause": r.root_cause,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
                }
                for r in rows
            ]
    except Exception as e:
        return []


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}
    state = graph.get_state(config)
    if state is None or not state.values:
        raise HTTPException(status_code=404, detail="Incident not found")
    return state.values


@router.get("/incidents/{incident_id}/history")
async def get_incident_history(incident_id: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}
    history = list(graph.get_state_history(config))
    return [{"step": i, "node": s.next, "values": s.values} for i, s in enumerate(history)]
