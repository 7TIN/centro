"""
Pinecone-backed vector store service for retrieval.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from config.settings import get_settings
from src.core.exceptions import ConfigurationError


class VectorStoreService:
    """Encapsulates embedding, indexing, and semantic search."""

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.pinecone_api_key or not settings.pinecone_index_name:
            raise ConfigurationError(
                "Pinecone is not configured. Set PINECONE_API_KEY and PINECONE_INDEX_NAME."
            )
        if not settings.pinecone_environment:
            raise ConfigurationError(
                "Pinecone region is not configured. Set PINECONE_ENVIRONMENT (example: us-east-1)."
            )

        self._settings = settings
        try:
            from pinecone import Pinecone, ServerlessSpec
        except Exception as exc:
            raise ConfigurationError(
                "Pinecone SDK is unavailable. Install the `pinecone` package.",
                details={"error": str(exc)},
            ) from exc

        self._serverless_spec_cls = ServerlessSpec
        self._client = Pinecone(api_key=settings.pinecone_api_key)
        self._index_name = settings.pinecone_index_name

        self._ensure_index()
        self._index = self._client.Index(self._index_name)

        # Import retrieval-only dependencies lazily so app boot does not require them.
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from sentence_transformers import SentenceTransformer

        self._embedder = SentenceTransformer(settings.embedding_model)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.retrieval_chunk_size,
            chunk_overlap=settings.retrieval_chunk_overlap,
        )

    def _ensure_index(self) -> None:
        existing_indexes = set(self._client.list_indexes().names())
        if self._index_name in existing_indexes:
            return

        self._client.create_index(
            name=self._index_name,
            dimension=self._settings.embedding_dimensions,
            metric="cosine",
            spec=self._serverless_spec_cls(
                cloud="aws",
                region=self._settings.pinecone_environment,
            ),
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._embedder.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if hasattr(vectors, "tolist"):
            return vectors.tolist()
        return [list(row) for row in vectors]

    def _split_documents(self, documents: list[str]) -> list[str]:
        chunks: list[str] = []
        for document in documents:
            if not document or not document.strip():
                continue
            chunks.extend(
                chunk.strip()
                for chunk in self._splitter.split_text(document)
                if chunk and chunk.strip()
            )
        return chunks

    def upsert_documents(
        self,
        person_id: str,
        documents: list[str],
        source: str = "manual",
        extra_metadata: dict[str, Any] | None = None,
    ) -> int:
        """Chunk and index documents for a person."""
        chunks = self._split_documents(documents)
        if not chunks:
            return 0

        vectors = self._embed(chunks)
        metadata = extra_metadata or {}
        timestamp = datetime.now(timezone.utc).isoformat()

        payload: list[dict[str, Any]] = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1):
            payload.append(
                {
                    "id": str(uuid4()),
                    "values": vector,
                    "metadata": {
                        "person_id": person_id,
                        "source": source,
                        "chunk_index": index,
                        "text": chunk,
                        "created_at": timestamp,
                        **metadata,
                    },
                }
            )

        self._index.upsert(vectors=payload)
        return len(payload)

    def search(
        self,
        person_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Run semantic search filtered by person."""
        query_vector = self._embed([query])[0]
        response = self._index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            include_values=False,
            filter={"person_id": {"$eq": person_id}},
        )

        matches = getattr(response, "matches", None)
        if matches is None and isinstance(response, dict):
            matches = response.get("matches", [])

        results: list[dict[str, Any]] = []
        for match in matches or []:
            match_id = getattr(match, "id", None)
            if match_id is None and isinstance(match, dict):
                match_id = match.get("id", "")

            score = getattr(match, "score", None)
            if score is None and isinstance(match, dict):
                score = match.get("score", 0.0)

            metadata = getattr(match, "metadata", None)
            if metadata is None and isinstance(match, dict):
                metadata = match.get("metadata", {})
            metadata = metadata or {}

            numeric_score = float(score or 0.0)
            if numeric_score < min_score:
                continue

            results.append(
                {
                    "id": str(match_id or ""),
                    "score": numeric_score,
                    "text": str(metadata.get("text", "")),
                    "source": metadata.get("source"),
                    "metadata": metadata,
                }
            )

        return results
