from functools import lru_cache
from fastembed import TextEmbedding

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _get_model() -> TextEmbedding:
    return TextEmbedding(model_name=EMBEDDING_MODEL)


def embed(text: str) -> list[float]:
    model = _get_model()
    return list(next(model.embed([text])))


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    return [list(v) for v in model.embed(texts)]
