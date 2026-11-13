import math
import os
from collections.abc import Sequence

import requests


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_BATCH_SIZE = 16
REQUEST_TIMEOUT = (5, 120)
_USES_NOMIC_TASK_PREFIXES = EMBEDDING_MODEL.split(":", maxsplit=1)[0] == "nomic-embed-text"
DOCUMENT_PREFIX = "search_document: " if _USES_NOMIC_TASK_PREFIXES else ""
QUERY_PREFIX = "search_query: " if _USES_NOMIC_TASK_PREFIXES else ""
EMBEDDING_PROFILE = (
    f"{EMBEDDING_MODEL}:nomic-search-v1"
    if _USES_NOMIC_TASK_PREFIXES
    else f"{EMBEDDING_MODEL}:raw-v1"
)


class EmbeddingServiceError(RuntimeError):
    """Raised when Ollama cannot return usable embeddings."""


class EmbeddingModelUnavailableError(EmbeddingServiceError):
    """Raised when the configured Ollama embedding model is missing."""


def _request_embeddings(texts: Sequence[str]) -> list[list[float]]:
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": list(texts)},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.ConnectionError as error:
        raise EmbeddingServiceError(
            "Ollama is unavailable. Start the local Ollama service and try again."
        ) from error
    except requests.exceptions.Timeout as error:
        raise EmbeddingServiceError(
            "Ollama embedding timed out. Try again with a smaller document."
        ) from error
    except requests.exceptions.RequestException as error:
        raise EmbeddingServiceError("Ollama could not process the embedding request.") from error

    if response.status_code == 404:
        raise EmbeddingModelUnavailableError(
            f"The Ollama embedding model '{EMBEDDING_MODEL}' is not installed."
        )
    if not 200 <= response.status_code < 300:
        raise EmbeddingServiceError("Ollama returned an unsuccessful embedding response.")

    try:
        payload = response.json()
    except ValueError as error:
        raise EmbeddingServiceError("Ollama returned an invalid embedding response.") from error

    embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise EmbeddingServiceError("Ollama returned an incomplete embedding response.")

    validated_embeddings: list[list[float]] = []
    expected_dimensions: int | None = None
    for vector in embeddings:
        if not isinstance(vector, list) or not vector:
            raise EmbeddingServiceError("Ollama returned an invalid embedding vector.")

        if expected_dimensions is None:
            expected_dimensions = len(vector)
        if len(vector) != expected_dimensions:
            raise EmbeddingServiceError("Ollama returned inconsistent embedding dimensions.")

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in vector
        ):
            raise EmbeddingServiceError("Ollama returned non-numeric embedding values.")
        validated_embeddings.append([float(value) for value in vector])

    return validated_embeddings


def embed_texts(
    texts: Sequence[str],
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Embedding inputs must be non-empty strings.")
    if not texts:
        return []

    embeddings: list[list[float]] = []
    embedding_dimensions: int | None = None
    for start in range(0, len(texts), batch_size):
        batch = _request_embeddings(texts[start : start + batch_size])
        for vector in batch:
            if embedding_dimensions is None:
                embedding_dimensions = len(vector)
            elif len(vector) != embedding_dimensions:
                raise EmbeddingServiceError(
                    "Ollama returned inconsistent embedding dimensions."
                )
        embeddings.extend(batch)

    return embeddings


def embed_documents(texts: Sequence[str]) -> list[list[float]]:
    return embed_texts([f"{DOCUMENT_PREFIX}{text}" for text in texts])


def embed_query(query: str) -> list[float]:
    if not query.strip():
        raise ValueError("query must not be empty.")
    return embed_texts([f"{QUERY_PREFIX}{query}"])[0]
