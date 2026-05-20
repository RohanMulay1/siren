import asyncio
from ..state import IncidentState
from ...memory import get_qdrant_client, recall_similar_incidents
from ...config import get_settings


async def run(state: IncidentState) -> dict:
    settings = get_settings()
    client = get_qdrant_client()

    query_text = (
        f"Service: {state['affected_service']}. "
        f"Summary: {state['incident_summary']}."
    )

    # recall_similar_incidents uses sentence-transformers (CPU-bound sync) — run in thread
    similar = await asyncio.to_thread(
        recall_similar_incidents,
        client=client,
        query_text=query_text,
        affected_service=state["affected_service"],
        severity=state["severity"],
    )

    playbook = None
    if similar:
        top = similar[0]
        if top["similarity_score"] >= 0.85:
            playbook = (
                f"High-confidence match (score={top['similarity_score']:.0%}): "
                f"Past incident '{top['description']}' had root cause: {top['root_cause']}. "
                f"Was resolved by: {top['resolution']} in {top['time_to_resolve_minutes']:.0f} minutes."
            )

    return {
        "similar_incidents": similar,
        "recalled_playbook": playbook,
        "workflow_status": "investigating",
    }
