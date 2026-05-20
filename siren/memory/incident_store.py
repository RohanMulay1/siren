from uuid import uuid4
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct

from ..agent.state import SimilarIncident
from ..config import get_settings
from .schemas import IncidentVectorPayload, build_embedding_text
from .embedder import embed


def recall_similar_incidents(
    client: QdrantClient,
    query_text: str,
    affected_service: str,
    severity: str,
    top_k: int | None = None,
    similarity_threshold: float | None = None,
) -> list[SimilarIncident]:
    settings = get_settings()
    top_k = top_k or settings.recall_top_k
    threshold = similarity_threshold or settings.similarity_threshold

    vector = embed(query_text)

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="resolved", match=MatchValue(value=True)),
            ],
            should=[
                FieldCondition(key="affected_service", match=MatchValue(value=affected_service)),
                FieldCondition(key="severity", match=MatchValue(value=severity)),
            ],
        ),
        limit=top_k,
        with_payload=True,
    )

    return [
        SimilarIncident(
            incident_id=r.payload["incident_id"],
            similarity_score=round(r.score, 3),
            description=r.payload["incident_summary"],
            root_cause=r.payload["root_cause"],
            resolution=r.payload["resolution_summary"],
            time_to_resolve_minutes=r.payload.get("time_to_resolve_minutes") or 0.0,
        )
        for r in results
        if r.score >= threshold
    ]


def upsert_incident(client: QdrantClient, payload: IncidentVectorPayload) -> str:
    settings = get_settings()
    embedding_text = build_embedding_text(payload)
    vector = embed(embedding_text)
    vector_id = str(uuid4())

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=vector_id,
                vector=vector,
                payload=payload.model_dump(mode="json"),
            )
        ],
    )
    return vector_id


def count_incidents(client: QdrantClient) -> int:
    settings = get_settings()
    result = client.count(collection_name=settings.qdrant_collection, exact=True)
    return result.count
