from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PayloadSchemaType,
    HnswConfigDiff,
)
from functools import lru_cache
from ..config import get_settings
from .embedder import EMBEDDING_DIM


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )


def ensure_collection(client: QdrantClient, collection_name: str) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE,
        ),
        hnsw_config=HnswConfigDiff(m=16, ef_construct=200),
        on_disk_payload=True,
    )

    # Payload indexes for fast filtered search
    for field, schema_type in [
        ("severity", PayloadSchemaType.KEYWORD),
        ("affected_service", PayloadSchemaType.KEYWORD),
        ("root_cause_category", PayloadSchemaType.KEYWORD),
        ("resolved", PayloadSchemaType.BOOL),
        ("alert_source", PayloadSchemaType.KEYWORD),
    ]:
        client.create_payload_index(collection_name, field, schema_type)
