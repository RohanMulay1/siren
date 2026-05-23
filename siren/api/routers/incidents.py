from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc
from ...agent.graph import get_graph
from ...db.session import get_session_factory
from ...db.models import Incident
from ...config import get_settings

router = APIRouter()


@router.get("/incidents")
async def list_incidents(limit: int = 20):
    settings = get_settings()
    try:
        factory = get_session_factory(settings.async_database_url)
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


@router.post("/incidents/{incident_id}/approve")
async def approve_incident_action(incident_id: str, approved: bool = True):
    """Directly approve/reject the pending DESTRUCTIVE action — for demo/testing."""
    import asyncio
    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}
    current = graph.get_state(config)
    if not current or not current.values:
        raise HTTPException(status_code=404, detail="Incident not found")
    plan = list(current.values.get("action_plan", []))
    idx = current.values.get("current_action_index", 0)
    if not plan or idx >= len(plan):
        raise HTTPException(status_code=400, detail="No pending action")
    plan[idx] = {**plan[idx], "approved": approved}
    await graph.aupdate_state(config, {"action_plan": plan})
    asyncio.create_task(graph.ainvoke(None, config))
    return {"incident_id": incident_id, "action": plan[idx]["tool_name"], "approved": approved}


@router.get("/incidents/{incident_id}/history")
async def get_incident_history(incident_id: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}
    history = list(graph.get_state_history(config))
    return [{"step": i, "node": s.next, "values": s.values} for i, s in enumerate(history)]
