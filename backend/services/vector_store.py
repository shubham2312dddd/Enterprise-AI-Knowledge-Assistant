import os
from functools import lru_cache
from pathlib import Path
from collections.abc import Sequence
from typing import Any

import chromadb
from chromadb.config import Settings
from chromadb.errors import ChromaError

from backend.services.embedding_service import EMBEDDING_MODEL, EMBEDDING_PROFILE


COLLECTION_NAME = "document_chunks"
DEFAULT_VECTOR_DB_PATH = Path(__file__).resolve().parents[1] / "vector_db"
VECTOR_DB_PATH = Path(os.getenv("CHROMA_DB_PATH", str(DEFAULT_VECTOR_DB_PATH)))


class VectorStoreError(RuntimeError):
    """Raised when ChromaDB cannot complete an operation."""


class DocumentNotFoundError(LookupError):
    """Raised when a document has no indexed chunks."""


class DocumentAlreadyExistsError(VectorStoreError):
    """Raised when a document ID is already present in the collection."""


@lru_cache(maxsize=4)
def _get_collection_at(path: str) -> Any:
    try:
        client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    except (ChromaError, OSError, ValueError) as error:
        raise VectorStoreError("The persistent vector database is unavailable.") from error


def get_collection() -> Any:
    return _get_collection_at(str(VECTOR_DB_PATH))


def store_document_chunks(
    document_id: str,
    filename: str,
    chunks: list[dict[str, int | str]],
    embeddings: list[list[float]],
    total_pages: int | None = None,
    extracted_characters: int | None = None,
) -> None:
    if not chunks or len(chunks) != len(embeddings):
        raise ValueError("Each non-empty chunk must have exactly one embedding.")

    collection = get_collection()
    document_filter = {"document_id": document_id}
    try:
        existing = collection.get(
            where=document_filter,
            limit=1,
            include=["metadatas"],
        )
    except (ChromaError, OSError, ValueError) as error:
        raise VectorStoreError("The vector database could not check the document index.") from error

    if existing.get("ids"):
        raise DocumentAlreadyExistsError("This document ID is already indexed.")

    ids = [f"{document_id}:{chunk['chunk_index']}" for chunk in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "filename": filename,
            "page_number": chunk["page_number"],
            "chunk_index": chunk["chunk_index"],
            "total_pages": total_pages or max(int(item["page_number"]) for item in chunks),
            "extracted_characters": extracted_characters
            if extracted_characters is not None
            else sum(len(str(item["text"])) for item in chunks),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_profile": EMBEDDING_PROFILE,
        }
        for chunk in chunks
    ]

    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=[str(chunk["text"]) for chunk in chunks],
            metadatas=metadatas,
        )
    except (ChromaError, OSError, ValueError) as error:
        try:
            collection.delete(where=document_filter)
        except (ChromaError, OSError, ValueError) as cleanup_error:
            raise VectorStoreError(
                "Vector storage failed and the partial document index could not be removed."
            ) from cleanup_error
        raise VectorStoreError(
            "Vector storage failed; the partial document index was removed."
        ) from error


def document_exists(document_id: str) -> bool:
    try:
        result = get_collection().get(
            where={"document_id": document_id},
            limit=1,
            include=["metadatas"],
        )
    except (ChromaError, OSError, ValueError) as error:
        raise VectorStoreError("The vector database could not check the document index.") from error
    return bool(result.get("ids"))


def list_indexed_documents() -> list[dict[str, Any]]:
    try:
        records = get_collection().get(include=["metadatas"])
    except (ChromaError, OSError, ValueError) as error:
        raise VectorStoreError("The vector database could not list indexed documents.") from error

    documents: dict[str, dict[str, Any]] = {}
    for metadata in records.get("metadatas") or []:
        document_id = metadata["document_id"]
        document = documents.setdefault(
            document_id,
            {
                "document_id": document_id,
                "filename": metadata["filename"],
                "total_chunks": 0,
                "total_pages": metadata.get("total_pages"),
                "extracted_characters": metadata.get("extracted_characters"),
                "pages_with_text": set(),
            },
        )
        document["total_chunks"] += 1
        if metadata.get("total_pages") is not None:
            current_total_pages = document["total_pages"] or 0
            document["total_pages"] = max(current_total_pages, metadata["total_pages"])
        document["pages_with_text"].add(metadata["page_number"])

    return [
        {
            **document,
            "pages_with_text": sorted(document["pages_with_text"]),
        }
        for document in sorted(
            documents.values(),
            key=lambda item: (item["filename"].casefold(), item["document_id"]),
        )
    ]


def delete_document_chunks(document_id: str) -> None:
    collection = get_collection()
    try:
        existing = collection.get(
            where={"document_id": document_id},
            limit=1,
            include=["metadatas"],
        )
        if not existing.get("ids"):
            raise DocumentNotFoundError("The requested document has not been indexed.")
        collection.delete(where={"document_id": document_id})
    except DocumentNotFoundError:
        raise
    except (ChromaError, OSError, ValueError) as error:
        raise VectorStoreError("The vector database could not remove the document.") from error


def _document_filter(
    document_id: str | None,
    document_ids: Sequence[str] | None,
) -> dict[str, Any] | None:
    if document_id is not None and document_ids is not None:
        raise ValueError("Provide either document_id or document_ids, not both.")

    selected_ids = list(document_ids) if document_ids is not None else (
        [document_id] if document_id is not None else []
    )
    if not selected_ids:
        return None
    if len(selected_ids) == 1:
        return {"document_id": selected_ids[0]}
    return {"document_id": {"$in": selected_ids}}


def search_document_chunks(
    document_id: str | None,
    query_embedding: list[float],
    top_k: int,
    document_ids: Sequence[str] | None = None,
    include_document_id: bool = False,
) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k must be greater than zero.")

    collection = get_collection()
    document_filter = _document_filter(document_id, document_ids)
    try:
        get_options: dict[str, Any] = {"limit": 1, "include": ["metadatas"]}
        if document_filter is not None:
            get_options["where"] = document_filter
        existing = collection.get(**get_options)
        matching_ids = existing.get("ids", [])
        if not matching_ids:
            raise DocumentNotFoundError("The requested document has not been indexed.")

        query_options: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if document_filter is not None:
            query_options["where"] = document_filter
        result = collection.query(
            **query_options,
        )
    except DocumentNotFoundError:
        raise
    except (ChromaError, OSError, ValueError) as error:
        raise VectorStoreError("The vector database search failed.") from error

    result_ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    results = []
    for chunk_id, text, metadata, distance in zip(
        result_ids,
        documents,
        metadatas,
        distances,
    ):
        item = {
            "chunk_id": chunk_id,
            "text": text,
            "filename": metadata["filename"],
            "page_number": metadata["page_number"],
            "chunk_index": metadata["chunk_index"],
            "distance": float(distance),
        }
        if include_document_id:
            item["document_id"] = metadata["document_id"]
        results.append(item)
    return results
