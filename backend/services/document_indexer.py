from uuid import uuid4

from backend.services.embedding_service import embed_documents
from backend.services.pdf_processor import ExtractedPage
from backend.services.text_chunker import chunk_pages
from backend.services.vector_store import store_document_chunks


class NoIndexableTextError(ValueError):
    """Raised when a PDF contains no extractable text to index."""


def index_document(
    filename: str,
    pages: list[ExtractedPage],
) -> dict[str, str | int]:
    document_id = uuid4().hex
    chunks = chunk_pages(pages)
    if not chunks:
        raise NoIndexableTextError("No selectable text was found in the PDF.")

    embeddings = embed_documents([str(chunk["text"]) for chunk in chunks])
    store_document_chunks(
        document_id,
        filename,
        chunks,
        embeddings,
        total_pages=len(pages),
        extracted_characters=sum(len(page["text"]) for page in pages),
    )
    return {
        "document_id": document_id,
        "total_chunks": len(chunks),
    }
