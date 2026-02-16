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

        # Local caches used for hybrid fallback and source lifecycle operations.
        self._keyword_cache: dict[str, list[dict[str, Any]]] = {}
        self._source_vector_ids: dict[tuple[str, str], set[str]] = {}

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
            vector_id = str(uuid4())
            payload.append(
                {
                    "id": vector_id,
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

        key = (person_id, source)
        self._source_vector_ids.setdefault(key, set()).update(item["id"] for item in payload)
        cache_entries = self._keyword_cache.setdefault(person_id, [])
        cache_entries.extend(
            {
                "id": item["id"],
                "source": item["metadata"]["source"],
                "text": item["metadata"]["text"],
                "metadata": item["metadata"],
            }
            for item in payload
        )
        return len(payload)

    def delete_by_source(self, person_id: str, source: str) -> int:
        """Delete all indexed chunks for a person/source pair."""
        key = (person_id, source)
        existing_ids = list(self._source_vector_ids.get(key, set()))

        try:
            self._index.delete(
                filter={
                    "person_id": {"$eq": person_id},
                    "source": {"$eq": source},
                }
            )
        except TypeError:
            if existing_ids:
                self._index.delete(ids=existing_ids)

        deleted_count = len(existing_ids)
        self._source_vector_ids.pop(key, None)

        if person_id in self._keyword_cache:
            before = len(self._keyword_cache[person_id])
            self._keyword_cache[person_id] = [
                item for item in self._keyword_cache[person_id] if item.get("source") != source
            ]
            deleted_count = max(deleted_count, before - len(self._keyword_cache[person_id]))

        return deleted_count

    def replace_source_documents(
        self,
        person_id: str,
        source: str,
        documents: list[str],
        extra_metadata: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        """Replace all chunks for a person/source with new documents."""
        deleted = self.delete_by_source(person_id=person_id, source=source)
        indexed = self.upsert_documents(
            person_id=person_id,
            documents=documents,
            source=source,
            extra_metadata=extra_metadata,
        )
        return deleted, indexed

    def _keyword_search(self, person_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        """Fallback lexical retrieval across locally cached chunks."""
        tokens = {token for token in query.lower().split() if token}
        if not tokens:
            return []

        entries = self._keyword_cache.get(person_id, [])
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in entries:
            text = str(item.get("text", "")).lower()
            if not text:
                continue

            overlap = sum(1 for token in tokens if token in text)
            if overlap <= 0:
                continue

            score = overlap / len(tokens)
            scored.append((score, item))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, item in scored[:top_k]:
            results.append(
                {
                    "id": str(item.get("id", "")),
                    "score": float(score),
                    "text": str(item.get("text", "")),
                    "source": item.get("source"),
                    "metadata": item.get("metadata", {}),
                    "retrieval_mode": "keyword_fallback",
                }
            )
        return results

    def search(
        self,
        person_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        enable_hybrid_fallback: bool = True,
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
                    "retrieval_mode": "vector",
                }
            )

        if results:
            results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
            return results[:top_k]

        if enable_hybrid_fallback:
            return self._keyword_search(person_id=person_id, query=query, top_k=top_k)

        return []
