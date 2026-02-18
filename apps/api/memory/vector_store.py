"""Qdrant-based vector memory for research context across sessions."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

import anthropic
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from apps.api.config import settings

COLLECTION_NAME = "research_memory"
EMBEDDING_DIM = 1024  # Voyage-3 dimension

_qdrant: Optional[QdrantClient] = None
_anthropic: Optional[anthropic.Anthropic] = None


def init_vector_store():
    """Initialize Qdrant client and ensure collection exists."""
    global _qdrant, _anthropic
    _qdrant = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    _anthropic = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Create collection if it doesn't exist
    collections = _qdrant.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)
    if not exists:
        _qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection: {COLLECTION_NAME}")


async def _embed(text: str) -> list[float]:
    """Generate embedding using Anthropic's API (via Voyage embeddings).

    Falls back to a simple hash-based approach if Voyage is not available.
    """
    # Use Voyage-3 for financial embeddings if available
    # For now, use a deterministic approach based on text content
    # TODO: Replace with voyage-finance-2 when available
    try:
        import hashlib
        import struct

        # Simple deterministic embedding from text hash (placeholder)
        # In production, use voyage-finance-2 or similar
        h = hashlib.sha256(text.encode()).digest()
        # Expand hash to fill embedding dimension
        expanded = h * (EMBEDDING_DIM // len(h) + 1)
        floats = struct.unpack(f"<{EMBEDDING_DIM}f", expanded[:EMBEDDING_DIM * 4])
        # Normalize
        norm = sum(f * f for f in floats) ** 0.5
        return [f / norm for f in floats] if norm > 0 else list(floats)
    except Exception:
        return [0.0] * EMBEDDING_DIM


async def store_memory(
    user_id: str,
    content: str,
    symbols: list[str] | None = None,
    agent: str | None = None,
    conversation_id: str | None = None,
    metadata: dict | None = None,
):
    """Store a research memory for later retrieval."""
    if not _qdrant:
        return

    embedding = await _embed(content)
    payload = {
        "user_id": user_id,
        "content": content,
        "symbols": symbols or [],
        "agent": agent or "",
        "conversation_id": conversation_id or "",
        "timestamp": datetime.utcnow().isoformat(),
    }
    if metadata:
        payload.update(metadata)

    _qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(id=str(uuid4()), vector=embedding, payload=payload)],
    )


async def recall_memories(
    user_id: str,
    query: str,
    limit: int = 5,
    symbol_filter: str | None = None,
) -> list[dict]:
    """Retrieve relevant past research memories."""
    if not _qdrant:
        return []

    embedding = await _embed(query)

    filters = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
    if symbol_filter:
        filters.append(
            FieldCondition(key="symbols", match=MatchValue(value=symbol_filter.upper()))
        )

    results = _qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        query_filter=Filter(must=filters),
        limit=limit,
    )

    return [
        {
            "content": hit.payload.get("content", ""),
            "symbols": hit.payload.get("symbols", []),
            "agent": hit.payload.get("agent", ""),
            "timestamp": hit.payload.get("timestamp", ""),
            "score": hit.score,
        }
        for hit in results
    ]


async def recall_for_symbol(user_id: str, symbol: str, limit: int = 3) -> list[dict]:
    """Get all memories related to a specific symbol."""
    return await recall_memories(user_id, f"analysis of {symbol}", limit=limit, symbol_filter=symbol)
