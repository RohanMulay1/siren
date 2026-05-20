from fastapi import APIRouter
from collections import Counter
from ...memory import get_qdrant_client, count_incidents
from ...config import get_settings

router = APIRouter()


@router.get("/api/memory/stats")
async def memory_stats():
    settings = get_settings()
    try:
        qdrant = get_qdrant_client()
        points, _ = qdrant.scroll(
            collection_name=settings.qdrant_collection,
            limit=500,
            with_payload=True,
        )
    except Exception:
        return {"total": 0, "categories": {}, "services": {}, "severities": {}, "mttr_series": []}

    total = len(points)
    categories = Counter()
    services = Counter()
    severities = Counter()
    mttr_series = []

    for p in points:
        pay = p.payload or {}
        categories[pay.get("root_cause_category", "other")] += 1
        services[pay.get("affected_service", "unknown")] += 1
        severities[pay.get("severity", "P3")] += 1
        if pay.get("time_to_resolve_minutes") and pay.get("created_at"):
            mttr_series.append({
                "created_at": pay["created_at"],
                "mttr": float(pay["time_to_resolve_minutes"]),
                "service": pay.get("affected_service", "unknown"),
                "severity": pay.get("severity", "P3"),
                "category": pay.get("root_cause_category", "other"),
                "description": (pay.get("description") or pay.get("incident_summary") or "")[:80],
            })

    mttr_series.sort(key=lambda x: x["created_at"])

    return {
        "total": total,
        "categories": dict(categories),
        "services": dict(services),
        "severities": dict(severities),
        "mttr_series": mttr_series,
    }
