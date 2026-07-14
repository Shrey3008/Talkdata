"""Text embedding via fastembed (ONNX), avoiding the ~2GB torch dependency of
sentence-transformers — Render's free tier has 512MB RAM.

Must stay consistent with EMBEDDING_DIM in app.models.schema_embedding (384).
"""
from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: TextEmbedding | None = None


def get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [vec.tolist() for vec in get_model().embed(texts)]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
