from chromadb.errors import ChromaError

from backend.services.embedding_service import (
    EMBEDDING_MODEL,
    EMBEDDING_PROFILE,
    EmbeddingServiceError,
    embed_documents,
)
from backend.services.vector_store import VectorStoreError, get_collection


def reembed_existing_documents() -> int:
    collection = get_collection()
    try:
        records = collection.get(include=["documents", "metadatas", "embeddings"])
    except (ChromaError, OSError, ValueError) as error:
        raise VectorStoreError("The vector database could not read stored chunks.") from error

    ids = records.get("ids", [])
    documents = records.get("documents") or []
    metadatas = records.get("metadatas") or []
    old_embeddings = records.get("embeddings")
    if not ids:
        return 0
    if len(ids) != len(documents) or len(ids) != len(metadatas) or old_embeddings is None:
        raise VectorStoreError("The vector database returned incomplete stored chunk data.")

    legacy_indexes = [
        index
        for index, metadata in enumerate(metadatas)
        if metadata.get("embedding_profile") != EMBEDDING_PROFILE
        or metadata.get("embedding_model") != EMBEDDING_MODEL
    ]
    if not legacy_indexes:
        return 0

    legacy_ids = [ids[index] for index in legacy_indexes]
    legacy_documents = [documents[index] for index in legacy_indexes]
    previous_vectors = [list(old_embeddings[index]) for index in legacy_indexes]
    previous_metadata = [dict(metadatas[index]) for index in legacy_indexes]
    updated_metadata = [
        {
            **metadata,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_profile": EMBEDDING_PROFILE,
        }
        for metadata in previous_metadata
    ]

    new_vectors = embed_documents(legacy_documents)
    if len(new_vectors) != len(legacy_ids):
        raise EmbeddingServiceError("Ollama returned an incomplete embedding response.")

    try:
        collection.update(
            ids=legacy_ids,
            embeddings=new_vectors,
            metadatas=updated_metadata,
        )
    except (ChromaError, OSError, ValueError) as error:
        try:
            collection.update(
                ids=legacy_ids,
                embeddings=previous_vectors,
                metadatas=previous_metadata,
            )
        except (ChromaError, OSError, ValueError) as rollback_error:
            raise VectorStoreError(
                "Embedding migration failed and the previous chunk vectors could not be restored."
            ) from rollback_error
        raise VectorStoreError(
            "Embedding migration failed; the previous chunk vectors were restored."
        ) from error

    return len(legacy_ids)


if __name__ == "__main__":
    updated_count = reembed_existing_documents()
    print(f"Updated embeddings for {updated_count} existing chunks.")
